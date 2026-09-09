import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.holiday.utils import get_list as _get_list


@frappe.whitelist()
@api_endpoint
def get_list(year: int | None = None):
	return _get_list(year)
