import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.attendance import utils


@frappe.whitelist()
@api_endpoint
def get_list(from_date: str | None = None, to_date: str | None = None, limit: int | None = None):
	return utils.get_list(from_date, to_date, limit)
