import frappe
from frappe import _
from frappe.utils import flt

from ess.utils import require_employee_id, session_employee, user_full_names

LIST_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"expense_approver",
	"approval_status",
	"status",
	"posting_date",
	"total_claimed_amount",
	"total_sanctioned_amount",
	"total_taxes_and_charges",
	"grand_total",
	"total_advance_amount",
	"remark",
]

WRITE_FIELDS = ("expense_approver", "posting_date", "remark", "company", "cost_center")


def get_list(limit=None) -> list[dict]:
	rows = frappe.get_all(
		"Expense Claim",
		filters={"employee": require_employee_id(), "docstatus": ["<", 2]},
		fields=LIST_FIELDS,
		order_by="posting_date desc",
		limit_page_length=frappe.utils.cint(limit),
	)

	approver_names = user_full_names(row.expense_approver for row in rows)
	for row in rows:
		row["expense_approver_name"] = approver_names.get(row.expense_approver)
		# Expense Claim's title_field is employee_name; it has no title column.
		row["title"] = row.employee_name
		row["advance_adjusted"] = row.pop("total_advance_amount")

	return rows


def create(payload: dict) -> dict:
	"""File a claim as a draft.

	It stays a draft on purpose: HR refuses to submit an Expense Claim whose
	`approval_status` is still Draft, and only the approver may change that.
	"""
	employee = require_employee_id()
	claim = frappe.get_doc(
		{
			"doctype": "Expense Claim",
			"employee": employee,
			**{f: payload.get(f) for f in WRITE_FIELDS if payload.get(f) is not None},
			"expense_approver": payload.get("expense_approver")
			or frappe.db.get_value("Employee", employee, "expense_approver"),
			"expenses": [
				{
					"expense_date": line.get("expense_date"),
					"expense_type": line.get("expense_type"),
					"description": line.get("description"),
					"amount": flt(line.get("amount")),
					"sanctioned_amount": flt(line.get("amount")),
				}
				for line in (payload.get("expenses") or [])
			],
			"taxes": [
				{
					"description": tax.get("description"),
					"rate": flt(tax.get("rate")),
					"tax_amount": flt(tax.get("tax_amount")),
				}
				for tax in (payload.get("taxes") or [])
			],
		}
	)
	claim.insert()

	attach_receipts(claim.name, payload.get("attachments") or [])

	return {"name": claim.name}


def update(name: str, payload: dict) -> dict:
	"""Amend one's own still-Draft claim, including its line items and taxes.
	Only before the approver has acted (docstatus 0)."""
	claim = frappe.get_doc("Expense Claim", name)
	if claim.employee != require_employee_id():
		frappe.throw(_("You can only edit your own claims"), frappe.PermissionError)
	if claim.docstatus != 0:
		frappe.throw(_("Expense Claim {0} has already been decided and can no longer be edited").format(name))

	for f in WRITE_FIELDS:
		if payload.get(f) is not None:
			claim.set(f, payload[f])

	if payload.get("expenses") is not None:
		claim.set(
			"expenses",
			[
				{
					"expense_date": line.get("expense_date"),
					"expense_type": line.get("expense_type"),
					"description": line.get("description"),
					"amount": flt(line.get("amount")),
					"sanctioned_amount": flt(line.get("amount")),
				}
				for line in payload["expenses"]
			],
		)
	if payload.get("taxes") is not None:
		claim.set(
			"taxes",
			[
				{
					"description": tax.get("description"),
					"rate": flt(tax.get("rate")),
					"tax_amount": flt(tax.get("tax_amount")),
				}
				for tax in payload["taxes"]
			],
		)

	claim.save()
	attach_receipts(claim.name, payload.get("attachments") or [])
	return {"name": claim.name}


def attach_receipts(claim: str, attachments: list[dict]) -> None:
	"""Point already-uploaded receipt files at the claim they belong to.

	`upload_receipt` runs first and returns a `file_url`; this is the step that
	turns those loose files into attachments of the claim.
	"""
	urls = [a.get("file_url") for a in attachments if a.get("file_url")]
	if not urls:
		return

	for name in frappe.get_all(
		"File",
		filters={"file_url": ["in", urls], "attached_to_name": ["is", "not set"]},
		pluck="name",
	):
		file = frappe.get_doc("File", name)
		file.attached_to_doctype = "Expense Claim"
		file.attached_to_name = claim
		file.save()


def upload_receipt(file_name: str, content: str, mime_type: str | None = None) -> dict:
	"""Step 1 of the two-step receipt push: store the bytes, hand back a URL.

	*content* is base64. The claim that references the URL is created
	separately, so a retry never re-uploads a file that already has one.
	"""
	require_employee_id()
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"content": content,
			"decode": True,
			"is_private": 1,
		}
	).insert()

	return {"file_url": file.file_url}


DETAIL_LINE_FIELDS = ["name", "idx", "expense_date", "expense_type", "amount", "sanctioned_amount", "description"]
DETAIL_TAX_FIELDS = ["name", "idx", "description", "rate", "tax_amount"]


def get_detail(name: str) -> dict:
	"""One claim with its lines, taxes and receipts.

	`get_list` deliberately returns parent rows only — the detail screen is the
	one place that needs the child tables, and loading them for every row of a
	list would be three extra queries per claim for data nobody is looking at.
	"""
	claim = frappe.db.get_value("Expense Claim", name, LIST_FIELDS, as_dict=True)
	if not claim:
		frappe.throw(_("Expense Claim {0} not found").format(name))

	employee = session_employee()
	is_owner = employee and claim.employee == employee
	is_approver = claim.expense_approver == frappe.session.user
	if not (is_owner or is_approver or "HR Manager" in frappe.get_roles()):
		frappe.throw(_("Expense Claim {0} is not yours to view").format(name), frappe.PermissionError)

	claim["expense_approver_name"] = user_full_names([claim.expense_approver]).get(claim.expense_approver)
	claim["title"] = claim.employee_name
	claim["advance_adjusted"] = claim.pop("total_advance_amount")

	return {
		"claim": claim,
		"lines": frappe.get_all("Expense Claim Detail", filters={"parent": name}, fields=DETAIL_LINE_FIELDS, order_by="idx asc"),
		"taxes": frappe.get_all("Expense Taxes and Charges", filters={"parent": name}, fields=DETAIL_TAX_FIELDS, order_by="idx asc"),
		"attachments": frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Expense Claim", "attached_to_name": name},
			fields=["name", "file_name", "file_url", "file_size"],
			order_by="creation asc",
		),
	}
