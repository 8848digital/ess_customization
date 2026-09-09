from ess.utils import insert_for_employee, list_for_employee

LIST_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"time",
	"log_type",
	"device_id",
	"latitude",
	"longitude",
]

# What a punch may carry. `time` is the moment of the TAP, not of the push, so
# the client sends it and the server does not stamp its own.
WRITE_FIELDS = ("time", "log_type", "device_id", "latitude", "longitude")


def get_list(limit=None, from_date=None, to_date=None) -> list[dict]:
	filters = {}
	if from_date and to_date:
		filters["time"] = ["between", [from_date, to_date]]

	rows = list_for_employee(
		"Employee Checkin",
		LIST_FIELDS,
		filters=filters,
		order_by="time desc",
		limit=limit,
	)
	for row in rows:
		# Device-only columns: Employee Checkin stores coordinates, not a
		# resolved place name, and never a reason the fix failed.
		row["location_name"] = None
		row["location_error"] = None
	return rows


def create(payload: dict) -> dict:
	return insert_for_employee("Employee Checkin", payload, WRITE_FIELDS)
