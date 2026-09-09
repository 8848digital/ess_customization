import frappe
from frappe import _
from frappe.utils import cint

LIST_FIELDS = [
	"name",
	"subject",
	"email_content",
	"document_type",
	"document_name",
	"type",
	"for_user",
	"read",
	"creation",
]


def get_list(limit=50) -> list[dict]:
	return frappe.get_all(
		"Notification Log",
		filters={"for_user": frappe.session.user},
		fields=LIST_FIELDS,
		order_by="creation desc",
		limit_page_length=cint(limit),
	)


def mark_read(name: str) -> dict:
	if frappe.db.get_value("Notification Log", name, "for_user") != frappe.session.user:
		frappe.throw(_("That notification is not yours"), frappe.PermissionError)

	frappe.db.set_value("Notification Log", name, "read", 1)
	return {"success": True}

