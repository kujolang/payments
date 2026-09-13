# Conditional purchase cancellation

The trusted gateway supports optional programmatic cancellation of an unsubmitted purchase. It does not cancel provider-side financial actions, revoke credentials, refund a payment or release the permanent financial claim.

## Contract and access

Existing `inspect` still selects `kujo.payments.execution.inspect` version `1.0.0` and returns the same four fields. The explicit `inspect_revision` operation selects version `2.0.0` and adds an integer `revision`. All five existing canonical definition hashes remain unchanged; the new definition has its own pinned v2 identity. Default agent, Agents SDK and MCP projections still expose only request/status.

An installation must explicitly add `inspect_revision` and `cancel` to a trusted transport credential's allowed operations. Existing two-operation credentials remain denied these controls. The server owns the payer/tenant identity; callers cannot supply it. No provider credential is required by these operations.

1. Call `inspect_revision` with `{ "execution_id": "…" }` and no idempotency key.
2. Review the current status and revision.
3. Call `cancel` with `{ "execution_id": "…", "expected_revision": 2 }` and a nonempty unique idempotency key. The example revision is illustrative; use the actual returned integer.
4. On a conflict, timeout or uncertain completion, inspect fresh status. Do not reinterpret a failed keyed call with changed input. A newly reviewed cancellation requires a new key.

The import-only public client exports `purchase_inspect_revision(transport, execution_id)` and `purchase_cancel(transport, execution_id, expected_revision, idempotency_key)`. A custom v1 storage port remains usable for its old operations; cancellation requires an additional callable `cancel(scope, execution_id, expected_revision)` method with the SQLite implementation's atomic semantics.

## Atomic behavior

A single scoped SQLite compare-and-set transitions `awaiting_authorization` or `ready` to `closed` with reason `cancelled`, increments the revision and requires `claimed = 0`. It races on the same authoritative row as financial execution. Once the financial claim wins, cancellation fails; if cancellation wins, no financial claim can follow. Incident pause still permits cancellation in the live database. Quarantined recovery copies refuse cancellation and cannot acknowledge a change to the live payment.

Cancellation reuses the existing keyed cancel Ability. Its new journal entries additionally bind the payer scope, execution ID and exact revision using field-framed SHA-256 values. This does not rewrite Ability's legacy receipt digests or existing operation histories. Successful or replayed results are checked against the scoped cancelled row before acknowledgement.

Cancellation's state commit and Ability receipt completion are separate. A crash or failed audit/receipt write can leave a cancelled row and an unfinished invocation. Fresh inspection is authoritative. Exact retries of an incomplete cancellation may also return a failed response with its current domain summary; see [interrupted invocations](interrupted-invocations.md). This does not repair or reopen an Ability invocation. No cancellation path clears a financial claim or starts a provider call.

## Synthetic verification

`tests/network/cancellation_test.py` uses the actual authenticated gateway, native Kujo storage/approval/claim helpers and a separate non-deduplicating fake processor ledger. It covers unchanged v1 output, explicit v2 revisions, operation scopes, cross-tenant denial, invalid revisions, exact replay, changed-input replay denial, stale revisions, live pause, eight four-claim/four-cancel races, post-claim denial and a real quarantined recovery copy. Normal CI never moves money. Definition identity mutation tests cover all six pinned definitions.

These fixtures establish behavior for the declared SQLite deployment. They are not proof of arbitrary external stores, stale backup recovery, physical credential isolation or provider-side cancellation.
