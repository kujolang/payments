# Implementation status

Source of requirements: docs.kujolang.ai/reviews/payments, revision 2026-09-12, commits d10480e and b99d0e8.

- [ ] Phase 0: exact contract and digest conformance
- [ ] Phase 1: durable fixture core, real Kujo SQLite concurrency and crash recovery
- [ ] Phase 2: Ability hooks and authenticated gateway
- [ ] Phase 3: tested physical credential boundary
- [ ] Phase 4: pinned Link machine adapter and provider conformance
- [ ] Phase 5: separately configured provider sandbox validation
- [ ] Phase 6: optional SDK/MCP/Dispatch/Workcell composition
- [ ] Phase 7: security, faults, fences, CI and release documentation
- [ ] Phase 8: separately authorized live acceptance (not authorized by a generic build request)

No phase is complete merely because a subset of its tests passes. Link remains experimental until actual account/merchant correlation and supported-deployment tests pass.

## Verified foundation (2026-09-12)

Implemented Kujo domain validators, canonical intent/snapshot/capability bindings, strict Ability definition artifacts, lifecycle transitions and the initial SQLite persistence port. Ability is pinned to e5a74803c822de79e934d2bea82d615d8be3bbee through Kennel.

Tests pass on the local Kujo binary reporting 1.4.0, inspected alongside source checkout d054d87a9919544d4ac8eeb4b2ecc86500e71cb8 (not a reproducible-build attestation): 67 independent Python/Kujo field-binding vectors, exact-money and relational checks, 60 state/event cases, pinned Ability validators, real SQLite grant/claim rollback, 8-process contention and SIGKILL before/after a non-idempotent fake processor submission. The Python code is test supervision/oracles; production modules are Kujo.

These are component proofs, not an executable payment service. Storage functions have trusted application preconditions; no agent transport exposes them. Observation persistence, authentic Ability hooks, provider SPI and fixture executor remain next work. Tests demonstrate process crash recovery on this host; power-cut durability and deployment isolation remain untested.

Implementation details clarified: use explicit array joining and boolean adapters for Kujo membership builtins. Mutation tests replace nested dictionaries explicitly, since chained dictionary assignments did not mutate the value in the tested runtime. Do not weaken adversarial tests around this behavior.

## Ability execution and gateway milestone

Implemented injected storage ports, atomic observation/receipt persistence, conflict incident retention, a synthetic provider SPI implementation, one-shot native authorization initiation, host-issued approval matching, real Ability execution hooks and a two-operation gateway/client. A private invocation-scoped in-memory SQLite handle carries the one-use dispatch permit across Kujo callbacks; it is not a persisted financial claim and cannot be recovered after restart.

New checks exercise completed-audit failure after payment success, forged approval fields, duplicate native authorization, failures before/after fake charge, pending-to-success observation, gateway authentication rejection, caller identity injection, hidden execution denial, stable request replay and uncached status. A simulated receipt-write failure atomically rolls back its observation while retaining the financial claim. The local fixture example executes the complete synthetic path.

Remaining: real network transport/identity and issuer adapters, provider conformance breadth, Link implementation, process/egress isolation profiles, all-sink secret canaries, CI/fences, sandbox/live gates, operations and release audit. Phase checkboxes stay open until their full requirements are verified. Existing SQLite schemas are development-only additive tables; supported schema migration/restore tooling is still a release gate.

## Authenticated service and OCI milestone

Added a real HTTP request/status service, scoped bearer-token verification, private provisioning, bounded HTTPS client and strict service settings. Transport tests cover tenant separation, expiry, hidden routes, caller identity rejection, request replay, lexical floating-money rejection and absence of raw tokens in service artifacts.

The OCI profile uses a checksum-pinned official Linux 1.4.0 runtime. A separate untrusted workload has no network, credential mounts, service process namespace or engine sockets; a trusted harness on an internal network can submit an intent. The synthetic canary probe and its positive control are recorded in docs/evidence/oci-containment.json. This supports only that deployment profile, not kernel-escape resistance or live-provider isolation.

Still unfinished: operator worker/approval flow, Link machine adapter, complete provider and security conformance matrix, Workcell/Dispatch/SDK examples, CI/fences/operations and real sandbox/live acceptance. No earlier broad phase checkbox is inferred complete from these partial proofs.

Verification note: the aggregate OCI script encountered a transient host fork/resource limit after the execution component test. The remaining gateway component and current-image containment test were then run separately and passed. The receipt records the tested image digests and positive canary control. This is not reported as a single uninterrupted aggregate run.
