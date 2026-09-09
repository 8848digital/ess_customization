import frappe
from frappe.auth import LoginManager

from ess.api.v1.response_formatter import api_response


def get_access_api_token(usr: str, pwd: str) -> dict:
	"""
	Validate credentials and return an API token for the given user.
	Generates API key/secret if not already set.
	"""

	if not frappe.db.exists("User", usr):
		return api_response(
			success=False,
			message="User does not exist",
			error_code="USER_NOT_FOUND",
		)

	# 2. Password verification. LoginManager.authenticate() is what /api/method/login
	# itself uses, so this endpoint inherits its brute-force tracking (per IP and per
	# user) and its disabled-user check rather than re-implementing either.
	login_manager = LoginManager()
	login_manager.authenticate(user=usr, pwd=pwd)  # raises frappe.AuthenticationError on failure

	# 3. Fetch user & resolve token (generate keys only when absent)
	user = frappe.get_doc("User", usr)
	if not user.api_key:
		api_key_secret = generate_keys(usr)
		token = f"token {api_key_secret['api_key']}:{api_key_secret['api_secret']}"
	else:
		token = f"token {user.api_key}:{user.get_password('api_secret')}"

	data = {
		"access_token": token,
		"user": {
			"email": user.name,
			"username": user.username,
		},
	}
	return api_response(data=data, message="User logged in successfully")


def generate_keys(usr: str) -> dict:
	"""
	Generate and persist API key + secret for *usr*.
	Regenerates the secret on every call; preserves an existing api_key.

	Returns:
	    dict with 'api_key' and 'api_secret' (plain-text, before hashing).
	"""
	user = frappe.get_doc("User", usr)

	api_secret = frappe.generate_hash(length=15)

	if not user.api_key:
		user.api_key = frappe.generate_hash(length=15)

	user.api_secret = api_secret
	user.save(ignore_permissions=True)

	return {"api_key": user.api_key, "api_secret": api_secret}
