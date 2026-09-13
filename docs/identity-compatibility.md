# Payments identity compatibility profile

Payments preserves Ability's existing v1 approvals, receipts and journal identities. It admits canonical definitions through the separately named `sha256-canonical-json-v2` digest and binds payment terms through its field-framed domain digests. This is an explicit application profile, not a general repair of Ability's historical nested serializer.

## Accepted principals

Payment principals contain exactly three string fields: `type`, `id` and `tenant_id`. The canonical domain schema permits ASCII identifiers of at most 128 characters. The installed Ability package imposes an additional identity constraint: its current `type` limit is 64 characters. Payments validates the intersection through `ability_principal_compatible`, using Ability's public invocation validator. It does not silently trim identifiers, discard claims or substitute a hash algorithm.

The validation probe is never registered, invoked or persisted as an operation. Service startup rejects an incompatible credential principal before creating/opening the payment journal. Embedded gateway calls reject it before invocation. All application lifecycle entry points and the bounded worker reject incompatible principals before consulting the store, including preparation, provider authorization, observation acceptance, internal reconciliation and already-claimed/terminal fast paths. Private review/delivery uses the same check before lookup. Execution invocation construction and private operator authority matching also require the closed compatible profile. Nested claims belong in host policy/identity infrastructure; they cannot enter this profile's approval hashing path.

Domain schema IDs and all canonical Ability definitions remain unchanged. The longer type names were already rejected by Ability at invocation time; the new checks report the incompatibility earlier. No old receipt or claim is rewritten, no new provider limitation is introduced into intent semantics, and no upstream Ability runtime change is required.

## Ownership and evidence

| Identity path | Authority and current protection | Verification and limit |
| --- | --- | --- |
| Definition identity | Exact ID/version plus compiled v2 canonical digest | 278 independent definition mutations; frozen historical v1 execution digest retained |
| Principal scope | Closed flat profile and field-framed tenant/type/id | Independent Python/VM/interpreter vectors and incompatible/nested-profile denial |
| Request key | Ability's existing flat principal/key digest | Actual gateway/store boundary compared with independent canonical JSON SHA-256; Unicode/escaped/boundary-length keys covered |
| Request terms and incomplete observations | Payment-specific field-framed terms plus durable request-key/execution join | Changed-input replay and real interrupted-gateway fixtures; no trust in a legacy nested request fingerprint alone |
| Cancellation key | New cancellation namespace and principal scope frame around the existing Ability key | Independent expected keys through actual cancellation dispatch; exact input/revision replay tests |
| Embedded lifecycle and worker | Closed compatible principal checked before store/provider access | 110 malformed, extra-claim and incompatible-length cases across ten entry points, plus a supported-principal storage control; existing full lifecycle tests exercise admitted operations |
| Execution approval | Flat execution/snapshot input and flat compatible principal; immutable snapshot and exact stored issuer approval | Independent expected approval hashes plus nine binding mutation/expiry cases; no arbitrary nested approval-input claim |
| Stored receipts | Existing v1 shape and scoped authoritative payment state | Actual request replay and retained v1 principal/receipt records; no v2 receipt emission or dual-read migration |
| Reconciliation dispatch | Canonical keyed Ability, closed principal and field-framed scope/execution/snapshot store binding | Actual private dispatch and keyed replay; see [reconciliation](reconciliation.md) |
| SDK/MCP/Dispatch | Optional client projections; server owns authority and journal checks | Separate pinned dependencies and real process fixtures; metadata does not grant financial authority |

`scripts/flat_identity_vectors.py` independently produces 36 combinations of principal and request key. `tests/flat_identity_scope.kujo` compares approval, principal, request-key and cancellation-key hashes and executes real request/cancel/replay paths while retaining v1 receipts. `tests/network/identity_profile_test.py` runs those fixtures in both runtime modes and verifies that incompatible service configurations fail before storage initialization. These fixtures use no provider, credential or financial action.

## Embedded admission regression

