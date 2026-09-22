import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.expense_claim import utils


@frappe.whitelist()
@api_endpoint
def get_list(limit: int | None = None):
	return utils.get_list(limit)


@frappe.whitelist()
@api_endpoint
def get_types():
	return utils.get_types()


@frappe.whitelist()
@api_endpoint
def get_detail(name: str):
	return utils.get_detail(name)


@frappe.whitelist(methods=["POST"])
@api_endpoint
def create(**payload):
	return utils.create(payload)


@frappe.whitelist(methods=["POST"])
@api_endpoint
def upload_receipt(file_name: str, content: str, mime_type: str | None = None):
	return utils.upload_receipt(file_name, content, mime_type)


@frappe.whitelist(methods=["POST"])
@api_endpoint
def update(name: str, **payload):
	return utils.update(name, payload)
