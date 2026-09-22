import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.team import utils


@frappe.whitelist()
@api_endpoint
def get_members():
	return utils.get_members()


@frappe.whitelist()
@api_endpoint
def get_member(employee: str):
	return utils.get_member(employee)


@frappe.whitelist()
@api_endpoint
def get_calendar(from_date: str, to_date: str):
	return utils.get_calendar(from_date, to_date)
