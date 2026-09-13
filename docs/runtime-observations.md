# Runtime observation: chained dictionary assignment

Kujo 1.4.0, source checkout d054d87a9919544d4ac8eeb4b2ecc86500e71cb8, observed 2026-09-12.

`kujo run tests/runtime/nested_assignment_context_repro.kujo` exits zero and prints `minor:5500` after assigning `changed["charge"]["minor"] = 5501`. The interpreter rejects the same file with `Complex index assignment not yet supported`. The smaller `nested_assignment_repro.kujo` produces VM `Stack underflow` and the same interpreter rejection. This is context-dependent VM behavior, not a claim that the language supports nested assignment.

Payments uses explicit replacement of the nested dictionary. Its malicious-input tests assert the resulting behavior; they do not depend on chained mutation. Diagnostic reproducers are excluded from the normal passing test runner. The upstream runtime issue is unresolved; no Kujo source was modified by this implementation milestone.


## Wrapped provider callback disagreement

`tests/runtime/wrapped_provider_vm_repro.kujo` is a reduced diagnostic excluded from normal passing tests. On the local Kujo 1.4.0 binary, its VM execution prints a provider deadline of 1800, skips the wrapper's post-call value output, produces reconciliation_required and exits 4 at the expected-succeeded assertion. The interpreter prints the successful native observation, produces succeeded and exits 0. The same snapshot, fixture ledger, approval and source are used in fresh databases. The underlying runtime cause is not established; no upstream runtime changes were made. This differs from the earlier chained-assignment diagnostic.

The passing deadline test checks the expiry directly inside the fixture provider instead of adding this wrapper. Link and private operator paths remain interpreter-required; this does not justify a general VM equivalence claim. See docs/evidence/2026-09-12-wrapped-vm.log and 2026-09-12-wrapped-interpreter.log.

## Ability v1 nested digest collision observed during SDK integration

At pinned Ability `e5a74803c822de79e934d2bea82d615d8be3bbee` with the local Kujo 1.4.0 binary, `tests/runtime/ability_nested_digest_repro.kujo` produces identical v1 digests for nested inputs differing only in purchase purpose. Its canonical output drops the `input` object and becomes `{"id":"payer","principal":{"id":"payer"}}` for both cases. Both local VM and interpreter reproduce this; the v2 helper distinguishes the same inputs. This is evidence about the pinned helper/runtime combination, not an established root cause or permission to change all existing v1 identities.

The SDK integration exposed the consequence through actual HTTP: a changed purchase using the same request key received the earlier success summary. Payments now checks its persisted payment-specific field binding before acknowledging any successful or audit-failed replay summary. Changed purchase reference, merchant, amount mode/minor/currency, purpose, profile, expiration and optional preferences are rejected; old exact replays remain compatible. No stored intent was overwritten and no financial claim was made by these tests.

The diagnostic's internal Ability import is confined to the explicit reproducer; production code continues to use public Ability APIs. Upstream investigation and compatibility-safe remediation remain necessary. Payments does not silently substitute v2 hashes for established v1 approval/definition identities.

Payments execution invocations use flat `execution_id` and `snapshot_digest` input fields; the snapshot digest comes from the separately tested field-vector binding. `tests/approval_bindings.kujo` verifies that the pinned Ability rejects changes to these two fields, principal type/id/tenant, invocation identity, Ability identity/version, supplied definition digest and expiration. Local VM and interpreter pass. This scopes the execution binding evidence; it does not prove that arbitrary nested Ability definitions have collision-resistant v1 identities. Deployed definitions remain trusted, pinned artifacts, and broader v1 compatibility remediation remains a release gate.

## Canonical definition admission guard

Payments now verifies the exact canonical operation definition using Ability's public `ability_definition_digest_v2` before gateway dispatch, construction of an execution invocation, authorization grant or execution. The only upstream change is facade export `fe6775d27b1742196e16f6c46f73c6cec906fe73`; the legacy serializers, registry, approval and runtime source are unchanged. The root package pins that commit; optional examples retain their independently reviewed dependency versions.

At the original admission milestone, `contracts/ability-identities.json` recorded explicit `sha256-canonical-json-v2` identities for five canonical operation definitions. The later inspect v2 addition brings the inventory to six definitions and 278 independent vectors. `src/identity/canonical.kujo` compiles the same inventory so runtime admission does not trust a second mutable configuration file. An independent Python serializer checks both inventories and generates 236 whole-definition mutation cases for the real Kujo helper. Request/status and execute tests verify that substitutions fail before grant or financial claim; unchanged definitions, v1 approvals, receipts and journal keys continue through existing tests. This is a Payments admission check, not another operation-contract format, a hash-algorithm migration or a claim that arbitrary v1 definitions are collision resistant.

Do not replace a recorded definition identity under the same Ability ID/version. A future semantic contract change requires a new version, reviewed identity inventory and explicit pending-approval/idempotency compatibility tests. Providers extend the provider SPI; they do not rewrite canonical Payments Ability definitions. The inventory does not attest handler code or protect against a privileged operator replacing the application binary.

### Remaining identity paths

| Path | Current evidence/control | Remaining compatibility work |
| --- | --- | --- |
| Definition registration and resolution | Canonical v2 admission before the existing v1 registry; all scalar-field substitutions fail in VM/interpreter vectors | General Ability registry v2 identity and versioned receipt migration remain upstream work |
| Gateway request fingerprint | Persisted field-framed request digest checked against every accepted replay summary; changed amount, merchant, purpose and optional fields are covered | Existing v1 operation receipts are retained; no aliasing old keys to newly computed hashes |
| Gateway idempotency key | Legacy input is flat tenant/type/principal/key; financial scope independently uses field framing | Keep historical journal identities intact during any future algorithm migration |
| Execution approval | Flat execution/snapshot input, exact canonical definition admission, nine binding mutations/expiry tests and exact persisted issuer approval | No arbitrary nested approval-input safety claim; no conversion of old approvals into new grants |
| Execution request/replay | Same scoped execution key plus immutable snapshot, exact issued approval and permanent financial claim; claimed executions only return authoritative status | Interrupted Ability invocation recovery remains a separate unresolved journal gate |
| Receipt principal comparison | Closed flat principal shape and independently scoped financial journal | No v2 receipt emission or broad dual-read receipt migration implemented |
| Cancellation | Canonical cancel Ability now dispatches through the scoped gateway, with application-bound keys and revision checks | No provider-side reversal or interrupted invocation re-entry |
| Reconciliation declaration | Canonical identity is pinned; the worker currently uses private observation functions | Reconciliation Ability dispatch remains open |
| SDK/MCP projections | Read canonical request/status schemas; server enforces the new admission guard | Projections and client-side metadata are not a privileged execution boundary |

The release checklist's broader versioned Ability compatibility gate remains open. The guard addresses current canonical definition substitution without silently changing any existing v1 identity. A future migration must distinguish algorithms/schemas explicitly, retain historical receipts for observation, reject cross-version approval reuse, preserve permanent financial claims, and prove mixed-history behavior before release.

The current flat principal, approval and key profile is now explicitly validated and checked against an independent Python oracle in both VM and interpreter modes. See [identity compatibility](identity-compatibility.md). This adds evidence for the bounded Payments profile; it does not waive the broader migration or unfinished operation gates.
