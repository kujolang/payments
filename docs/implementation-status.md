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

## Incident execution control milestone

Added a private database-administrator pause/resume entrypoint, revision-checked durable mode changes and atomic immutable control evidence. New financial claims and native authorization reservations fail closed while paused; reconciliation and intake remain available. The application preflight avoids beginning an Ability invocation for an already-paused store. See docs/execution-control.md for deployment authority, in-flight limitations and the explicit distinction between resume and retry.

A stop cannot revoke an earlier winning claim. A stop racing an already-started Ability invocation can retain its rejection receipt; automatic reopening is intentionally absent pending a reviewed recovery procedure. Supported backup/restore, schema migration and interrupted-invocation recovery remain unfinished release requirements. This milestone does not establish rollback-safe restoration.

Verification: full host and current-image containment jobs passed at `ff96074`, [run 34727473797](https://github.com/kujolang/payments/actions/runs/34727473797). Evidence: docs/evidence/execution-control-ci.json. The stop/Ability race is fault-injected in tests/execution.kujo; tests/network/worker_test.py verifies both normal paused-to-active execution and reconciliation of an earlier charge while paused.

## Quarantined recovery snapshot milestone

Added a bounded administrative SQLite snapshot tool that includes committed WAL pages, validates the core journal and publishes only after permanent observation-only quarantine. Shared SQL guards block claims, native authorization reservations and normal resume on recovery copies. Source journals remain unchanged; retained executing claims become reconciliation-required in the copy. Native store opening now refuses foreign or future schema markers before schema initialization.

This implements a core-journal recovery artifact, not complete disaster recovery or live restoration. Provider journals/configuration are separate; safe financial-history merge, schema migrations and interrupted Ability recovery remain open. See docs/recovery-snapshots.md for supported operations, partial-publication handling and explicit limits.

Verification: both Linux jobs passed at `1dd0596`, [run 34727839884](https://github.com/kujolang/payments/actions/runs/34727839884). The full host suite includes the stale-snapshot, WAL, quarantine and schema-refusal tests. Evidence: docs/evidence/recovery-ci.json.

## Explicit v1-to-v2 schema migration milestone

New core journals initialize transactionally as private schema version 2. Existing v2 journals validate frozen required SQL definitions and migration provenance instead of silently repairing missing guards. A separate administrator entrypoint upgrades the exact frozen complete v1 baseline, preserving financial rows and restore quarantine, atomically recording its provenance and leaving the store paused. Normal open refuses v1 until explicitly migrated; this does not change canonical payment/Ability schema versions.

Concurrent initialization/upgrades, consumed approval/claim/receipt preservation, schema drift rejection, audit failure and SIGKILL rollback are covered by native Kujo process tests. See docs/schema-migrations.md. Earlier experimental schema variants, coordinated backup/history merge and interrupted Ability recovery remain outside the implemented migration path.

Verification: both Linux jobs passed at `b2b5bfe`, [run 34728510725](https://github.com/kujolang/payments/actions/runs/34728510725). Actual logs confirm the migration, recovery and existing synthetic suites passed. Evidence: docs/evidence/migration-ci.json.

## Agents SDK projection and replay hardening milestone

The optional `examples/agents-sdk` project pins SDK source and its separate transitive Ability version. It uses existing `register_ability_tool` with trusted client callbacks to expose only purchase request/status. No SDK source changes or core SDK dependency were required. The HTTP endpoint retains compact domain output; the example does not fabricate the full receipts required by `register_ability_gateway_tool`. Host-owned tokens/callbacks still require deployment isolation.

Actual HTTP/SDK tests cover cross-run replay, all changed request fields, hidden operation/identity injection denial, and callback exception suppression. A pinned Ability v1 nested digest collision was reproduced locally; a payment-specific persisted binding now prevents changed-term replay acknowledgement. The upstream helper/runtime cause and broader impact remain unresolved; see `docs/runtime-observations.md`.

Migration validation now occurs under the write transaction, including a deterministic stale-preflight regression. WAL configuration retries only SQLite lock contention within a bounded setup deadline; no financial retry was introduced. The full local synthetic suite completed through native merchant HTTP. Linux verification for this milestone is recorded separately after CI completes. Remaining provider, deployment, operations, integration and release gates above remain open.

Verification: both Linux jobs passed at `ea7f8ca`, [run 34729823675](https://github.com/kujolang/payments/actions/runs/34729823675). Inspected logs include the new flat approval checks, SDK HTTP conformance and migration regressions. Evidence: `docs/evidence/sdk-ci.json`. The current release checklist is `docs/release-checklist.md`.

## Dispatch wait/resume composition milestone

`examples/dispatch` requests intake through the public client and persists only an execution ID in actual Dispatch workflow state. Separate-process wakeups re-read authoritative status: nonterminal states remain paused, unavailable/mismatched status cannot release the checkpoint, and succeeded/closed outcomes allow observation to finish. A closed payment is never labeled succeeded. Dispatch continuation approval is not financial authorization; no execute/approve payment API is exposed. The host owns wakeup scheduling.

The example pins Dispatch `9eb16c72316744d8a691d9ef5ec5be4f12018408`; its sole upstream change corrects the unchanged AI SDK SHA from a named `ref` to a `commit` declaration. The original manifest failed clean Kennel resolution. Corrected installation and independent source comparisons pass for all four development projects. Dispatch's own CI passed at the corrected commit (run 34730114265). Its runtime was not changed.

The conformance test uses the real Dispatch VM/native client and a synthetic HTTP status service. It exercises durable pause/restart, early/error/wrong-execution wakeups, terminal outcomes, no repeated intake and artifact suppression. It complements, rather than replaces, the actual Payments gateway tests. All-sink deployment security, MCP/Workcell composition and the other release gates remain open. Linux Payments verification is recorded after CI completes.

Verification: both Linux jobs passed at `81ae7b4`, [run 34730274166](https://github.com/kujolang/payments/actions/runs/34730274166). Actual logs include the Dispatch restart test and all four exact dependency installations. Evidence: `docs/evidence/dispatch-ci.json`.

## MCP STDIO frontend milestone

`examples/mcp` projects canonical definitions with pinned Kujo MCP and uses official MCP SDK 1.30.0 for STDIO protocol handling. Only purchase request/status are exposed. Native public-client calls retain canonical schema and lexical integer validation; no full Ability receipt is fabricated. Before JavaScript parsing can round numbers, an 8 KiB wire guard rejects fractional/exponent/unsafe numeric tool calls. The bridge has four-call admission, bounded subprocesses/output, a cached startup catalog, a child environment allowlist and process-group cleanup. It imports no Payments provider/executor code.

An actual official SDK client now exercises the actual Payments HTTP gateway in normal tests. Hidden operations, principal/approval injection, changed-term replay and invalid wire inputs are rejected; all four direct/client/SDK/MCP fixture executions remain unclaimed. A separate process test verifies launcher cleanup. Node/MCP dependencies are confined to the optional example, installed with lifecycle scripts disabled and lockfile integrity checks. No Kujo MCP source change was necessary. See examples/mcp/README.md for protocol scope, source pins and deployment limitations. Workcell composition, all-sink conformance, provider/operations and other release gates remain open.

Verification: both Linux jobs passed at `454870f`, [run 34731012642](https://github.com/kujolang/payments/actions/runs/34731012642). Actual logs include all five exact Kujo dependency installations, official SDK client conformance, wire rejection, process cleanup and footprint/latency measurements. Evidence: `docs/evidence/mcp-ci.json`.
