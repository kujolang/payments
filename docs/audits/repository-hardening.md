# Payments repository hardening — 2026-10-13

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
