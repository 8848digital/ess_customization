import frappe

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
]


def get_profile() -> dict:
	"""The signed-in user's own `Employee` record. Read-only (spec.md §6.12)."""
	profile = frappe.db.get_value("Employee", require_employee_id(), PROFILE_FIELDS, as_dict=True)
	# `reports_to` is a link to Employee; the client shows the manager's name.
	profile["reports_to_name"] = (
		frappe.db.get_value("Employee", profile.reports_to, "employee_name") if profile.reports_to else None
	)
	return profile
