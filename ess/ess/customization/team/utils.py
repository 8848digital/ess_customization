from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import getdate

from ess.ess.customization.approvals.utils import direct_reports, get_mine
from ess.ess.customization.attendance.utils import get_list as attendance_list
from ess.ess.customization.leave_balance.utils import get_balances
from ess.utils import session_employee

# The roster row — one line per report in the Members list.
ROSTER_FIELDS = [
	"name",
	"employee_name",
	"designation",
	"department",
	"image",
	"status",
]

# The member detail header. Deliberately not PROFILE_FIELDS: a manager has no
# business reading a report's `leave_approver` / `expense_approver` routing, and
# `personal_email` is the employee's own, not the company's.
MEMBER_FIELDS = [
	"name",
	"employee_name",
	"designation",
	"department",
	"branch",
	"company",
	"image",
	"status",
	"date_of_joining",
	"cell_number",
	"reports_to",
]

CALENDAR_LEAVE_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"leave_type",
	"from_date",
	"to_date",
	"half_day",
	"half_day_date",
]

CALENDAR_ATTENDANCE_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"attendance_date",
	"status",
]

# Attendance statuses a manager needs to see. A present day is not news.
CALENDAR_ATTENDANCE_STATUSES = ["Absent", "Half Day", "On Leave"]

# How far back a member's attendance strip reaches.
RECENT_ATTENDANCE_LIMIT = 30


def manages(employee: str) -> bool:
	"""Whether the signed-in user may read *employee*'s record.

	This is the only guard on the three team endpoints, and `get_member` is the
	one that takes an employee id straight from the client — so this is what
	stands between a manager and an arbitrary colleague's attendance history.
	`get_members` and `get_calendar` are bounded by `direct_reports()` instead,
	which never contains an id the caller did not earn.

	Scoped to `reports_to` on purpose, unlike `approvals.assert_can_approve`
	which also accepts the `leave_approver` / `expense_approver` fields. Being
	named approver on one request is consent to decide that request, not to
	browse the person's profile, balances and attendance. Such an approver still
	sees those requests in their inbox — that path is unchanged.

	A predicate rather than a bare `frappe.throw`, so the decision can be tested
	without a site the way `approvals._quantity` and `_status` already are; the
	throw is `assert_manages` below.
	"""
	manager = session_employee()
	# `manager` and `reports_to` can both be empty; that is not a match.
	if manager and frappe.db.get_value("Employee", employee, "reports_to") == manager:
		return True

	return "HR Manager" in frappe.get_roles()


def assert_manages(employee: str) -> None:
	if not manages(employee):
		frappe.throw(
			_("{0} does not report to you").format(employee),
			frappe.PermissionError,
		)


def get_members() -> list[dict]:
	"""The signed-in user's direct reports.

	`reports_to` is the definition of "my team" here — the same one
	`approvals.get_pending` uses for the kinds HR gives no approver field.
	"""
	reports = direct_reports()
	if not reports:
		return []

	return frappe.get_all(
		"Employee",
		filters={"name": ["in", reports]},
		fields=ROSTER_FIELDS,
		order_by="employee_name asc",
	)


def get_member(employee: str) -> dict:
	"""One report: who they are, what they have open, and how they stand.

	Every read below is the existing session-scoped util called with an explicit
	`employee` — there is no second copy of those queries here.
	"""
	assert_manages(employee)

	profile = frappe.db.get_value("Employee", employee, MEMBER_FIELDS, as_dict=True)
	if not profile:
		frappe.throw(_("Employee {0} not found").format(employee))

	return {
		"profile": profile,
		"open_requests": get_mine(employee=employee),
		"leave_balances": get_balances(employee=employee),
		"recent_attendance": attendance_list(limit=RECENT_ATTENDANCE_LIMIT, employee=employee),
	}


def get_calendar(from_date: str, to_date: str) -> dict:
	"""Who on the team is out between *from_date* and *to_date*.

	Leave comes back as RANGES, not one row per day: expanding a range into
	dates is shaping, which belongs in the client's repo (ADR-004), and a
	fortnight of leave is one row on the wire instead of fourteen.
	"""
	reports = direct_reports()
	if not reports:
		return {"leaves": [], "attendance": []}

	return {
		# ponytail: Approved leave only — a pending request is in the approver's
		# inbox, not yet a commitment to cover. Add "Open" to the status filter
		# if the product wants provisional absences shown on the calendar.
		"leaves": frappe.get_all(
			"Leave Application",
			filters={
				"employee": ["in", reports],
				"status": "Approved",
				"docstatus": 1,
				# Overlap, not containment: leave that starts before the window
				# or ends after it still occupies days inside it.
				"from_date": ["<=", to_date],
				"to_date": [">=", from_date],
			},
			fields=CALENDAR_LEAVE_FIELDS,
			order_by="from_date asc",
		),
		"attendance": frappe.get_all(
			"Attendance",
			filters={
				"employee": ["in", reports],
				"docstatus": 1,
				"status": ["in", CALENDAR_ATTENDANCE_STATUSES],
				"attendance_date": ["between", [from_date, to_date]],
			},
			fields=CALENDAR_ATTENDANCE_FIELDS,
			order_by="attendance_date asc",
		),
	}


def get_calendar_counts(from_date: str, to_date: str) -> dict[str, int]:
	"""Headcount per day, for the month grid.

	The grid only ever shows a number per cell — `get_calendar` above sends
	every leave/attendance row's name and type up front, which is a client-side
	convenience the grid doesn't need. This fetches the same rows but only the
	fields needed to count, and returns one int per date; the full detail is
	fetched separately (`get_calendar` called with `from_date == to_date`) once
	someone taps a day.
	"""
	reports = direct_reports()
	if not reports:
		return {}

	leaves = frappe.get_all(
		"Leave Application",
		filters={
			"employee": ["in", reports],
			"status": "Approved",
			"docstatus": 1,
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date],
		},
		fields=["employee", "from_date", "to_date"],
	)
	attendance = frappe.get_all(
		"Attendance",
		filters={
			"employee": ["in", reports],
			"docstatus": 1,
			"status": ["in", CALENDAR_ATTENDANCE_STATUSES],
			"attendance_date": ["between", [from_date, to_date]],
		},
		fields=["employee", "attendance_date"],
	)

	window_start, window_end = getdate(from_date), getdate(to_date)
	by_date: dict[str, set[str]] = {}
	for row in leaves:
		day = max(getdate(row.from_date), window_start)
		last = min(getdate(row.to_date), window_end)
		while day <= last:
			by_date.setdefault(day.isoformat(), set()).add(row.employee)
			day += timedelta(days=1)
	for row in attendance:
		by_date.setdefault(getdate(row.attendance_date).isoformat(), set()).add(row.employee)

	return {date: len(employees) for date, employees in by_date.items()}
