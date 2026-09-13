# Trusted embedding interfaces

The host constructs these per-service objects. Never deserialize callbacks, database handles, route definitions or configuration from caller input.

## Persistence

`sqlite_port(db)` supplies the `kujo.payment-store/v1` interface to application and gateway modules. They import no concrete database implementation. Its functions are:

- `execution_enabled()` — strict boolean advisory preflight for incident control; `claim` must enforce the same control atomically.
- `inspect(scope, execution_id)` — tenant/principal scoped authoritative row or null.
- `intake(scope, key_hash, request_digest, execution_id, intent)` — persist or resolve the same purchase/key; changed input conflicts.
- `save_preparation(scope, execution_id, revision, snapshot, digest, prepared_ref, now_ms)` — atomic immutable snapshot and private provider reference.
- `preparation_ref(scope, execution_id)` — private reference or null.
- `grant(scope, execution_id, revision, approval, snapshot_digest, invocation_id, issuer_ref, now_ms)` — store a host-verified issued Ability approval and advance ready atomically.
- `load_approval(scope, execution_id)` — retrieve the issued, unconsumed approval for an unclaimed ready execution, or null.
- `issued_approval_matches(scope, execution_id, approval)` — compare the entire stored issued object, including nonce, issuer evidence and approver; only unconsumed approvals match.
- `claim(scope, execution_id, revision, approval_id, binding_digest, snapshot_digest, invocation_id, now_ms)` — atomically consume approval and permanently reserve financial dispatch. Only the current successful return authorizes issuing the ephemeral permit.
- `record_observation(scope, execution_id, revision, evidence_id, digest, observation, event, receipt)` — append normalized evidence with state/receipt in one transaction; retain conflicts without replacing terminal results.
- `begin_ability(operation, key_digest, request_digest, invocation_id)` and `complete_ability(operation, key_digest, request_digest, receipt)` — Ability callback envelopes with durable operation-scoped replay state.
- `begin_provider_authorization(scope, execution_id)` — one winner for native approval/credential initiation; later calls may only observe it.
- `new_permit()` — a fresh, nonpersistent instance with `issue()`, `take()` and `close()`. Issue occurs only after a successful claim in this invocation. Take is atomic and succeeds once. Nothing in persisted state recreates it.

The SQLite port also provides optional `cancel(scope, execution_id, expected_revision)` and `inspect_request(scope, key_hash, request_digest)` methods for conditional cancellation and exact incomplete-request observation. They are checked only by their corresponding gateway paths; existing custom v1 stores are not silently required to implement them. See [cancellation](cancellation.md) and [interrupted invocations](interrupted-invocations.md).

A replacement store must pass real process contention, transactional rollback, stale-key, terminal-conflict and crash tests. The store is a privileged persistence port with application validation preconditions, not a public financial API. Native database ownership and underlying filesystem durability are deployment requirements.

## Gateway host callbacks

`authenticate(transport_context)` returns the trusted canonical principal or null. The transport owns authentication; model JSON cannot supply `transport_context`. `policy(definition, invocation, exposure)` returns the existing Ability decision. `audit(phase, invocation, payload)` must write a sanitized event and return the Ability audit envelope. Never serialize the entire callback arguments into telemetry. `clock_ms()` supplies a trusted integer clock. A persistent installation `namespace` gives deterministic invocation identities per authenticated operation/key. Principals must satisfy the [closed Payments/Ability compatibility profile](identity-compatibility.md); unsupported identities are rejected without truncation.

The default agent projection exposes request and inspect. Explicitly scoped programmatic callers may also use cancel and versioned inspect_revision. Keyed request replay preserves its original summary; inspect returns current state. If completion auditing fails after a handler produced a valid summary, the error includes that safe execution reference rather than implying the intent never existed.

## Privileged execution host callbacks

`policy(snapshot, invocation)` receives immutable terms; allow still requires one-use Ability approval in V1. `verify_issuer(issuer_ref, approval, invocation)` must consult the authenticated issuer's issued record and validate approver authority. Hash equality or a provider-approved status alone is insufficient. Full approval equality is checked again before consumption.

A registered confirmation rule provides `id`, `assurance` and `verify(snapshot, observation)`. It must independently correlate authenticated account/payee/route/transaction evidence with the exact charge. A final no-effect verdict additionally requires proof that the original sender is dead or its authority revoked. Merchant text, a redirect return and a provider's credential-issuance success are not payment confirmation. The fixture verifier queries its separate synthetic processor database; it is not a live-provider proof.

## Current limits

The public client imports no provider or storage modules. This embedding API alone does not isolate a malicious runtime. Scoped HTTP transport, a local operator issuer and synthetic OCI/Workcell profiles exist; production identity/approval installation, provider egress, selected-deployment validation and Link acceptance remain unfinished. The fixture's fixed clock, channels, issuer and audit callback must never be used for real funds.

## Private reconciliation host

The worker requires the canonical `installed.reconciliation_definition` and explicit `host.reconciliation_key` for claimed nonterminal work. It reuses `policy(snapshot, invocation)`, `audit` and `clock_ms` through actual Ability dispatch. Hosts must permit the observation Ability separately from financial execution; no consumed payment grant is reused. Exact-key retries and deliberately fresh observations differ. See [reconciliation](reconciliation.md). The storage v1 interface and public gateway operations are unchanged.
