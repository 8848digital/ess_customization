import frappe

from ess.api.v1.response_formatter import api_endpoint
from ess.ess.customization.salary_slip import utils


@frappe.whitelist()
@api_endpoint
def get_list(limit: int | None = None):
	return utils.get_list(limit)


@frappe.whitelist()
@api_endpoint
def download_pdf(name: str):
	return utils.download_pdf(name)


@frappe.whitelist()
@api_endpoint
def get_detail(name: str):
	return utils.get_detail(name)
