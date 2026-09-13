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

## Workcell containment composition milestone

`examples/workcell` uses Workcell's stable v1 lifecycle to run only a public agent/probe checkout with no network, credential mounts or payment-client token. It exports one bounded intent artifact. The host verifies the receipt/manifest and a separate trusted harness submits the untrusted intent through the existing gateway. The resulting payment remains awaiting authorization. No Workcell source change or core dependency was required.

The example pins Workcell `e2915a3fbf5befe28cab09509f8a79bc93976975` and its tested Kujo 1.2.1 runtime source `692512a9070fdba713f160d795bbddb8077db7b5`. The workload independently uses the Payments Kujo 1.4.0 image. Stable v1 does not accept caller context, so trusted evidence correlates Workcell run and payment execution IDs externally. An operator cancellation file precedes bounded process termination; unresponsive cleanup is reported as unconfirmed. Four unit fixtures cover escalation/error suppression, without claiming real daemon-failure recovery.

The real Docker fixture retains a separate service with a positive credential canary, runs hostile access probes, verifies exported evidence, submits through trusted intake and searches Workcell artifacts/logs/receipts and harness output for provider and request credentials. CI retains synthetic evidence for 14 days. This proves the named fixture profile only: no live provider, general model-network profile, microVM, daemon/kernel escape, raw-card handling or all-sink production claim. Full release gates remain in `docs/release-checklist.md`.

