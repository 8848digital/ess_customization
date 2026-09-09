import frappe
from frappe import _
from frappe.utils import cint, flt

from ess.ess.customization.attendance_request.utils import derive_status, requested_days
from ess.utils import session_employee

# One row per request kind the approver's inbox unions together. Leave and
# Expense carry their own approver field; Advance and Attendance Request have
# none in HR, so those route by the employee's `reports_to`.
KINDS = {
	"leave": {
		"doctype": "Leave Application",
		"approver_field": "leave_approver",
		"pending": {"status": "Open", "docstatus": 0},
		"quantity_field": "total_leave_days",
		"posted_on_field": "posting_date",
		"status_field": "status",
		"extra_fields": (),
		"approved": {"status": "Approved"},
		"rejected": {"status": "Rejected"},
		"cancel_on_reject": False,
	},
	"expense": {
		"doctype": "Expense Claim",
		"approver_field": "expense_approver",
		"pending": {"approval_status": "Draft", "docstatus": 0},
		"quantity_field": "total_claimed_amount",
		"posted_on_field": "posting_date",
		"status_field": "approval_status",
		"extra_fields": (),
		"approved": {"approval_status": "Approved"},
		"rejected": {"approval_status": "Rejected"},
		"cancel_on_reject": False,
	},
	"advance": {
		"doctype": "Employee Advance",
		"approver_field": None,
		"pending": {"docstatus": 0},
		"quantity_field": "advance_amount",
		"posted_on_field": "posting_date",
		"status_field": "status",
		"extra_fields": (),
		"approved": {},
		"rejected": {},
		# ponytail: Employee Advance has no Rejected state — submitting then
		# cancelling is how a rejection becomes visible. Swap for a Workflow if
		# the product needs "rejected" told apart from "cancelled".
		"cancel_on_reject": True,
	},
	"attendance": {
		"doctype": "Attendance Request",
		"approver_field": None,
		"pending": {"docstatus": 0},
		# No amount column — the figure the approver reads is the day count.
		"quantity_field": None,
		"posted_on_field": "creation",
		# No status column either; docstatus is the approval state.
		"status_field": None,
		"extra_fields": ("from_date", "to_date", "half_day"),
		"approved": {},
		"rejected": {},
		"cancel_on_reject": True,
	},
}


def _config(kind: str) -> dict:
	config = KINDS.get(kind)
	if not config:
		frappe.throw(_("Unknown request kind: {0}").format(kind))
	return config


def direct_reports() -> list[str]:
	"""Employees reporting to the signed-in user, for the kinds HR gives no
	approver field."""
	manager = session_employee()
	if not manager:
		return []
	return frappe.get_all("Employee", filters={"reports_to": manager}, pluck="name")


def get_pending(limit=50) -> list[dict]:
	"""What is waiting on the signed-in user, across all four request kinds.

	This endpoint is the authority on who may approve what (spec.md §7): the
	client renders what comes back and never derives the answer itself.
	"""
	reports = direct_reports()
	pending = []

	for kind, config in KINDS.items():
		filters = dict(config["pending"])
		if config["approver_field"]:
			filters[config["approver_field"]] = frappe.session.user
		elif reports:
			filters["employee"] = ["in", reports]
		else:
			continue

		pending += _summaries(kind, config, filters, limit)

	return _newest_first(pending)


def get_mine(limit=50) -> list[dict]:
	"""The signed-in employee's own submissions, across the same four kinds.

	Same row shape as `get_pending`, so one list component renders both — this
	is the "My Requests" screen, where `get_pending` is the approver's inbox.
	"""
	employee = session_employee()
	if not employee:
		return []

	mine = []
	for kind, config in KINDS.items():
		mine += _summaries(kind, config, {"employee": employee}, limit)

	return _newest_first(mine)


def _newest_first(rows: list[dict]) -> list[dict]:
	return sorted(rows, key=lambda r: r["posted_on"] or "", reverse=True)


def _summaries(kind: str, config: dict, filters: dict, limit) -> list[dict]:
	"""The rows of one doctype, flattened to the shape both inboxes render."""
	fields = ["name", "employee", "employee_name", "docstatus", config["posted_on_field"]]
	fields += [f for f in (config["quantity_field"], config["status_field"]) if f]
	fields += list(config["extra_fields"])

	return [
		{
			"id": row.name,
			"kind": kind,
			"employee": row.employee,
			"employee_name": row.employee_name,
			"quantity": _quantity(row, config),
			"posted_on": str(row.get(config["posted_on_field"]) or "")[:10] or None,
			"status": _status(row, config),
		}
		for row in frappe.get_all(
			config["doctype"],
			filters=filters,
			fields=list(dict.fromkeys(fields)),
			order_by=f"{config['posted_on_field']} desc",
			limit_page_length=cint(limit),
		)
	]


def _quantity(row: dict, config: dict) -> float:
	if config["quantity_field"]:
		return flt(row.get(config["quantity_field"]))
	return requested_days(row.get("from_date"), row.get("to_date"), row.get("half_day"))


def _status(row: dict, config: dict) -> str | None:
	if config["status_field"]:
		return row.get(config["status_field"])
	return derive_status(row.get("docstatus"))


def act(kind: str, id: str, approve: bool, comment: str | None = None) -> dict:
	"""Approve or reject one request. Online-only by design — the client never
	queues these, so a stale queue can never approve a withdrawn request."""
	config = _config(kind)
	doc = frappe.get_doc(config["doctype"], id)
	assert_can_approve(doc, config)

	if comment:
		doc.add_comment("Comment", comment)

	doc.update(config["approved"] if approve else config["rejected"])

	if doc.docstatus == 0:
		doc.submit()
	else:
		doc.save()

	if not approve and config["cancel_on_reject"]:
		doc.cancel()

	return {"success": True}


def assert_can_approve(doc, config: dict) -> None:
	"""HR's own permissions decide this — never the caller."""
	if config["approver_field"]:
		if doc.get(config["approver_field"]) == frappe.session.user:
			return
	else:
		manager = session_employee()
		# `manager` and `reports_to` can both be empty; that is not a match.
		if manager and frappe.db.get_value("Employee", doc.employee, "reports_to") == manager:
			return

	if "HR Manager" in frappe.get_roles():
		return

	frappe.throw(
		_("You are not the approver for {0} {1}").format(doc.doctype, doc.name),
		frappe.PermissionError,
	)
