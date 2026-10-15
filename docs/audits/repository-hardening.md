# Payments repository hardening — 2026-10-13

The **2026-10-15 completion audit** below incorporates the second sweep, a fresh verification run and the open reconciliation-seed finding. Earlier sections preserve their original revision-scoped evidence.

## Scope and provenance

- Repository: `kujolang/payments`; branch: `main`.
- Starting SHA: `ea2f2242489ecd77c7a040a1cb67f49b5383763e` (clean).
- Ending implementation SHA: `6bc4526670d74a954d8346da362a7876e0713d5b`.
- This report and its measurement artifacts are a subsequent documentation-only commit. They do not change the tested implementation.
- Direct source review and local synthetic tests; the blocked security-plugin scan was not used or represented as completed. No credentials were read and no financial API was called.

Payments is a buyer-side request, authorization, single-use execution and reconciliation library. Ability supplies semantic operation contracts; SQLite holds authoritative durable claims. The provider SPI has five required methods. Agents SDK, MCP, Dispatch and Workcell are optional compositions. Fence is a development dependency. Link remains an unaccepted native integration, not a production payment capability.

## Baseline and verification

The baseline ran the existing `scripts/test.sh` with the previously verified development runtime (`84ef9eb2313de963690f25a31f56083b61013ccdf6a34bad47d630d69f88694a`, Intel macOS). Its embedded version is 1.4.0, but it includes the header-values fix absent from the stable release. Node was v26.7.0 and Python 3.10 locally; Linux CI uses its committed runtime and Node 24.20.0 pins.

The baseline passed through architecture checks, then failed in native package creation at the existing 180-second deadline. Total elapsed time before failure was 990.90 seconds. All remaining original test commands passed in a separate 946.41-second run, without changing their assertions or deadlines. The media exclusion alone did **not** eliminate the local packaging timeout: the focused rerun also reached 180 seconds. The isolated rerun after the baseline workload finished passed in 83.27 seconds, with 102 files and 150,497 compressed bytes, at the unchanged deadline. This report does not attribute a latency improvement to media exclusion: concurrent workload conditions differed. Timing alone does not establish the original timeout cause.

The local post-change full-suite attempt separately reached the unchanged 90-second deadline in the flat identity VM fixture, whose source and dependencies were unchanged and whose baseline run passed. The isolated local identity rerun then passed in 53.06 seconds with unchanged deadlines after the concurrent baseline workload finished. Linux passed the entire suite. These local timing failures are retained, not hidden or treated as new financial regressions.

