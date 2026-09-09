import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.notification_log import utils


@frappe.whitelist()
@api_endpoint
def get_list(limit: int = 50):
	return utils.get_list(limit)


@frappe.whitelist(methods=["POST"])
@api_endpoint
def mark_read(name: str):
	return utils.mark_read(name)

