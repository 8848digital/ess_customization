from ess.utils import insert_for_employee, list_for_employee, update_for_employee

LIST_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"purpose",
	"advance_amount",
	"paid_amount",
	"claimed_amount",
	"return_amount",
	"advance_account",
	"posting_date",
	"status",
]

WRITE_FIELDS = ("purpose", "advance_amount", "posting_date", "company", "advance_account")


def get_list(limit=None) -> list[dict]:
	rows = list_for_employee(
		"Employee Advance",
		LIST_FIELDS,
		filters={"docstatus": ["<", 2]},
		order_by="posting_date desc",
		limit=limit,
	)
	return rows


def create(payload: dict) -> dict:
	return insert_for_employee("Employee Advance", payload, WRITE_FIELDS)


def update(name: str, payload: dict) -> dict:
	"""Amend one's own still-Draft advance request. Only the same fields
	create() accepts may change, and only before it's been actioned."""
	return update_for_employee("Employee Advance", name, payload, WRITE_FIELDS)
