import frappe

from ess.ess.customization.approvals.utils import is_approver
from ess.utils import require_employee_id

PROFILE_FIELDS = [
	"name",
	"employee_name",
	"user_id",
	"designation",
	"department",
	"branch",
	"company",
	"reports_to",
	"image",
	"cell_number",
	"personal_email",
	"date_of_joining",
	"holiday_list",
	"status",
	"leave_approver",
	"expense_approver",
]


def get_profile() -> dict:
	"""The signed-in user's own `Employee` record. Read-only (spec.md §6.12)."""
	profile = frappe.db.get_value("Employee", require_employee_id(), PROFILE_FIELDS, as_dict=True)
	# `reports_to` is a link to Employee; the client shows the manager's name.
	profile["reports_to_name"] = (
		frappe.db.get_value("Employee", profile.reports_to, "employee_name") if profile.reports_to else None
	)
	# leave_approver / expense_approver are Users, separate from reports_to and
	# independently mandatory on their doctypes (HR Settings can require them).
	# The client must show these, not reports_to_name, wherever it names who
	# approves a request — reports_to can be set while these are still empty,
	# and showing the manager's name there promises an approver the server
	# then refuses.
	profile["leave_approver_name"] = frappe.db.get_value("User", profile.leave_approver, "full_name") if profile.leave_approver else None
	profile["expense_approver_name"] = frappe.db.get_value("User", profile.expense_approver, "full_name") if profile.expense_approver else None

	# Whether to offer the Team workspace. Computed, not columns — deliberately
	# kept out of PROFILE_FIELDS, which test_api_contract checks against real
	# Employee columns.
	#
	# `is_approver` is asked separately from `team_size` because the two routes
	# into the approver's inbox are different fields: Leave and Expense carry
	# their own `leave_approver` / `expense_approver` (a **User**), while Advance
	# and Attendance Request have no approver field in HR and route by the
	# employee's `reports_to` (an **Employee**) — see KINDS in
	# ess/ess/customization/approvals/utils.py. Someone can be named approver on
	# colleagues who do not report to them, so team_size alone would hide the
	# Team workspace from a user whose inbox is not empty.
	#
	# The answer comes from the approvals module rather than being recomputed
	# here: it must match what get_pending actually filters on, which is the
	# approver field on the document, not on the Employee master.
	profile["team_size"] = frappe.db.count("Employee", {"reports_to": profile.name})
	profile["is_approver"] = is_approver()
	return profile
