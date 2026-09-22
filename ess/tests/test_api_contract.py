"""The one check that fails when this app stops matching Frappe HR.

Every endpoint in `ess.api.v1` is a thin read or write over HR's own doctypes,
so the way this breaks is a renamed column or a stale entry in the approvals
table — not a logic bug. That is what these test.

    python -m unittest ess.tests.test_api_contract          # pure logic only
    bench --site <site> run-tests --app ess                 # + the schema check
"""

import importlib
import unittest

import frappe

from ess.ess.customization.approvals.utils import KINDS, _quantity, _status

REQUIRED_KEYS = {
	"doctype",
	"approver_field",
	"pending",
	"quantity_field",
	"posted_on_field",
	"status_field",
	"extra_fields",
	"approved",
	"rejected",
	"cancel_on_reject",
}


def _utils(module: str):
	return importlib.import_module(f"ess.ess.customization.{module}.utils")


def _configured_fields() -> dict[str, list[str]]:
	"""Every doctype field this app names, by doctype."""
	fields = {
		"Employee": _utils("employee").PROFILE_FIELDS,
		"Attendance": _utils("attendance").LIST_FIELDS,
		"Notification Log": _utils("notification_log").LIST_FIELDS,
	}
	for doctype, module in (
		("Employee Checkin", "employee_checkin"),
		("Attendance Request", "attendance_request"),
		("Leave Application", "leave_application"),
		("Expense Claim", "expense_claim"),
		("Employee Advance", "employee_advance"),
	):
		utils = _utils(module)
		fields[doctype] = [*utils.LIST_FIELDS, *utils.WRITE_FIELDS]

	# Child tables, named only by the two detail endpoints and the type picker.
	fields["Expense Claim Detail"] = _utils("expense_claim").DETAIL_LINE_FIELDS
	fields["Expense Taxes and Charges"] = _utils("expense_claim").DETAIL_TAX_FIELDS
	fields["Expense Claim Account"] = _utils("expense_claim").TYPE_ACCOUNT_FIELDS

	for config in KINDS.values():
		fields.setdefault(config["doctype"], []).extend(
			f
			for f in (
				config["quantity_field"],
				config["status_field"],
				config["posted_on_field"],
				config["approver_field"],
				*config["extra_fields"],
				*config["pending"],
				*config["approved"],
				*config["rejected"],
			)
			if f
		)

	return fields


class TestApiContract(unittest.TestCase):
	def test_every_named_field_exists_on_its_doctype(self):
		"""Catches an HR rename before it 500s in a user's list view."""
		if not frappe.db:
			self.skipTest("needs a site: bench --site <site> run-tests --app ess")

		for doctype, fields in _configured_fields().items():
			columns = set(frappe.db.get_table_columns(doctype))
			for field in dict.fromkeys(fields):
				self.assertIn(field, columns, f"{doctype}.{field}")

	def test_every_approval_kind_is_fully_configured(self):
		self.assertEqual(set(KINDS), {"leave", "expense", "advance", "attendance"})
		for kind, config in KINDS.items():
			self.assertEqual(set(config), REQUIRED_KEYS, kind)
			# A kind with no quantity column must be derivable from its date range.
			if not config["quantity_field"]:
				self.assertTrue({"from_date", "to_date"} <= set(config["extra_fields"]), kind)

	def test_attendance_quantity_and_status_are_derived(self):
		config = KINDS["attendance"]
		row = {"from_date": "2026-09-01", "to_date": "2026-09-03", "half_day": 0, "docstatus": 0}
		self.assertEqual(_quantity(row, config), 3)
		self.assertEqual(_status(row, config), "Open")

		row["half_day"] = 1
		self.assertEqual(_quantity(row, config), 2.5)
		row["docstatus"] = 2
		self.assertEqual(_status(row, config), "Cancelled")

	def test_leave_quantity_and_status_come_from_columns(self):
		config = KINDS["leave"]
		row = {"total_leave_days": 1.5, "status": "Open"}
		self.assertEqual(_quantity(row, config), 1.5)
		self.assertEqual(_status(row, config), "Open")


if __name__ == "__main__":
	unittest.main()
