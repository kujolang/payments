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

Verification note: the aggregate OCI script encountered a transient host fork/resource limit after the execution component test. The remaining gateway component and current-image containment test were then run separately and passed. The receipt records the tested image digests and positive canary control. A subsequent uninterrupted aggregate rerun passed; this supersedes the interrupted-run limitation without changing the scoped deployment claim.

## Import boundary milestone

The shared principal digest now lives in domain binding code, so intake no longer imports the private execution module. Fence is pinned in a separate development-tool project; normal tests enforce the import graph and reject nine forbidden dependency edges plus three source-coverage/external-import mutations. See docs/architecture-enforcement.md. This is static enforcement, not a runtime sandbox or a completed security gauntlet. The normal service suite and the OCI aggregate suite passed after the change.

## Local operator and bounded worker milestone

Added a trusted local issuer that reviews immutable terms and commits an exact Ability approval, plus a one-step worker that prepares, waits for external/operator authorization, executes through the existing one-use claim or reconciles claimed work. Scheduling stays outside Payments. See docs/operator.md for the OS authentication assumptions and private configuration. Separate-process tests exercise approval binding/expiry/scope, native authorization deduplication, concurrent dispatch, post-charge ambiguity and terminal replay without real money. This does not complete the Link or operator deployment-containment gates.

Verification limitation for this milestone: the normal host suite and expanded Fence mutations passed. The new OCI run failed before any build/component test because Docker returned HTTP 500 while booting BuildKit. The prior OCI receipt belongs to the earlier tested image and does not establish Linux/containment coverage for the new operator/worker code. The runner now explicitly loads Buildx output to avoid testing stale images with a container builder; this updated path still needs a successful engine-backed run.

## Link native authorization components

Implemented a bounded fixed-origin private Link transport and crash-conservative SpendRequest issuance/observation journal, grounded in pinned SDK 0.4.1 / CLI 0.19.1 source. Tests cover exact native binding, suppression of extra secret fields, four-process issuance contention and lost-response no-retry. This is not yet a complete selectable Link provider; MPP execution, credential retrieval, merchant reconciliation and live account conformance remain unfinished. See docs/link-provider.md and deployment/link-source.lock.json.


## MPP codec and one-shot submission components

Added a source-pinned Stripe charge codec, immutable private MPP preparations/dispatches, execution-only SPT retrieval, exact challenge revalidation and sanitized merchant observation. Provider deadlines now end no later than the approval or snapshot; expired intents cannot initiate native authorization. Tests use independent vectors and synthetic merchant/API callbacks. Complete Link registration, native merchant transport and authoritative account/merchant observation are still unfinished. A wrapped-callback VM/interpreter disagreement is preserved under tests/runtime and documented; supported privileged entrypoints continue to require interpreter mode.

## Link registration and native merchant HTTP milestone

Implemented the internal five-method Link provider factory, immutable installation/preparation binding and a bounded native registered-merchant HTTP port. The factory verifies route identity, origin, body digest and tenant context; the MPP codec now requires an explicitly installed externalId expectation (58 vectors). Provider fixtures exercise the actual worker and approval path against a separate synthetic merchant ledger. Native HTTP fixtures cover header ambiguity, credential placement, redirects, exact UTF-8 body digests and output/deadline limits.

This supersedes earlier statements that the factory and native merchant HTTP were unimplemented. Production configuration, stable payer-account verification, private approval URL delivery, OAuth lifecycle and authoritative settlement observation remain open. Current OCI coverage, all-sink security conformance, integrations, CI and migration/restore operations also remain release gates. No real money moved.

Verification: the uninterrupted full host suite passed after an earlier attempt hit host process exhaustion. Evidence: docs/evidence/2026-09-12-link-registration.log. The earlier OCI receipt does not cover these new modules.

## Reproducible Linux CI milestone

The workflow at `.github/workflows/verify.yml` now runs the full synthetic host suite and a separate current-image OCI job for pushes, pull requests and manual runs. It has read-only repository permissions, no persisted checkout credentials, no provider secrets and bounded job/process timeouts. Runtime archive/binary checksums and the Kennel source commit are pinned. Kennel installs committed Ability/Fence locks; an independent checkout comparison verifies installed source, and modified dependency contracts fail the build.

Both jobs passed at commit `8d44c4d86b021fb7214c3026740570cf2e825801`: [run 34727010312](https://github.com/kujolang/payments/actions/runs/34727010312). Evidence and selected verification output are in `docs/evidence/linux-ci.json` and the adjacent CI logs. The OCI runner now includes Link authorization, MPP, submission and complete provider fixtures, with interpreter mode on privileged component checks. This closes the earlier current-image validation gap despite the local Docker Desktop failure. The old local OCI receipt remains historical.

CI automation is implemented and verified. This does not close the broader Phase 7 gates: all-sink leak conformance, supported operations/migration/restore, incident stop control and final release audit remain. Native account/settlement confirmation, OAuth/operator delivery, optional integrations and real sandbox/live gates also remain unfinished.
