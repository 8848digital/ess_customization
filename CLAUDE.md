# CLAUDE.md — ESS Frappe backend

The Frappe app behind **ESS** (Employee Self-Service). It ships no doctypes of its
own: every endpoint is a thin read or write over **Frappe HR**'s doctypes, scoped
to the signed-in user's `Employee` record.

## The frontend lives in a separate repo

The web + React Native client is at **`/Users/ritik/projects/ESS`** — a separate
git repo, because this app must sit under `frappe-bench/apps/` for `bench` to find
it. Neither can be vendored into the other.

To work across both in one session, grant access to that path (this app's
folder-access request, or `/add-dir` in the CLI). Read its `CLAUDE.md` for the
client-side conventions.

**The contract between the two repos** is `packages/core/src/api/endpoints.ts`
over there and `ess/api/v1/` over here — the method names must match exactly, and
`APP` in that file must be the lowercase `'ess'` (it is the Python package Frappe
imports; `'ESS'` gives `AppNotInstalledError` on every call). The client's
`*.types.ts` files define the field names each endpoint returns, and the
`LIST_FIELDS` / `WRITE_FIELDS` constants here are built to match them. Change one
side, change the other in the same breath.

## Layout (follows the LBCP app's structure)

```
ess/api/v1/<module>.py                     thin @frappe.whitelist wrappers, nothing else
ess/api/v1/response_formatter.py           the response envelope + @api_endpoint
ess/ess/customization/<doctype>/utils.py   the actual logic
ess/utils.py                               session employee, list/insert helpers
ess/tests/test_api_contract.py             the one check that matters
```

`api/` and `customization/` are namespace packages — no `__init__.py`, same as LBCP.

## Rules

- **Every whitelisted method returns the envelope.** The client (`@8848digital/catalyst`
  → `apiFetch`) reads `raw.message` and hands back `envelope.data`, so an exception
  that escapes to Frappe's own handler produces a body with no `message` key and
  crashes the client before it can show the error. Always decorate with
  `@api_endpoint`, which also rolls back — Frappe only rolls back when the
  exception reaches *its* handler, and `@api_endpoint` swallows it first.
- **`employee` is never a parameter.** It is resolved from `frappe.session.user`
  via `require_employee_id()`. A client-supplied one would let any employee read
  and write against a colleague.
- **Writes copy an allow-list of fields**, never the whole payload — that is what
  keeps a request from setting `docstatus`, `approval_status`, or anything else
  the approver owns.
- **`hooks.py` sets `require_type_annotated_api_methods`**, so every whitelisted
  parameter needs a type annotation or Frappe raises before your function runs.
  That check sits *outside* `@api_endpoint`, so its errors bypass the envelope.
- **Frappe HR owns the workflow rules.** Leave Applications and Expense Claims are
  created as *drafts*: HR refuses to submit a Leave Application still `Open`, or a
  claim whose `approval_status` is `Draft`. The approver moves them, not the filer.
- Deliberate shortcuts are marked `# ponytail:` with the ceiling and the upgrade
  path. Two of them matter: Attendance Request and Employee Advance have no
  Rejected state in HR, so a rejection lands as Cancelled.

## Checks

```bash
bench --site ESS run-tests --app ess   # includes the schema check against HR
uvx ruff check ess/ && uvx ruff format --check ess/
```

`test_api_contract.py` asserts that every field name this app uses still exists on
its doctype. That is how this app breaks — an HR rename, not a logic bug — so run
it after any Frappe/HRMS upgrade.
