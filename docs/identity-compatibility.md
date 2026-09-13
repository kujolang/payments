# Payments identity compatibility profile

Payments preserves Ability's existing v1 approvals, receipts and journal identities. It admits canonical definitions through the separately named `sha256-canonical-json-v2` digest and binds payment terms through its field-framed domain digests. This is an explicit application profile, not a general repair of Ability's historical nested serializer.

## Accepted principals

Payment principals contain exactly three string fields: `type`, `id` and `tenant_id`. The canonical domain schema permits ASCII identifiers of at most 128 characters. The installed Ability package imposes an additional identity constraint: its current `type` limit is 64 characters. Payments validates the intersection through `ability_principal_compatible`, using Ability's public invocation validator. It does not silently trim identifiers, discard claims or substitute a hash algorithm.

The validation probe is never registered, invoked or persisted as an operation. Service startup rejects an incompatible credential principal before creating/opening the payment journal. Embedded gateway calls reject it before invocation. Execution invocation construction and private operator authority matching also require the closed compatible profile. Nested claims belong in host policy/identity infrastructure; they cannot enter this profile's approval hashing path.

Domain schema IDs and all canonical Ability definitions remain unchanged. The longer type names were already rejected by Ability at invocation time; the new checks report the incompatibility earlier. No old receipt or claim is rewritten, no new provider limitation is introduced into intent semantics, and no upstream Ability runtime change is required.

## Ownership and evidence

| Identity path | Authority and current protection | Verification and limit |
| --- | --- | --- |
| Definition identity | Exact ID/version plus compiled v2 canonical digest | 278 independent definition mutations; frozen historical v1 execution digest retained |
| Principal scope | Closed flat profile and field-framed tenant/type/id | Independent Python/VM/interpreter vectors and incompatible/nested-profile denial |
| Request key | Ability's existing flat principal/key digest | Actual gateway/store boundary compared with independent canonical JSON SHA-256; Unicode/escaped/boundary-length keys covered |
| Request terms and incomplete observations | Payment-specific field-framed terms plus durable request-key/execution join | Changed-input replay and real interrupted-gateway fixtures; no trust in a legacy nested request fingerprint alone |
| Cancellation key | New cancellation namespace and principal scope frame around the existing Ability key | Independent expected keys through actual cancellation dispatch; exact input/revision replay tests |
| Execution approval | Flat execution/snapshot input and flat compatible principal; immutable snapshot and exact stored issuer approval | Independent expected approval hashes plus nine binding mutation/expiry cases; no arbitrary nested approval-input claim |
| Stored receipts | Existing v1 shape and scoped authoritative payment state | Actual request replay and retained v1 principal/receipt records; no v2 receipt emission or dual-read migration |
| Reconciliation declaration | Canonical definition is pinned; current worker uses private observation functions | Declaration identity does not prove Ability dispatch; that integration remains open |
| SDK/MCP/Dispatch | Optional client projections; server owns authority and journal checks | Separate pinned dependencies and real process fixtures; metadata does not grant financial authority |

`scripts/flat_identity_vectors.py` independently produces 36 combinations of principal and request key. `tests/flat_identity_scope.kujo` compares approval, principal, request-key and cancellation-key hashes and executes real request/cancel/replay paths while retaining v1 receipts. `tests/network/identity_profile_test.py` runs those fixtures in both runtime modes and verifies that incompatible service configurations fail before storage initialization. These fixtures use no provider, credential or financial action.

## Remaining work

The known general Ability nested v1 serializer issue remains unresolved upstream. Current proof is scoped to the closed Payments paths above. A general migration must explicitly version its algorithms/operational schemas, retain historical receipts for observation, deny cross-version approval reuse and preserve permanent financial claims. This milestone does not implement that migration, the remaining reconciliation Ability dispatch, interrupted execution re-entry or coordinated backup/history recovery. Those gates must be reviewed from their own evidence before release.
