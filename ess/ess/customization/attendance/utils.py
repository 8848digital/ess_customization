from ess.utils import list_for_employee

LIST_FIELDS = [
	"name",
	"employee",
	"attendance_date",
	"status",
	"working_hours",
	"in_time",
	"out_time",
	"leave_type",
]


def get_list(from_date=None, to_date=None, limit=None) -> list[dict]:
	"""Submitted attendance only — a draft row is not yet the payroll's answer."""
	filters = {"docstatus": 1}
	if from_date and to_date:
		filters["attendance_date"] = ["between", [from_date, to_date]]

	return list_for_employee(
		"Attendance",
		LIST_FIELDS,
		filters=filters,
		order_by="attendance_date desc",
		limit=limit,
	)
