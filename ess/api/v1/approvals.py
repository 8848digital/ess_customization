import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.approvals import utils


@frappe.whitelist()
@api_endpoint
def get_pending(limit: int = 50):
	return utils.get_pending(limit)


@frappe.whitelist()
@api_endpoint
def get_mine(limit: int = 50):
	return utils.get_mine(limit)


@frappe.whitelist(methods=["POST"])
@api_endpoint
def approve(kind: str, id: str, comment: str | None = None):
	return utils.act(kind, id, approve=True, comment=comment)


@frappe.whitelist(methods=["POST"])
@api_endpoint
def reject(kind: str, id: str, comment: str | None = None):
	return utils.act(kind, id, approve=False, comment=comment)
