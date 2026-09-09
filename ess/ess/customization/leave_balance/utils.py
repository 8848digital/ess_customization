from frappe.utils import flt, today
from hrms.hr.doctype.leave_application.leave_application import get_leave_details

from ess.utils import require_employee_id


def get_balances(on_date: str | None = None) -> list[dict]:
	"""Allowance per leave type for the period covering *on_date*.

	Carry-forward, encashment and leave-without-pay rules live in HR's ledger,
	so the numbers come straight from `get_leave_details` rather than being
	re-derived here — the device never recomputes them either (spec.md §6.6).
	"""
	details = get_leave_details(require_employee_id(), on_date or today())

	balances = []
	for leave_type, allocation in (details.get("leave_allocation") or {}).items():
		allocated = flt(allocation.get("total_leaves"))
		taken = flt(allocation.get("leaves_taken"))
		balances.append(
			{
				"leaveType": leave_type,
				"allocated": allocated,
				"taken": taken,
				"remaining": flt(allocation.get("remaining_leaves")),
				"usedPercent": round(taken / allocated * 100) if allocated else 0,
			}
		)

	return sorted(balances, key=lambda b: b["leaveType"])