Verification results are recorded in `repository-hardening-evidence.json`. Detailed local logs remain under `.local/audit-20261013/`; those logs are ignored, not shipped as package input. The full Linux host suite passed, including real package installation: 102 files and 150,497 compressed bytes at the ending implementation SHA. Both the host and OCI/Workcell containment jobs passed. The source-scoped Linux verification run is [38346668948](https://github.com/kujolang/payments/actions/runs/38346668948).

## Changes

| Problem and root cause | Implementation and files | Regression proof | Compatibility and impact |
| --- | --- | --- | --- |
| Python `-O`/`-OO` removed runtime hashes, source pins, permissions and verified-artifact checks expressed as `assert`. A synthetic bad archive was installed with exit 0 under `-O`. | Explicit `ValueError` guards in `scripts/deployment/{fetch_runtime,setup_workcell}.py`, `scripts/ci/bootstrap.py`, `examples/workcell/run.py`. | `tests/deployment_integrity_test.py`: valid/cached installs; corrupt archive/binary hashes; duplicate executable; symlink; invalid image; checks under normal, `-O`, `-OO`. Expanded Workcell tests exercise source/version, failed receipt, escaped path, unverified evidence and unsafe artifact rejection. | Valid setup and result formats unchanged. Invalid inputs still exit nonzero, now also with optimized Python; private Python exception type becomes `ValueError`. |
| Runtime cache writes replaced the destination contents before completion; cache hashing read the whole file. | Stage a verified binary in the same directory, flush/fsync, then atomically replace; remove failed staging files. Hash cached data in 1 MiB chunks with a 256 MiB maximum. Restore executable mode after verified cache hits. | Fault-injected fsync/replace failures retain the previous file and leave no stage; test forbids whole-file cache reads. | Same paths, hashes and successful messages. This is an operator-owned build directory, not protection against same-user ancestor replacement or a power-loss durability claim. |
| Optional MCP lock included four packages flagged by the current npm advisory database. | Pin SDK 1.32.1; update fast-uri 3.1.8, ip-address 10.7.4 and proxy-addr 2.0.8 in `examples/mcp`. | Locked install and npm audit; HTTP/MCP contract, process cleanup, exact-money and output-budget tests. | No new direct dependency; 94 locked packages before and after. Advisory package count 4 → 0 at audit time. This is dependency hygiene, not proof of four exploitable Payments vulnerabilities. |
| Installable package included promotional assets unrelated to execution. | Exclude `docs/videos` in `kennel.toml`; retain every asset in Git. README links now point to hosted media/transcript. | Actual Kennel package test includes a tracked video-directory sentinel, rejects all video entries, preserves import/private-path tests, and sets a 1 MiB uncompressed payload budget. | Removes 45 promotional source files totaling 5,285,320 bytes from package eligibility. No code export removed. Package users follow hosted media links. Budget changes require explicit contents review. |
| Verification assertions themselves could disappear if the test runner inherited `PYTHONOPTIMIZE`. | Reject optimized Python before any suite execution; add integrity regressions to normal CI. | An optimized-runner regression verifies the explicit refusal before Kujo launch. | Intentional test-runner behavior change; production bootstrap still supports optimized Python safely. |
| Sandbox documentation described already-implemented components as unfinished; Linux setup omitted MCP npm install. | Correct `docs/stripe-sandbox-evidence.md`, `docs/deployment.md`, package and MCP guides. | Compared commands to launchers and suite dependencies. | No readiness gate removed; real Link enrollment and provider acceptance remain open. |

The SDK advisory explicitly excludes MCP servers and STDIO clients; this example uses a STDIO server and does not use the affected OAuth client. See the [upstream advisory](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-6qxp-vccf-f47h). The proxy-addr advisory concerns trusted proxy IP interpretation, which this STDIO entrypoint does not configure. Updating these dependencies does not substitute for payment-domain isolation tests.

## Measured efficiency

| Measurement | Before | After | Interpretation |
| --- | --- | --- | --- |
| Peak Python traced allocation, verified 8 MiB synthetic runtime cache | 8,703,996 bytes | 2,417,831 bytes | Same payload and checksum, separate Python processes. Python allocation only, not total RSS. |
| Cache probe elapsed time, one local sample | 317.05 ms | 692.70 ms | No latency improvement claimed; host load and startup dominate this small probe. |
| Locked npm package count | 94 | 94 | No dependency expansion. |
| npm advisory package count | 4 | 0 | Time-specific registry result, not a general security certification. |
| Model-visible two-tool descriptors | 3,065 UTF-8 bytes | 3,065 UTF-8 bytes | Bytes, not tokenizer counts. Existing 4,096-byte regression budget retained. |
| MCP pending summary / response envelope | 182 / 438 UTF-8 bytes | 182 / 438 UTF-8 bytes | No extra tool or model-visible journal added. |

No new cache, provider abstraction, policy engine or workflow engine was introduced. The source review found no evidence justifying removal of operation contracts, duplicate financial validation, compatibility identity checks or reconciliation journals. Those checks protect different boundaries and are retained. The five-method SPI, two-tool projection and existing catalog reuse already keep model exposure and idle subprocess work bounded. No speculative token savings or production payment-latency claims are made.

Reproduce the cache measurement with `python3 docs/audits/runtime-cache-measure.py scripts/deployment/fetch_runtime.py`. To reproduce the baseline, save `git show ea2f224:scripts/deployment/fetch_runtime.py` to a temporary file and pass that file instead. The probe creates only a disposable synthetic cache and never downloads or executes a runtime.

## Reviewed boundaries and retained invariants

| Area | Source and evidence inspected | Result and limit |
| --- | --- | --- |
| Public APIs, exact money, versioned contracts | Package exports, Ability JSON, domain validation/binding, identity vectors, client and gateway | No contract or schema changes. Integer-only money, narrow principal profile and cross-language digests retained. |
| Agent and transport boundary | Gateway operations/HTTP; MCP framing and admission; SDK/Dispatch staging; client transport | Authenticated host principal, two projected tools, bounded input/output/processes, sanitized results; requesting runtime still requires actual deployment isolation. |
| Financial concurrency and ambiguity | Application execution/worker, SQLite port/schema/CAS/claim triggers, SIGKILL/race tests | Permanent claims, one-use permits, independent confirmation and observation-only recovery retained. No retry authorizes a new charge after an ambiguous dispatch. |
| Provider credentials and network | Link API/OAuth/enrollment/vault/approval/submission, MPP parser, merchant and Stripe sandbox ports | Fixed or installed routes, bounded requests, no redirects/automatic financial retries, scoped generations and sanitized observations. Synthetic authority callbacks do not prove a real funding account. |
| Filesystem and maintenance | Shell launchers, recovery snapshot/set/verification, runtime installer, Workcell composition | Private journals and quarantined restores retained; installer checks fixed. Same-user administrators and compromised trusted executors remain outside the containment claim. |
| Build and dependencies | Manifests/locks, source bootstrap, package fixture, Dockerfile, workflow pins | Exact source pins retained; optional npm patches reviewed. No sibling repository modified. |
| Resource and output behavior | MCP process-group cleanup, admission cap, Link measurement fixture, compact summaries, cache fetch | Existing byte/process budgets retained; cache allocation bounded. Detailed test logs kept outside routine response context. |
| Architecture and maintainability | Fence zones and mutation checks, gateway/application/storage/provider dependency directions | All 46 source files classified. Large storage/execution modules encode cohesive transactional behavior; no evidence justified a risky cosmetic split. |

This audit does not claim exhaustive formal verification, PCI compliance, live Link readiness, or a new physical isolation guarantee. Local Docker did not answer within the bounded eight-second availability check; local OCI execution was unavailable. The current Linux CI containment job passed at the ending implementation SHA, including actual Workcell and OCI hostile probes. This is source-scoped fixture evidence, not live-deployment certification.

## Compatibility statement

Public Kujo APIs, Ability identities, provider SPI, financial JSON schemas, SQLite formats, configuration formats and environment variable names are unchanged. Successful bootstrap and Workcell output shapes are unchanged. The test runner now rejects optimized Python explicitly. The runtime cache publication mechanism and invalid-setup exception type changed. Package contents intentionally omit promotional media; links preserve access. Optional MCP dependencies changed within their supported 1.x SDK line. No consumer migration or sibling repository edit is required.

## Commands and remaining work

Exact commands, exit results and measurements are in the companion evidence file. Existing tests were not disabled, weakened or given longer timeouts. New tests use synthetic data only. There is no standalone compile/lint/typecheck target for the Kujo library; executed contracts, real package installation, Python/JSON/shell syntax checks and Fence are the applicable checks.

- **P0/P1:** No newly demonstrated unresolved financial-execution defect from this pass. This is not a claim that none exist.
- **Needs more evidence:** Local native package generation initially timed out at the unchanged 180-second bound before and after media exclusion. The same test passed on Linux and then locally in isolation without changing its deadline. If the problem recurs, isolate local contention and Kennel builder/runtime cost before changing deadlines or dependency pins. The pinned Kennel builder constructs archives in Kujo and repeatedly concatenates growing buffers; that is a code-supported performance hypothesis, not a measured root cause. If a builder change is necessary, it belongs in `kujolang/kennel` and must preserve deterministic archive bytes, safety limits and installation compatibility. No sibling change was made.
- **P2 / existing release gate:** Supported Link client provisioning, verified funding-authority linkage, actual sandbox purchase/confirmation and selected-deployment containment remain unaccepted. Account ownership and an official CLI demo do not close these gates.
- **P3:** Consider a bounded provider-backed acceptance job only once provisioning exists; normal CI must continue to move no money.
- **Not worth changing:** Financial revalidation at separate boundaries, two-tool catalog, explicit one-step worker, historical evidence and source pins solely for stylistic consistency.


## Completion audit — 2026-10-15

This section closes the repository-hardening task against its full Phase 0–18 checklist. It incorporates the [second sweep](repository-hardening-second-pass.md) rather than treating the first implementation SHA as the final state. The previous turn made verified progress: it committed the recovery fix and obtained passing host/containment evidence. This continuation checks completion; it does not reopen the separate real-money release project.

Repository `kujolang/payments`, branch `main`: original baseline `ea2f2242489ecd77c7a040a1cb67f49b5383763e`; financial implementation `7766181d0732104c9d979de9467e821762f711d9`; initial inspected snapshot `a41d67286525c904af671b84bf573c0d5ddb522a`; ending tested implementation including fixture diagnostics `7659aa310c03b86c692126d5a436a1118f580975`. Between `7766181` and `a41d672`, only two second-pass report files changed. Commit `7659aa3` adds failure-only scalar diagnostics in `tests/reconciliation.kujo`; production code remains identical. The failure-only diagnostic has independent synthetic positive/forced-negative checks and a fresh Linux run. This closure is another documentation-only commit; its final commit SHA is supplied in the engineering receipt and Git history, not embedded recursively in its own contents.

### Findings disposition

| ID | Priority | Area | Finding | Evidence | Action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| KPH-001 | P1 | Build integrity | Optimized Python removed critical runtime/source/receipt checks | Bad hashes accepted under `-O`; integrity fixtures exercise normal, `-O`, `-OO` | Explicit guards in bootstrap, runtime fetch, Workcell setup/runner | Fixed in `5ee7cb1`; regression suite retained |
| KPH-002 | P1 | Resource/publication | Cache reads buffered the full binary; failed replacement could destroy the previous cache | 8 MiB allocation probe and fsync/replace fault injection | Stream bounded cache hashing and atomically publish a verified staged file | Fixed in `5ee7cb1` |
| KPH-003 | P2 | Supply chain | Four optional MCP dependency entries flagged by advisory database | Locked dependency audit; advisory applicability reviewed separately | Patch SDK and transitives without increasing dependency count | Fixed in `9653cbb`; fresh audit zero advisories |
| KPH-004 | P2 | Package efficiency | Promotional media entered library package inputs | 45 files / 5,285,320 bytes; real native package fixture | Exclude media, preserve hosted access, enforce 1 MiB payload budget | Fixed in `6bc4526` |
| KPH-005 | P1 | Verification | Optimized Python could remove test assertions | Optimized-runner negative fixture | Refuse optimized verification before launching Kujo | Fixed in `5ee7cb1` |
| KPH-006 | P2 | Documentation | Setup omitted MCP install; sandbox status described implemented components as missing | Compared setup commands and source entrypoints | Correct deployment/package/sandbox guides without relaxing acceptance gates | Fixed in `6bc4526` |
| KPH-007 | P2 | Recovery bounds | Initial source query and lock wait could exceed requested work limit; metadata scan unnecessarily unbounded | One-second operations killed by three-second outer timeout; 5,000-row scan; invalid API bounds | Initial SQL progress handler, capped busy wait, two-row cardinality check and integer admission | Fixed in `7766181`; four new regression methods |
| KPH-008 | P2 (test reliability) | Reconciliation fixture reliability | Fresh baseline failed once at `unknown_after_charge` before any current-turn source edits | Baseline log, unchanged isolated reconciliation pass and 30 passing fresh seed attempts | Preserve status/code/claim/charge counts on failure; no assertion weakening, timeout increase or automatic retry | Diagnostic added; underlying intermittent cause remains unproven |

### Requirement-to-evidence map

Each row records review coverage, not a claim of exhaustive formal verification. Historical before/after evidence remains in the two companion reports; current-state checks are in [closure evidence](repository-hardening-closure-evidence.json).

| Phase | Evidence inspected or executed | Disposition |
| --- | --- | --- |
| 0 — Repository understanding | `src/{domain,identity,gateway,application,storage,providers,executor,client}`, contracts, root exports, manifests/locks, examples, CI, deployment and release checklist | Buyer-side library and privileged executor ownership documented; no seller-side or workflow/policy duplication introduced |
| 1 — Baseline | Original baseline/remainder logs, second full baseline, fresh full suite before closure edits | Existing timing failures and the new unexplained seed assertion remain recorded; no assertion or deadline weakened |
| 2 — Complexity | Provider five-method contract, one-step worker, storage transactions, identity admission, framing and repeated final validation | Cohesive financial checks retained; no evidence justified generic abstraction or cosmetic split |
| 3 — Runtime | MCP/Link lifecycle fixtures, process counters, cache probe | Same workload before/after allocation proof; no cross-platform latency comparison or unmeasured speed claim |
| 4 — Resources | Atomic cache staging/fault cleanup, recovery deadlines/cardinality, MCP admission/process bounds and launcher cleanup | Measured improvements and explicit bounds covered by regressions |
| 5 — Agent context | Two-tool projection, single startup catalog, conformance byte budgets and compact receipt references | 3,065-byte schemas, 182-byte summary and 438-byte envelope retained; byte counts are not token counts |
| 6 — Output | Generic provider/process failures, compact status, evidence references, sentinel tests, ignored detailed audit logs | Detailed evidence preserved outside routine output; errors remain inspectable without raw secrets |
| 7 — Failure semantics | Cache failure preservation, recovery publication, interrupted intake/execution, receipt failure and reconciliation tests | Failure fixtures, not only successful paths; no automatic replay of ambiguous financial effects |
| 8 — Security | Host-owned principal, approval binding, private provider modules, bounded HTTP, installed routes, filesystem checks, architecture mutations and actual OCI/Workcell probes | Integrity/availability fixes validated; same-user administrator and deployment limits explicit |
| 9 — Concurrency/state | SQLite CAS/permanent claims, one-use permits, cancellation races, shared recovery write barrier, killed/live-original fixtures | At-most-one synthetic dispatch and observation-only recovery retained; no state migration introduced |
| 10 — Contracts | Six canonical Ability definitions, flat principal compatibility, immutable snapshots, exact-money and identity vectors, package exports | Public payment and storage contracts unchanged; invalid private maintenance bounds rejected earlier |
| 11 — Dependencies | Exact Git pins, independent bootstrap tree comparison, reviewed npm lock, archive/binary hashes and pinned workflow actions | No new dependency; patched optional dependencies, fresh advisory audit and optimization-resistant verification |
| 12 — Tests | Eleven deployment-integrity methods, expanded Workcell cases, four recovery-bound methods, package sentinels, existing full suite | Behavior and negative fixtures added for verified defects |
| 13 — CI/ratchets | `scripts/test.sh`, Fence mutations, 1 MiB package budget, MCP byte/process budgets, workflow host/containment jobs | New regression tests run normally; growth policy documented; no timeout increase or disabled test |
| 14 — Documentation | README setup, package/deployment/sandbox/recovery guides against actual launchers and fixtures | Affected docs corrected; historical evidence preserved; findings table and completion mapping added |
| 15 — Human/agent operation | README quickstart, public package shims, named selective test scripts, architecture guide, structured status/error contracts | Clear setup/verification entrypoints; no new agent-specific framework or giant tool surface |
| 16 — Dead weight | Package source selection and native install, tracked media use, compatibility contracts and examples | Media excluded from installation but retained for documented use; no unsupported deletion of shims/fixtures/history |
| 17 — Implementation | `5ee7cb1`, `9653cbb`, `6bc4526`, `7766181`, `7659aa3`, linked source changes and regression evidence | All safely evidenced fixes implemented; KPH-008 remains explicitly unproven rather than receiving a speculative fix |
| 18 — Completed verification | Fresh baseline plus full rerun, syntax checks, cache reproduction, dependency audit, exact-revision Linux host/containment evidence | Results and exact commands recorded in closure evidence; no introduced regression left unresolved |

There is no separate configured library lint, formatter, static typecheck or binary-build target. Kujo VM/interpreter execution, Fence, actual Kennel packaging/installation, Python AST parsing, JSON parsing, shell syntax and the synthetic integration/E2E fixtures are the applicable checks. Promotional-video build tooling is not a payment runtime dependency. No live provider or financial transaction was used to claim E2E acceptance.

### Explicit compatibility review

| Interface | Result |
| --- | --- |
| Public Kujo APIs, Ability identities, network contracts | Unchanged; `git diff ea2f224..HEAD -- src contracts payments.kujo payments_http.kujo kennel.lock` is empty |
| CLI arguments, successful exit/result shapes | Unchanged; optimized test runner now deliberately refuses unsafe verification; invalid setup still exits nonzero |
| Financial file formats, schemas and configuration | Unchanged; no journal migration or approval/hash rewriting |
| Environment variables | No renamed or removed variable |
| Python maintenance calls | Boolean/fractional bounds fail before filesystem output; integer CLI behavior preserved |
| Runtime cache filesystem behavior | Failed writes preserve prior contents; staged replacement and temporary-file cleanup are tested |
| Package consumers | Promotional media intentionally excluded; documentation links preserved; real client imports/install tested; no consumer migration required |

### Cross-repository follow-ups and remaining work

| Classification | Repository / contract | Evidence and impact | Recommendation / dependency |
| --- | --- | --- | --- |
| Needs more evidence | Kennel native archive builder at the pinned revision | Original local 180-second timeouts; later unchanged-limit local/Linux passes. Growing-buffer construction is a hypothesis, not established cause | Profile only if recurrence warrants it; preserve deterministic bytes and safety checks. No Kennel change required for this audit |
| Existing scoped limitation | Ability v1 nested identity at Payments' pinned dependency | `tests/ability_identities.kujo` retains the historical collision and proves changed definitions are rejected; `docs/identity-compatibility.md` documents flat approval inputs and independent payment-term bindings | General serializer migration belongs to Ability and needs explicit algorithm/receipt versioning. No upstream change required for the frozen Payments profile; this is not a claim about the latest upstream HEAD |
| Needs more evidence / existing release gates | Link provisioning, funding authority, merchant confirmation, selected deployment and operational recovery | Synthetic fixtures cannot establish these live properties; see `docs/release-checklist.md` | Keep developer-alpha claims. These are not newly discovered defects or prerequisites for completing the bounded repository audit |
| P0 / P1 | In-scope verified defects | All demonstrated defects above have fixes and passing regressions | No known introduced regression or newly demonstrated unresolved P0/P1 remains; this does not certify absence of vulnerabilities |
| Needs more evidence | Payments reconciliation fixture | One unexplained seed assertion in the fresh baseline; original temporary journals were removed by the harness; isolated rerun and 30 diagnostic seeds passed | Track KPH-008. Future failure now retains bounded scalar evidence. No financial-domain defect or host-load cause is asserted; the historical passing CI is not used to erase this new failure |
| P2 / P3 | Speculative refactors, cache expansion or purely stylistic cleanup | No demonstrated benefit over existing boundaries | Not worth changing during this pass |

No sibling repository was modified. The newly observed intermittent reconciliation-seed failure is retained for follow-up; it is not labeled fixed or harmless. Existing release and upstream limitations remain visible rather than being converted into unsupported readiness claims.


### Current verification receipt

The fresh baseline at `a41d672` exited 1 after **606.66 seconds**, before any current-turn source edit, at the reconciliation seed assertion `unknown_after_charge`. The original fixture did not preserve its result fields or temporary journals. No cause or actual financial state is inferred from that assertion name. The unchanged isolated reconciliation suite passed; 30 fresh diagnostic seed processes passed. The failure-only diagnostic was then verified by forcing an unexpected synthetic status: rejection remained intact, scalar status/code/claim/charge evidence was present, and no sentinel appeared.

The complete post-diagnostic local suite **passed in 1,219.46 seconds**. Current Linux [run 38687600913](https://github.com/kujolang/payments/actions/runs/38687600913) passed both host and OCI/Workcell containment at `7659aa310c03b86c692126d5a436a1118f580975`. This fresh result supplements the previously revalidated run `38349145665`; it does not erase the baseline failure. Local timing differences are not attributed to a cause or presented as a speed improvement.

Commands executed from the Payments root unless noted otherwise:

```sh
KUJO_BIN="$PWD/.local/runtime-artifacts/34878190347/macos-x64/verified-bin/kujo" PAYMENTS_HEADER_VALUES_RUNTIME=1 /usr/bin/time -p bash scripts/test.sh
KUJO_BIN="$PWD/.local/runtime-artifacts/34878190347/macos-x64/verified-bin/kujo" python3 tests/network/reconciliation_test.py
git show ea2f224:scripts/deployment/fetch_runtime.py > .local/audit-20261015/cache-before.py
python3 docs/audits/runtime-cache-measure.py .local/audit-20261015/cache-before.py
python3 docs/audits/runtime-cache-measure.py scripts/deployment/fetch_runtime.py
npm ls --depth=0 --prefix examples/mcp
git diff ea2f224..HEAD -- src contracts payments.kujo payments_http.kujo kennel.lock
git diff --check
```

`npm audit --omit=dev --json` ran inside `examples/mcp` and returned zero advisories across 94 dependency entries. The exact Python AST/JSON/shell-check command and results are retained in the [closure evidence](repository-hardening-closure-evidence.json): 56 Python files, 79 JSON files and 10 shell scripts passed before these documentation edits. The new JSON artifact and Markdown references were checked separately. There is no newly added production dependency.

The repeated 8 MiB cache probe again measured **8,703,996 → 2,417,831 bytes** of peak Python allocation. Its single elapsed samples were 128.402 and 109.883 ms; these are not statistical latency claims. Current local and Linux runs retain schema/summary/envelope sizes of **3,065/182/438 UTF-8 bytes** and project/request/inspect process counts **1/13/9**. The package fixture passed with 107 files and 163,824 compressed bytes before these closure documents; final documentation inputs are separately checked against the existing 1 MiB payload budget. No binary-size or tokenizer-specific improvement is claimed.

All 13 first-sweep and six second-sweep recorded local log hashes still match their retained files. Current log hashes and the initial failure are preserved in the closure artifact. KPH-008 remains open for evidence-driven follow-up despite subsequent passing runs. The repository audit is complete within these stated limits; real-money release acceptance is not.
