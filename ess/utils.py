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



def update_for_employee(doctype: str, name: str, payload: dict, fields: tuple[str, ...]) -> dict:
	"""Update *doctype* for the session employee's own record.

	Only *fields* are copied across — same allowlist discipline as
	insert_for_employee. Refuses once the record is no longer the employee's
	to change: not theirs, or already decided (docstatus != 0 — Frappe's own
	validate_update_after_submit would catch most of this anyway, but this
	gives a clean message instead of a framework error).
	"""
	doc = frappe.get_doc(doctype, name)
	if doc.employee != require_employee_id():
		frappe.throw(_("You can only edit your own records"), frappe.PermissionError)
	if doc.docstatus != 0:
		frappe.throw(_("{0} {1} has already been decided and can no longer be edited").format(doctype, name))

	doc.update({f: payload.get(f) for f in fields if payload.get(f) is not None})
	doc.save()
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
