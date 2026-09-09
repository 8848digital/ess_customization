import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.user.helpers import get_access_api_token as _get_access_api_token


@frappe.whitelist(allow_guest=True, methods=["POST"])
@api_endpoint
def get_access_api_token(usr: str, pwd: str):
	return _get_access_api_token(usr, pwd)
