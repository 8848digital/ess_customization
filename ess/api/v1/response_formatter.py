"""
Response envelope for the ESS clients.

The client (`@8848digital/catalyst` → `apiFetch`) reads `raw.message` as the
envelope and hands `envelope.data` to the caller, so every whitelisted method
in `ess.api.v1` must answer with `api_response(...)` — on failure too. An
exception that escapes to Frappe's own handler produces a body with no
`message` key, which crashes the client before it can show the error. That is
what `@api_endpoint` is for.
"""

import functools
from datetime import datetime
from typing import Any

import frappe
from frappe import _
from frappe.utils import strip_html


def api_response(
	success: bool = True,
	data: Any = None,
	message: str | None = None,
	error_code: str | None = None,
) -> dict[str, Any]:
	"""
	Generate standardized response format

	Args:
	        success: True for "success", False for "error"
	        data: Response data
	        message: Human-readable message
	        error_code: Error code for failures

	Returns:
	        Formatted response dictionary
	"""
	response = {
		"status": "success" if success else "error",
		"data": data,
		"message": message,
		"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
	}

	if error_code:
		response["error_code"] = error_code

	# Remove None values
	return {k: v for k, v in response.items() if v is not None}


def _fail(message: str, error_code: str, http_status: int) -> dict[str, Any]:
	# Frappe only rolls back when the exception reaches its handler. We swallow
	# it, so a half-written transaction would otherwise be committed.
	frappe.db.rollback()
	frappe.clear_messages()
	frappe.local.response.http_status_code = http_status
	return api_response(success=False, message=message, error_code=error_code)


def api_endpoint(fn):
	"""Wrap a whitelisted method so both its result and its failures reach the
	client inside the envelope above."""

	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		try:
			result = fn(*args, **kwargs)
		except frappe.AuthenticationError:
			return _fail(_("Invalid credentials"), "AUTHENTICATION_FAILED", 401)
		except frappe.PermissionError as e:
			return _fail(strip_html(str(e)) or _("Not permitted"), "PERMISSION_DENIED", 403)
		except frappe.ValidationError as e:
			# Covers frappe.throw() — those messages are written for the user.
			return _fail(strip_html(str(e)) or _("Invalid request"), "VALIDATION_ERROR", 400)
		except Exception:
			frappe.log_error(title=f"ESS API: {fn.__name__}", message=frappe.get_traceback())
			return _fail(_("Something went wrong"), "INTERNAL_ERROR", 500)

		# Helpers that need their own message/error_code build the envelope
		# themselves; everything else just returns its data.
		if isinstance(result, dict) and result.get("status") in ("success", "error"):
			return result
		return api_response(data=result)

	return wrapper


def handle_method_not_found():
	"""
	Custom handler for method not found errors
	"""
	return api_response(
		success=False,
		message=_("The requested API method does not exist"),
		error_code="METHOD_NOT_FOUND",
	)


def handle_permission_error(message: str | None = None):
	"""
	Custom handler for permission errors
	"""
	return api_response(
		success=False,
		message=message or _("You don't have permission to access this resource"),
		error_code="PERMISSION_DENIED",
	)
