"""The guard on the team endpoints.

`team.get_member` is the only endpoint in this app that takes an employee id
straight from the client, so `assert_manages` is what stands between a manager
and an arbitrary colleague's profile, balances and attendance history. These
test its branching directly — including the case the comment in
`approvals/utils.py` warns about, where two empty values must not compare equal.

    python -m unittest ess.tests.test_team_permissions      # pure logic only
    bench --site <site> run-tests --app ess                 # + the live check
"""

import unittest
from contextlib import contextmanager

import frappe

from ess.ess.customization.team import utils


@contextmanager
def _identity(session_employee, reports_to, roles=()):
	"""Swap the three facts `assert_manages` reads, and put them back after."""
	originals = (utils.session_employee, frappe.db, frappe.get_roles)
	utils.session_employee = lambda *a, **k: session_employee
	frappe.db = type("Db", (), {"get_value": staticmethod(lambda *a, **k: reports_to)})()
	frappe.get_roles = lambda *a, **k: list(roles)
	try:
		yield
	finally:
		utils.session_employee, frappe.db, frappe.get_roles = originals


class TestManages(unittest.TestCase):
	"""The decision, with no site. `frappe.throw` needs an initialised site to
	log, so the branching is tested through the predicate and the throw itself
	through `get_member` on a real site below."""

	def test_direct_report_is_allowed(self):
		with _identity(session_employee="HR-EMP-0001", reports_to="HR-EMP-0001"):
			self.assertTrue(utils.manages("HR-EMP-0002"))

	def test_someone_elses_report_is_refused(self):
		with _identity(session_employee="HR-EMP-0001", reports_to="HR-EMP-0009"):
			self.assertFalse(utils.manages("HR-EMP-0002"))

	def test_hr_manager_is_allowed(self):
		with _identity(session_employee="HR-EMP-0001", reports_to="HR-EMP-0009", roles=["HR Manager"]):
			self.assertTrue(utils.manages("HR-EMP-0002"))

	def test_two_empty_values_are_not_a_match(self):
		"""The subtle one: a user with no Employee record asking after an
		employee with no manager must be refused, not waved through because
		None == None."""
		with _identity(session_employee=None, reports_to=None):
			self.assertFalse(utils.manages("HR-EMP-0002"))

	def test_employee_with_no_manager_is_refused(self):
		with _identity(session_employee="HR-EMP-0001", reports_to=None):
			self.assertFalse(utils.manages("HR-EMP-0002"))


class TestTeamEndpointsAreBounded(unittest.TestCase):
	def test_get_member_refuses_a_non_report_on_a_real_site(self):
		"""The same refusal, against real data and a real session."""
		if not frappe.db:
			self.skipTest("needs a site: bench --site <site> run-tests --app ess")

		pair = frappe.get_all(
			"Employee",
			filters={"status": "Active", "user_id": ["is", "set"]},
			fields=["name", "user_id", "reports_to"],
			limit_page_length=2,
		)
		if len(pair) < 2:
			self.skipTest("needs two Active employees with user_id set")

		caller, other = pair
		if other.reports_to == caller.name:
			self.skipTest("the two employees found are manager and report")

		original = frappe.session.user
		try:
			frappe.set_user(caller.user_id)
			if "HR Manager" in frappe.get_roles():
				self.skipTest("caller is an HR Manager, which bypasses the guard by design")
			with self.assertRaises(frappe.PermissionError):
				utils.get_member(other.name)
		finally:
			frappe.set_user(original)

	def test_empty_team_returns_empty_rather_than_everyone(self):
		"""A user with no reports must get [] — never an unfiltered roster."""
		if not frappe.db:
			self.skipTest("needs a site: bench --site <site> run-tests --app ess")

		original = frappe.session.user
		try:
			frappe.set_user("Guest")
			self.assertEqual(utils.get_members(), [])
			self.assertEqual(utils.get_calendar("2026-09-01", "2026-09-30"), {"leaves": [], "attendance": []})
		finally:
			frappe.set_user(original)


class TestWorkspaceSignalMatchesTheInbox(unittest.TestCase):
	def test_a_user_with_a_non_empty_inbox_is_offered_the_team_workspace(self):
		"""The signal the client gates the Team workspace on must never say "no"
		to someone who has approvals waiting.

		This caught a real bug: `is_approver` first checked the Employee master's
		`leave_approver` / `expense_approver`, but `get_pending` filters the
		approver field on the DOCUMENT. A user named on live documents but on
		nobody's master scored False with a full inbox.
		"""
		if not frappe.db:
			self.skipTest("needs a site: bench --site <site> run-tests --app ess")

		from ess.ess.customization.approvals.utils import get_pending
		from ess.ess.customization.employee.utils import get_profile

		users = frappe.get_all(
			"Employee",
			filters={"status": "Active", "user_id": ["is", "set"]},
			pluck="user_id",
			limit_page_length=10,
		)
		if not users:
			self.skipTest("needs an Active employee with user_id set")

		original = frappe.session.user
		try:
			for user in users:
				frappe.set_user(user)
				pending = len(get_pending())
				if not pending:
					continue
				profile = get_profile()
				self.assertTrue(
					profile["team_size"] > 0 or profile["is_approver"],
					f"{user} has {pending} pending approvals but would be denied the Team workspace",
				)
		finally:
			frappe.set_user(original)


if __name__ == "__main__":
	unittest.main()
