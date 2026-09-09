import frappe
from frappe import _

from ess.utils import list_for_employee, require_employee_id

LIST_FIELDS = [
	"name",
	"employee",
	"start_date",
	"end_date",
	"posting_date",
	"gross_pay",
	"total_deduction",
	"net_pay",
	"status",
]


def get_list(limit=None) -> list[dict]:
	"""Submitted slips only — a draft slip is not yet what anyone was paid."""
	return list_for_employee(
		"Salary Slip",
		LIST_FIELDS,
		filters={"docstatus": 1},
		order_by="start_date desc",
		limit=limit,
	)


def download_pdf(name: str) -> None:
	"""Stream one's own slip as a PDF.

	Writes straight to the response — the client opens this as a URL, so it must
	answer with the file, not with the JSON envelope every other endpoint uses.
	"""
	slip = frappe.db.get_value("Salary Slip", name, ["employee", "docstatus"], as_dict=True)
	if not slip or slip.employee != require_employee_id():
		frappe.throw(_("Salary Slip {0} is not yours to download").format(name), frappe.PermissionError)
	if slip.docstatus != 1:
		frappe.throw(_("Salary Slip {0} has not been submitted yet").format(name))

	frappe.local.response.filename = f"{name}.pdf"
	frappe.local.response.filecontent = frappe.get_print("Salary Slip", name, as_pdf=True)
	frappe.local.response.type = "pdf"


COMPONENT_FIELDS = ["name", "parentfield", "idx", "salary_component", "amount"]


def get_detail(name: str) -> dict:
	"""One slip with its earnings and deductions rows.

	Split server-side by `parentfield` — it is the only thing the screen does
	with them, and Frappe stores both in the same `Salary Detail` table.
	"""
	slip = frappe.db.get_value("Salary Slip", name, [*LIST_FIELDS, "docstatus"], as_dict=True)
	if not slip or slip.employee != require_employee_id():
		frappe.throw(_("Salary Slip {0} is not yours to view").format(name), frappe.PermissionError)
	if slip.pop("docstatus") != 1:
		frappe.throw(_("Salary Slip {0} has not been submitted yet").format(name))

	components = frappe.get_all("Salary Detail", filters={"parent": name}, fields=COMPONENT_FIELDS, order_by="idx asc")

	return {
		"slip": slip,
		"earnings": [c for c in components if c.parentfield == "earnings"],
		"deductions": [c for c in components if c.parentfield == "deductions"],
	}
