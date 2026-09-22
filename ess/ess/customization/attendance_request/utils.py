from frappe.utils import date_diff

from ess.utils import insert_for_employee, list_for_employee, update_for_employee

LIST_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"from_date",
	"to_date",
	"half_day",
	"half_day_date",
	"reason",
	"explanation",
	"docstatus",
	"creation",
]

WRITE_FIELDS = ("from_date", "to_date", "half_day", "half_day_date", "reason", "explanation")

# ponytail: Attendance Request has no `status` field in HR — approval is
# docstatus. So there is no "Rejected" state to map; a rejection lands as
# Cancelled (see ess.ess.customization.approvals.utils). Add a custom `status`
# Select (or a Workflow) on the doctype if the product needs the two told apart.
_STATUS_BY_DOCSTATUS = {0: "Open", 1: "Approved", 2: "Cancelled"}


def derive_status(docstatus) -> str:
	return _STATUS_BY_DOCSTATUS.get(docstatus, "Open")


def requested_days(from_date, to_date, half_day=None) -> float:
	if not from_date or not to_date:
		return 0
	days = date_diff(to_date, from_date) + 1
	return days - 0.5 if half_day else days


def get_list(limit=None) -> list[dict]:
	rows = list_for_employee(
		"Attendance Request",
		LIST_FIELDS,
		order_by="creation desc",
		limit=limit,
	)
	for row in rows:
		row["status"] = derive_status(row.pop("docstatus"))
		# The doctype has no posting_date; creation is when the employee filed it.
		row["posting_date"] = str(row.pop("creation"))[:10]
	return rows


def create(payload: dict) -> dict:
	"""Filed as a draft — submitting is the approver's action, not the filer's."""
	return insert_for_employee("Attendance Request", payload, WRITE_FIELDS)


def update(name: str, payload: dict) -> dict:
	"""Amend one's own still-Open request. Only the same fields create()
	accepts may change, and only before the approver has acted."""
	return update_for_employee("Attendance Request", name, payload, WRITE_FIELDS)