Verification: both Linux jobs passed at `ac26e3b`, [run 34731947795](https://github.com/kujolang/payments/actions/runs/34731947795). Downloaded artifact 10309607468 matched its GitHub archive digest; all six manifest entries matched byte counts and hashes. The receipt reports complete cleanup, one 206-byte artifact and 3916 ms elapsed in this fixture, not a latency guarantee. Evidence: `docs/evidence/workcell-ci.json`. Raw synthetic receipt/manifest/logs are retained outside Git under `deployment/.workcell/evidence/34731947795/` and in the expiring CI artifact.

## Canonical Ability definition admission milestone

Payments now checks canonical operation definitions with Ability's existing versioned v2 digest before gateway dispatch, execution invocation construction, approval grant and financial execution. The reviewed identity inventory is compiled into a small isolated module; Python independently calculates canonical bytes and generates 236 mutation vectors. The module cannot import storage or provider code. Request/status substitutions and execution-definition substitutions are rejected before a financial claim or approval consumption.

The pinned upstream change `fe6775d` only exposes the existing helper through Ability's public facade. Its full local release verification and upstream CI run 34732688161 passed; v1 runtime and serializer source are unchanged. Root Payments dependencies were installed through Kennel and compared with exact upstream source. Optional SDK/MCP/Dispatch dependency pins remain independent.

A regression preserves the exact historical v1 execution-definition digest and demonstrates that changing `input_schema.additionalProperties` still collides under v1 but is rejected by v2 admission. Existing approvals, receipts and journal identities are not rewritten. This narrows the canonical Payments boundary; it does not migrate general Ability identities or close the broader compatibility gate. The eight-path identity audit and migration constraints are in `docs/runtime-observations.md`.

Verification: both Linux jobs passed at `04741e9`, [run 34732966439](https://github.com/kujolang/payments/actions/runs/34732966439). Actual logs include both 236-vector runs, 13 forbidden architecture edges and real Workcell containment. The downloaded Workcell artifact matched its archive digest and all six manifest entries; cleanup was complete. Evidence: `docs/evidence/ability-identity-ci.json`; raw synthetic evidence remains outside Git at `.local/evidence/34732966439/`.

## Private Link credential rotation milestone

`credentials.kujo` implements a versioned private credential vault, bound installation, metadata-only inspection, one-shot generation refresh, local disable and an expiry-checked Link API callback. `oauth.kujo` provides a bounded fixed-origin native refresh transport with validated form encoding. Neither adds agent tools or changes the provider SPI. The host owns vault permissions, isolation, at-rest protection and initial verified grant installation.

A durable generation reservation removes usable old tokens before refresh. Replacement tokens commit atomically; old-generation calls never repeat the native request. Crashes, malformed responses, scope changes, write failure and local disable preserve nonusable or disabled state. Expiry uses request start, rejects delayed expired responses and fails closed on backward time. Old bytes can remain in private SQLite pages; there is no secure-erasure or provider-revocation claim.

Native fixtures cover four-process races, failures, crashes before/after commit, binding denial, conservative expiry, foreign-journal/schema rejection and output leakage. The OCI fixture creates a real synthetic credential vault in the privileged service mount and adds four vault/journal path probes to the isolated agent. Device enrollment, private approval delivery, provider revocation, stable account/authorized grant evidence, coordinated vault recovery and live/all-sink acceptance remain open. See `docs/link-provider.md` for exact contracts and deployment limits.

Documentation-only pushes under `docs/` no longer rebuild the pinned runtimes; runtime suites do not read these files. Code/configuration pushes, pull requests and manual verification retain their existing checks. This avoids repeating a runtime build solely to record already-verified evidence.

Verification: both Linux jobs passed at `1ef1f5f` (implementation `9177dec`), [run 34734241325](https://github.com/kujolang/payments/actions/runs/34734241325). Actual logs include credential failure/recovery fixtures and OCI/Workcell containment. Downloaded artifact 10310531846 matched its archive digest and all six manifest entries; both isolated probes reported 14 denied file paths, with a positive private credential-vault control and complete cleanup. Evidence: `docs/evidence/credentials-ci.json`; raw synthetic artifacts/logs remain outside Git in `.local/evidence/34734241325/`.


## Private approval delivery component

Added an immutable executor-only URL outbox and trusted delivery callback, with exact native SpendRequest binding, installation-owned HTTPS origin allowlist, principal/snapshot selection and expiry checks. Safe results contain only an opaque reference; neither provider SPI nor agent tools changed. The credential vault and outbox share an exact-schema initializer while retaining separate database identities. Whitespace-only OAuth scope is now rejected before installation.

The local native tests pass 24 URL/binding/callback cases, four-process staging, credential rotation regressions and empty-scope denial. The initial sink failure was a fixture error: overwriting a pre-created private file requires explicit `write_file(..., true)`. No new runtime defect was established. The complete local host suite passed, including architecture enforcement and all existing Link/Ability/integration regressions. Both pinned Linux jobs passed at `6b34647`, [run 34735770887](https://github.com/kujolang/payments/actions/runs/34735770887). Downloaded artifact 10311380332 matched its archive digest and all six manifest entries. The actual private outbox/vault positive controls, both 18-file agent probes and complete cleanup were verified. Evidence: `docs/evidence/approval-delivery-ci.json`; raw synthetic logs/archive remain outside Git under `.local/evidence/34735770887/`. Production operator authentication, current-state enforcement, URL retention/cleanup, enrollment/revocation, stable account identity and settlement evidence remain open; see the release checklist.


## Approval URL retention and explicit private-store upgrade

The outbox now uses private schema v2: expiry-indexed cleanup removes the live URL column after expiration while retaining a permanent principal/snapshot/execution identity and retirement time. Re-staging, URL restoration, deletion and changed bindings remain denied. A private administrator command performs bounded cleanup or explicitly upgrades the exact frozen v1 profile after declared quiescence. The credential vault/core/Ability versions are unchanged.

Tests cover four-process migration/cleanup, preservation, disk-full rollback, SIGKILL during migration and retirement, old-reader refusal, direct-delivery/re-staging denial and administrator validation. This is logical retention, not physical erasure, provider revocation, browser cleanup or coordinated backup recovery. The complete local host suite and both pinned Linux jobs passed at `ce87be7`, [run 34736615489](https://github.com/kujolang/payments/actions/runs/34736615489). Downloaded artifact 10310914166 matched its archive digest and all six manifest entries; private outbox/vault positive controls, both 18-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/approval-retention-ci.json`; raw synthetic artifacts/logs: `.local/evidence/34736615489/`; operational procedure and scope are in `docs/link-approval-maintenance.md`.


## Reviewed private operator delivery composition

Added `reviewed_operator_sink` in the privileged executor. It reuses the existing payer authority and canonical Ability review, rechecks journal state/pause at handoff and afterward, binds payload execution/snapshot/expiry and caps the renderer deadline. A delivery-only review permits unclaimed awaiting/ready states so provider and Kujo consent can occur in either order; the financial grant path remains awaiting-only. No grant, financial claim, provider SPI or agent surface is added.

Nineteen native core/Link integration cases pass, including scope/binding/state denial, fetch/render cancellation and pause, private renderer failures and unchanged financial grants/claims. The actual private positive-control seed also passes locally; it now exercises the reviewed renderer and adds six hostile agent file probes (24 total). The full local host suite passed, followed by the expanded 19-case delivery and operator regressions after shared authority-schema admission was added. Both pinned Linux jobs passed at `15253d1`, [run 34737608492](https://github.com/kujolang/payments/actions/runs/34737608492). Downloaded artifact 10311144852 matched its archive digest and all six manifest entries; reviewed private renderer/outbox/vault positive controls, both 24-file probes and complete cleanup were verified. Evidence: `docs/evidence/operator-delivery-ci.json`; raw synthetic logs/archive: `.local/evidence/34737608492/`. Renderer authentication/isolation, hard process bounds, browser/redirect controls, sink retention and remote delivery races remain explicitly deployment-owned; see `docs/operator-delivery.md`.


## Conditional cancellation and explicit revision inspection

The gateway now dispatches the existing canonical cancel Ability and a separately pinned inspect version 2.0.0 with a revision field. Existing inspect v1 output and all five previous definition identities remain unchanged. New controls require explicit credential operation scopes and are absent from default agent/SDK/MCP projections. SQLite cancellation is scoped, revision-checked, pre-claim only and denied on quarantined copies; incident pause permits cancellation in the live store.

New cancellation journal identities add a field-framed application binding without rewriting legacy Ability receipts. The complete local host suite passed with 278 independent definition mutation vectors, unchanged 3065-byte model tool schemas and a 182-byte sample status, eight real cancellation/claim races, stale/changed-input replay denial and recovery-copy denial. Cancellation state and Ability receipt completion remain separate; interrupted invocation repair is still an open release gate. See `docs/cancellation.md` for the supported contract and limitations. Both pinned Linux jobs passed at `599f850`, [run 34738832485](https://github.com/kujolang/payments/actions/runs/34738832485). Downloaded artifact 10311947605 matched its archive digest and all six manifest entries; actual reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/cancellation-ci.json`; raw synthetic logs/archive: `.local/evidence/34738832485/`.


## Interrupted gateway invocation observations

Exact request/cancellation retries can now return `operation_incomplete` with a verified current payment summary after Ability reports an invocation still in progress. A purchase lookup joins the authenticated scope, request key and field-framed terms to the authoritative execution; strict integer money/expiration checks remain in force. Cancellation reuses its existing exact journal binding. No handler, provider call, claim reset or receipt completion occurs on this path. Policy/approval/audit rejection remains closed, and older custom stores keep their prior behavior without the optional lookup method.

The complete local host suite passed, including five actual SIGKILL boundaries, four concurrent observation retries, unchanged journals, authenticated HTTP restart, exact-input denial and no recreated action. Expanded missing-approval, preflight/completed-audit failure and optional-field mutation checks then passed independently. Completed successful replays retain their original result. Pre-intake crashes without a domain record, abandoned invocation repair, pre-claim execution recovery and coordinated backup/history recovery remain open. See `docs/interrupted-invocations.md`. Both pinned Linux jobs passed at `2c407a7`, [run 34739364947](https://github.com/kujolang/payments/actions/runs/34739364947). Artifact 10312187815 matched its archive digest and all six manifest entries; reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/interrupted-gateway-ci.json`; raw synthetic logs/archive: `.local/evidence/34739364947/`.


## Recovery observations across optional harnesses

The optional SDK and MCP adapters previously discarded the gateway's safe error summary, and the Dispatch entrypoint stopped before tracking the existing purchase. They now preserve a validated incomplete observation without converting it into a successful request. SDK retains the compact summary in its normalized handler error; MCP returns structured content with `isError: true`; the SDK example and Dispatch observer read fresh status before continuing. Status observations must match the requested execution ID. No upstream SDK/MCP/Dispatch source change, new tool or hard dependency was needed.

The native HTTP client now retains error observations only from documented HTTP 409 responses with `ok: false` and a valid closed summary/envelope. Authentication failures, server errors, extra fields and malformed summaries cannot supply recovery data. The complete local host suite passed, including 21 actual frontend-process runs against a synthetic HTTP fixture, stale-terminal-to-fresh-pending behavior, wrong-ID denial, no automatic intake retry and private artifact/output suppression. Existing real gateway crash fixtures and normal SDK/MCP/Dispatch regressions passed. The catalog remains 3065 bytes and the sample successful status remains 182 bytes; these are byte counts, not tokenizer counts. Both pinned Linux jobs passed at `2e1b960`, [run 34739939659](https://github.com/kujolang/payments/actions/runs/34739939659). Artifact 10311519342 matched its archive digest and all six manifest entries; reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/recovery-projections-ci.json`; raw logs/archive: `.local/evidence/34739939659/`.


## Closed principal and flat identity compatibility profile

Independent cross-language vectors exposed a real configuration mismatch: Payments' domain/service shape permits 128-character principal type identifiers, while the installed Ability invocation contract supports 64. Service startup now validates the closed Payments profile against Ability's existing public validator before opening the database. The embedded gateway, execution invocation construction and private operator authority checks reject incompatible/nested profiles without truncation or hash substitution. Canonical intent/Ability definitions, existing receipts, dependency pins and journal schemas remain unchanged.

Thirty-six independent Python vectors compare actual approval/scope/request/cancellation-key identities with both VM and interpreter execution, including escaped/Unicode keys and boundary-length identifiers. The fixture performs actual request/cancel/replay operations and checks retained v1 receipts. Negative profile and incompatible-startup tests pass. The full local host suite passed, including 278 canonical definition mutations and the expanded Fence test: executor code may read pure identity validators, but the reverse edge is rejected alongside the existing forbidden dependencies (14 edges total).

See `docs/identity-compatibility.md` for the exact profile, updated identity path matrix and limits. General nested v1 Ability migration, reconciliation Ability dispatch and broader recovery remain open; this milestone does not claim those gates are complete. Both pinned Linux jobs passed at `5709744`, [run 34740892902](https://github.com/kujolang/payments/actions/runs/34740892902). Artifact 10312149959 matched its archive digest and all six manifest entries; reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/identity-profile-ci.json`; raw logs/archive: `.local/evidence/34740892902/`.


## Canonical private reconciliation dispatch

The bounded worker now dispatches `kujo.payments.execution.reconcile@1.0.0` through real Ability hooks. The host supplies the pinned definition and an explicit key per logical observation; missing configuration fails closed. Policy can allow evidence observation independently of financial approval. Exact retries retain their operation receipt or in-progress state; deliberately fresh keys permit only a new observation. Additional field-framed storage bindings cover scope, execution and snapshot without rewriting legacy receipts or changing canonical contracts.

The private API returns authoritative current status separately from its Ability result, including after receipt/audit failure. The worker keeps its compact result and the public gateway/model surfaces are unchanged. See `docs/reconciliation.md`. Targeted fixtures cover policy/identity/provider rejection, independent processor counts, keyed replay, fresh observations and three process-kill boundaries. All local host-suite components passed across the initial run and corrected continuation. The initial new two-payment fixture reused a purchase reference and then an issuer nonce; existing intake/approval uniqueness correctly rejected it. The fixture now gives each intentional payment distinct business and approval identities. The corrected reconciliation suite and all remaining Link/merchant regressions passed; prior host checks, including Fence and optional harnesses, had passed before that fixture failure. Synthetic logs are `.local/reconciliation-host.log` and `.local/reconciliation-remaining.log`. Both pinned Linux jobs subsequently passed at `7129434`, [run 34741800233](https://github.com/kujolang/payments/actions/runs/34741800233), including the full uninterrupted host suite. Artifact 10313366171 matched its archive digest and all six manifest entries; reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/reconciliation-ci.json`; raw logs/archive: `.local/evidence/34741800233/`. General v1 migration, abandoned invocation repair, coordinated backups and live provider/deployment acceptance remain open.


## Intake recovery through the existing business-reference contract

No new runtime API or journal repair is needed to complete a stalled intake: a trusted host can deliberately submit the exact original input and business purchase reference with a fresh operation key. SQLite's existing atomic `(scope,purchase_ref)` uniqueness and payment-specific term binding resolve concurrent and late handlers to one execution. Default agent/harness behavior remains stable-key request/status; it does not automatically generate replacement keys. See `docs/intake-recovery.md` for the bounded host procedure and deployment requirements.

The expanded interrupted-gateway suite passed its existing five SIGKILL/HTTP/policy/audit cases plus six recovery scenarios: before intake, after intake and before receipt completion, each with killed and live originals and four fresh-key contenders. Terms and expiry remain unchanged, changed inputs conflict, and no approval/financial claim is created. Deliberately delayed original handlers correctly return failed timeout receipts even though the domain purchase exists; a kill before intake leaves the original key unmapped, so its exact retry cannot invent the ID known through a fresh key. Initial new fixture assertions were corrected to respect these existing timeout/mapping semantics; no production behavior was weakened. Synthetic output: `.local/intake-recovery.log`. Both pinned Linux jobs passed at `c030e50`, [run 34742185301](https://github.com/kujolang/payments/actions/runs/34742185301). Artifact 10313476491 matched its archive digest and all six manifest entries; reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/intake-recovery-ci.json`; raw logs/archive: `.local/evidence/34742185301/`.

This closes the supported host-composition gap for interrupted intake, not abandoned-journal repair, pre-claim financial execution re-entry, coordinated provider/vault backup or stale-history merge. Those release gates remain open.


## Private Link revocation component

Added `revoke_link_credentials` alongside the existing private rotation/disable methods, plus a fixed-origin native revocation form/transport. The operation disables the reviewed local generation before one provider request. Strict bounded acknowledgment is reported separately from local disablement; failure, lost response or crash leaves provider status unknown. The vault persists only local disabled state, so neither restart nor a deleted token fabricates a remote acknowledgment. An in-flight refresh cannot restore a disabled generation. No public operation, provider SPI, dependency or private-store schema change was required.

The reviewed Link source remains `4aa62ba`; the logout source hash joins the existing auth provenance. No CLI client ID, verbose native logging or raw OAuth errors are copied. See `docs/link-revocation.md` for endpoint acknowledgment limits, operator responsibilities and in-flight credentials. Enrollment, durable remote-status recovery, supported registration/account identity, authenticated installation and live provider semantics remain open.

The full uninterrupted local host suite passed, including 12 synthetic revocation cases, four-process contention, SIGKILL, refresh/disable interaction, form and pre-network denial, secret-output checks and the existing credential, approval, payment, recovery and integration regressions. Local synthetic log: `.local/revocation-host.log`. An initial parser error in a compound expression inside a dictionary was corrected by calculating the boolean first; no new runtime finding was established. Both pinned Linux jobs passed at `59ed9c8`, [run 34742759652](https://github.com/kujolang/payments/actions/runs/34742759652). Artifact 10312587505 matched its archive digest and all six manifest entries; reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/revocation-ci.json`; raw logs/archive: `.local/evidence/34742759652/`.


## Private Link device enrollment journal

Added a separate exact-schema private enrollment journal and bounded native device initiation/token forms. Session initiation, token polling and private acceptance reserve before effects; only explicit pending/slow-down responses schedule another host-driven poll. The journal binds tenant/payer/account/client/scope, label, allowed operator origins and a unique target credential ID. Status exposes metadata only. Private delivery includes expected connection terms and user confirmation, while device codes and tokens stay inside the executor. The required acceptance callback must verify provider account/grant binding before credential installation; the fixture supplies only synthetic attestation.

An enrollment API guard permits the underlying matching credential API only after the immutable enrollment is recorded as accepted. It blocks the crash window after a vault installation but before the enrollment receipt commits. This is not cross-store atomicity or proof of provider identity; unguarded privileged configurations, incident recovery and backup freshness remain deployment/release responsibilities. No public payment/Ability/SPI contract or hard dependency changed. See `docs/link-enrollment.md`.

The full local host suite passed, including the initial enrollment lifecycle, 13 fault cases, four-way races and four process-kill boundaries. After the final publication guard, persistence-failure and clock tests were added, the expanded enrollment suite passed 22 fault cases plus the lifecycle/concurrency/crash checks. Tests retain conservative token expiry, prevent native or installer re-entry, clear live secret columns on phase completion/abandonment, suppress unknown native fields and keep all sentinel values out of process output. Logs: `.local/enrollment-host.log` and `.local/enrollment-expanded.log`. An initial fixture assertion compared integer `has_key` output with boolean false; it was corrected to zero without changing runtime semantics.

Both pinned Linux jobs passed at `85300fe`, [run 34744086846](https://github.com/kujolang/payments/actions/runs/34744086846). Artifact 10313417726 matched its archive digest and all six manifest entries; reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. This run predates dedicated enrollment storage/operator probes. Source-scoped evidence: `docs/evidence/enrollment-ci.json`; raw logs/archive: `.local/evidence/34744086846/`. Supported client registration, actual provider-account verification, authenticated operator/installer deployment, uncertain installation recovery, dedicated enrollment containment/all-sink coverage and provider sandbox/live acceptance remain open. Existing payment approvals remain separate and mandatory; no real account or funds were used.


## Dedicated enrollment containment fixtures

The shared OCI/Workcell hostile probe now attempts 30 file reads, including the enrollment database and journal/WAL/SHM paths, the private enrollment operator output and the enrollment implementation module. The privileged seed creates actual pending device-code and received-token rows through the enrollment API and delivers an actual filtered operator payload. It verifies the live private values before hostile probes run; the containment receipt records three distinct enrollment positive controls. Artifact/process scans include the random credential canary and separately derived user-code canary, including service stderr.

The exact privileged seed also runs in normal host CI. Its local synthetic test passed using the available Kujo 1.3.1 release interpreter; the previously recorded local debug executable is no longer present. This local result is not Linux containment evidence. Pinned Kujo 1.4.0 host and OCI/Workcell verification of these added probes is pending. No deployment, provider identity, authenticated operator renderer or live-account guarantee is added.
