import frappe
from frappe import _

from ess.utils import session_employee


def get_list(year=None) -> list[dict]:
	"""The employee's assigned holiday list.

	Weekly offs are left in — the client filters them out of the holiday screen
	but still needs them to count working days (spec.md §6.10).
	"""
	employee = session_employee(["name", "holiday_list"])
	if not employee:
		frappe.throw(_("No Employee record is linked to {0}").format(frappe.session.user))
	if not employee.holiday_list:
		return []

	filters = {"parent": employee.holiday_list, "parenttype": "Holiday List"}
	if year:
		filters["holiday_date"] = ["between", [f"{year}-01-01", f"{year}-12-31"]]

	return frappe.get_all(
		"Holiday",
		filters=filters,
		fields=["name", "parent", "holiday_date", "description", "weekly_off"],
		order_by="holiday_date asc",
	)
