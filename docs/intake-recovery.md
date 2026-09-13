# Recovering a stalled intake

A trusted caller can issue a deliberately new `request` operation with a new idempotency key while retaining the original payer, purchase reference and exact purchase input. This uses existing Ability and intake contracts. It does not restart or repair the original invocation and grants no permission to move funds.

The SQLite intake store has an atomic uniqueness constraint on `(scope, purchase_ref)`. Different request keys for the same business purchase resolve to one execution only when the payment-specific request digest matches. The winner's persisted intent and expiration remain authoritative. A late original handler resolves to that same execution; it does not replace terms, extend expiry or create another payment.

## Trusted-host procedure

1. Retain the original request input, purchase reference and key outside model-generated reconstruction. Authenticate as the same payer/tenant through the original installation.
2. Retry the exact original key or inspect an already known execution. A completed response can be replayed; `operation_incomplete` with an execution ID means status can already be tracked. Prefer status when that is sufficient.
3. If intake completion is still required, deliberately allocate and retain a new operation key. Send the exact original input with the same `purchase_ref`. This step must not invent a new purchase reference or silently change terms to evade a conflict.
4. On success, track the returned execution ID with fresh status. Its existing terms, expiry and state prevail. Continue ordinary separate authorization and execution; the request response is not a payment approval.
5. If input conflicts or the new operation is itself interrupted, inspect known state and retain both keys. Do not erase journals, clear claims or repeatedly generate new keys in a loop. Escalate unavailable/corrupt storage to the operator.

A new operation undergoes normal authentication, Ability input/policy/audit checks and durable request admission. It is not a retry of a financial provider command. Existing public `purchase_request(transport, input, idempotency_key)` already permits this explicit host composition; default agent/harness projections retain their stable keys and do not automatically start replacement operations.

Before any intake commits, the server has no durable payment terms to compare against another new key. Retaining the exact original input is therefore a caller responsibility, not a server claim about an absent record. Once the business purchase exists, changed-input admission fails. Every eventual financial execution still requires its own immutable prepared terms and exact approval.

## Scope and limits

This handles interrupted intake, including a crash before a domain execution exists, without implementing a second workflow engine or modifying Ability's unfinished journal. An abandoned original receipt remains unfinished; its exact retry can recover a domain observation only if the original request-key mapping committed. A pre-intake kill leaves no original key mapping even after another key admits that business purchase; track the ID returned by the new request. A live original can finish its own receipt through normal Ability processing, including a timed-out receipt when its handler exceeded the deadline. A failed operation receipt does not reverse the one admitted payment.

This does not recover a pre-claim financial execution invocation, renew an approval, unblock an expired purchase, restore missing provider/vault state, merge backups or re-enable quarantined copies for spending. Never use a new business purchase reference to work around an ambiguous financial action. An uncertain claimed action must be reconciled.

The guarantee depends on the single authoritative store's durable business-reference uniqueness and exact term binding. Custom stores must establish equivalent transactional behavior. A stale, independently writable replica cannot provide this guarantee. Transport authentication, retained input integrity, scheduling, rate limits and storage durability remain host/deployment responsibilities.

## Evidence

`tests/network/interrupted_gateway_test.py` supervises actual Kujo gateway/Ability processes at three boundaries: before intake, after intake and before Ability receipt completion. Each boundary runs with both a killed original and a held original that later resumes. Four fresh-key contenders must resolve one execution; changed terms must fail; intent and expiration must remain unchanged; no approval or financial claim is created. The original unfinished receipt is preserved after a kill and finishes through normal Ability processing only when the live original resumes; delayed handlers retain timeout failure even though the single domain execution exists. Existing exact-key policy/audit/authentication and HTTP restart cases run alongside these recovery cases. Tests are synthetic and move no funds.