The earlier gateway and execution-invocation checks did not cover every embedded path. For example, preparation and provider authorization derived scope from `type`, `id` and `tenant_id` while passing the caller principal onward; extra claims could be silently ignored for the lookup. Review and terminal-state shortcuts also needed admission before reading. These are trusted embedding functions, not new agent or HTTP endpoints; the authenticated gateway already rejected the malformed profiles. The fix makes embedding behavior consistent rather than granting authorization to a principal supplied by an untrusted process.

`tests/application_identity.kujo` exercises eleven invalid principal shapes across preparation, provider authorization, grant, observation acceptance, internal reconciliation, execution, worker, review, review-delivery and canonical reconciliation. A real SQLite counter detects any attempted store inspection. Every case must return `unsupported_principal` without storage access; a valid principal is a positive control. Existing execution/operator/provider tests cover valid financial lifecycle behavior. Pure field-framing/hash utilities remain deterministic encoders, not authentication/admission APIs; their historical outputs and all Ability receipts remain unchanged.

## Compatibility decision for the frozen V1 profile

The Payments-specific audit selects the existing restricted profile. A general Ability v1-to-v2 journal migration is not a prerequisite for this profile: replacing those hashes would change historical identities without adding a necessary payment authorization boundary. This decision applies only to the six definitions pinned in `src/identity/canonical.kujo`, the closed principal profile, the current application/store paths and the pinned Ability dependency. It does not repair or approve arbitrary uses of Ability v1.

The relevant distinction is between three uses of a digest:

1. **Definition admission:** the application checks the complete definition with Ability's explicitly named v2 algorithm before registering or dispatching it. The legacy definition digest retained inside an Ability receipt cannot independently identify the permitted schema. The frozen collision fixture proves that a changed definition with the same legacy digest is rejected.
2. **Consequential approval:** Ability hashes the flat execution input and flat principal separately, then hashes the flat binding containing those digests. Execution also requires the exact locally issued approval, an immutable payment snapshot, a permanent financial claim and a newly issued process-local dispatch permit. The runtime's nested idempotency request digest is not the approval binding and cannot issue that permit.
3. **Operation replay:** Ability's keyed request digest wraps input and principal in a nested object, even when the input itself is flat. Therefore this audit does **not** call that request digest collision-resistant. Request replay must pass the stored payment-term postcondition; incomplete request observations require the scoped key and independent term binding. Cancellation and reconciliation add their own scoped action bindings before journal access. Inspect operations are intrinsic reads of scoped current state. Execution uses an execution-derived key and checks permanent claims before dispatch; replay cannot recreate a permit. An ambiguous or abandoned invocation remains unavailable for re-entry.

Policy and preflight audit execute before Ability's replay decision (`kennel_packages/ability/src/runtime.kujo`). Payments does not accept a caller-supplied request approval through the gateway. A replayed operation receipt is historical evidence, not fresh financial authorization or settlement evidence. Failed receipts can remain historical failures when a reused key has different terms; they cannot authorize or acknowledge a new purchase. Financial state and its independently bound evidence remain authoritative.

The supported store, host policy and credential executor are trusted components. This decision does not permit importing arbitrary receipts, editing journal rows, reopening claims, admitting nested principal claims or using a legacy digest alone in an external verifier. Such changes require a new compatibility review. Any change to canonical definitions, Ability serialization, runtime behavior, persistence or approval inputs must rerun the independent vectors and actual replay/claim fixtures before release. A future general migration must explicitly version its algorithms and operational schemas, retain historical receipts for observation, deny cross-version approval reuse and preserve permanent financial claims.

## Remaining work

The known general Ability nested v1 serializer issue remains unresolved upstream. The scoped compatibility decision above does not implement that migration, interrupted execution re-entry or coordinated backup/history recovery. The latter two remain separate Payments release gates. Provider identity, settlement evidence and deployment isolation also require their own acceptance evidence; this compatibility decision does not approve a real-money release.
