import frappe
from frappe import _
from frappe.utils import cint


def session_employee(fields: str | list[str] = "name"):
	"""The `Employee` record linked to the signed-in user, or None if there is none."""
	return frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user},
		fields,
		as_dict=isinstance(fields, list),
	)


def require_employee_id() -> str:
	"""The session employee id. Throws rather than returning data for nobody."""
	employee = session_employee()
	if not employee:
		frappe.throw(_("No Employee record is linked to {0}").format(frappe.session.user))
	return employee


def list_for_employee(
	doctype: str,
	fields: list[str],
	filters: dict | None = None,
	order_by: str | None = None,
	limit=None,
	employee: str | None = None,
) -> list[dict]:
	"""Rows of *doctype* belonging to the session employee. `limit` unset = all rows."""
	filters = dict(filters or {})
	filters["employee"] = employee or require_employee_id()
	return frappe.get_all(
		doctype,
		filters=filters,
		fields=fields,
		order_by=order_by,
		limit_page_length=cint(limit),
	)


def insert_for_employee(
	doctype: str,
	payload: dict,
	fields: tuple[str, ...],
	extra: dict | None = None,
) -> dict:
	"""Insert *doctype* as a draft for the session employee.

	`employee` always comes from the session, never from *payload* — a
	client-supplied one would let any employee file records against a colleague.
	Only *fields* are copied across, so no request can set `docstatus`,
	`approval_status` or any other field the approver owns.
	"""
	doc = frappe.get_doc(
		{
			"doctype": doctype,
			"employee": require_employee_id(),
			**{f: payload.get(f) for f in fields if payload.get(f) is not None},
			**(extra or {}),
		}
	)
	doc.insert()
	return {"name": doc.name}



def user_full_names(emails) -> dict[str, str]:
	"""`{email: full_name}` for the given users, in one query."""
	emails = {e for e in emails if e}
	if not emails:
		return {}
	return {
		u.name: u.full_name
		for u in frappe.get_all("User", filters={"name": ["in", list(emails)]}, fields=["name", "full_name"])
	}
