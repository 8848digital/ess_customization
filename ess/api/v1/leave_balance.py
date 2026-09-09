import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.leave_balance.utils import get_balances as _get_balances


@frappe.whitelist()
@api_endpoint
def get_balances(on_date: str | None = None):
	return _get_balances(on_date)
