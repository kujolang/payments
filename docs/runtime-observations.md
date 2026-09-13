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
