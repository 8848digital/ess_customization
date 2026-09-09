import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.employee.utils import get_profile as _get_profile


@frappe.whitelist()
@api_endpoint
def get_profile():
	return _get_profile()
