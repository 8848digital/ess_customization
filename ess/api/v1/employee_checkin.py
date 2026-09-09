import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.employee_checkin import utils


@frappe.whitelist()
@api_endpoint
def get_list(limit: int | None = None, from_date: str | None = None, to_date: str | None = None):
	return utils.get_list(limit, from_date, to_date)


@frappe.whitelist(methods=["POST"])
@api_endpoint
def create(**payload):
	return utils.create(payload)
