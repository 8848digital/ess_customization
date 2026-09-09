import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.attendance_request import utils


@frappe.whitelist()
@api_endpoint
def get_list(limit: int | None = None):
	return utils.get_list(limit)


@frappe.whitelist(methods=["POST"])
@api_endpoint
def create(**payload):
	return utils.create(payload)
