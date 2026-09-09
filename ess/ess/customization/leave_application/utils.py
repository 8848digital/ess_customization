import frappe
from frappe import _

from ess.utils import insert_for_employee, list_for_employee, require_employee_id

LIST_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"leave_type",
	"from_date",
	"to_date",
	"half_day",
	"half_day_date",
	"description",
	"leave_approver",
	"leave_approver_name",
	"status",
	"total_leave_days",
	"posting_date",
]

WRITE_FIELDS = (
	"leave_type",
	"from_date",
	"to_date",
	"half_day",
	"half_day_date",
	"description",
	"leave_approver",
)


def get_list(limit=None) -> list[dict]:
	rows = list_for_employee(
		"Leave Application",
		LIST_FIELDS,
		filters={"docstatus": ["<", 2]},
		order_by="from_date desc",
		limit=limit,
	)
	return rows


def create(payload: dict) -> dict:
	"""Filed as a draft with status Open.

	HR refuses to submit a Leave Application still in Open, by design: the
	approver is the one who moves it to Approved/Rejected and submits it.
	"""
	return insert_for_employee("Leave Application", payload, WRITE_FIELDS, extra={"status": "Open"})


def cancel(name: str) -> dict:
	"""Withdraw one's own application. Only the applicant may, and only while
	nobody has actioned it."""
	doc = frappe.get_doc("Leave Application", name)
	if doc.employee != require_employee_id():
		frappe.throw(_("You can only cancel your own leave applications"), frappe.PermissionError)

	if doc.docstatus == 1:
		doc.cancel()
	elif doc.docstatus == 0:
		doc.db_set("status", "Cancelled")

	return {"success": True}
