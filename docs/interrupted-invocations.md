# Observing interrupted gateway invocations

An Ability invocation and a payment's domain state are separate records. The gateway can now recover a compact domain observation when an exact request or cancellation retry finds a live or interrupted Ability invocation whose receipt has not committed. It returns `ok: false`, `code: operation_incomplete`, and the current payment summary. This is an observation, not a replayed successful operation receipt.

For purchase requests, the lookup requires the authenticated payer/tenant scope, original request key and exact field-framed purchase terms to match both the durable request-key record and the execution. Integer money and expiration inputs remain mandatory. For cancellation, the existing cancellation journal binding already requires the same scope, execution and revision. Changed inputs cannot recover another operation's result.

The path runs only after Ability returns `ability_invocation_in_progress`, following its normal input, policy and audit checks. A policy denial, missing approval, failed audit or unrelated error does not enable observation. The gateway does not invoke the handler, finish a receipt, reset a claim, renew an authorization or call a provider. A concurrent original worker may still be live, so the response does not claim that an invocation crashed or that execution has stopped.

## Caller behavior

Keep the original purchase reference, input and request key. If a retry returns a summary with `operation_incomplete`, retain its execution ID and use fresh status inspection. The public HTTP client preserves the safe summary from a validated HTTP 409 response with its normalized `gateway_rejected` code. Other failure status codes cannot provide a recovery observation. The optional SDK and MCP integrations retain the observation while marking the tool call failed; their examples and the Dispatch observer use fresh status before continuing. Do not treat `ok: false` as evidence that no purchase exists or that no payment can occur.

When the crash happened before intake committed, there is no authoritative execution to return. The gateway retains the failure without inventing an ID or admitting a new intent. Successful completed request replays still return their original operation result; only fresh status or the explicitly incomplete observation reports current state.

A custom storage port may add the optional `inspect_request(scope, key_hash, request_digest)` read operation. The SQLite implementation joins the request key to its execution with matching scope and request digest. Older custom ports preserve their previous behavior and receive no automatic recovery capability.

## Remaining recovery work

This does not repair the Ability journal, retire abandoned pre-intake invocations, re-enter pre-claim execution, coordinate provider/vault backups or merge restored financial history. The permanent financial claim and quarantined recovery-copy restrictions remain unchanged. Those broader release gates remain open.

## Synthetic evidence

`tests/network/interrupted_gateway_test.py` kills actual Kujo processes before intake, after intake, before receipt completion, before cancellation and after cancellation. Four concurrent retries must observe without changing the journal. Fresh-process policy, audit and authentication denial, changed purchase terms/revisions, old-store fallback and real authenticated HTTP restarts are exercised. Incomplete receipts remain incomplete and no financial claim is created. Existing execution crash and non-deduplicating processor tests continue to cover the separate financial boundary. No live provider or money is involved.
