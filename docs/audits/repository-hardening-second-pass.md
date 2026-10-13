# Payments second hardening sweep — 2026-10-13

## Scope and result

Manual repeat review of revision `666a27cea83bd135cd8ac196632bc4134587734f`, following the [first sweep](repository-hardening.md). No security-plugin result is claimed. Changes remain inside Payments; no real credentials or provider transactions were used.

The complete local baseline passed in **585.85 seconds** before production files changed. The review found an availability defect in offline recovery: the initial source-schema query had no SQL deadline handler, and its SQLite lock wait was always five seconds even when the requested work limit was one second. This is an administrative maintenance boundary, not a demonstrated agent-accessible credential or financial-execution exploit.

Fix: `7766181d0732104c9d979de9467e821762f711d9` (`fix: bound initial recovery snapshot validation`). The source connection now has a progress handler before schema validation and caps its initial busy wait at the smaller of five seconds and the configured deadline. Metadata validation reads at most two version rows, which suffices to reject invalid cardinality. The Python entrypoint rejects non-integer bounds before creating an output directory, consistent with the CLI, verifier and recovery-set interfaces.

## Reproduction and verification

| Check | Before | After |
| --- | --- | --- |
| Malformed `payments_meta` view performing a large recursive aggregate; one-second work limit | Still running when the outer three-second process timeout killed it | Sanitized failure in 1.080 seconds; no database or manifest published |
| Source held under `BEGIN EXCLUSIVE`; one-second work limit | Still waiting when the outer three-second process timeout killed it | Sanitized failure in 1.116 seconds; no database or manifest published |
| Malformed metadata table with 5,000 version rows and a 1,000-instruction SQLite budget | Full scan exhausted the instruction budget | Rejects after observing two rows without exhausting the budget |
| Boolean/fractional Python bounds | Could reach database access and create the destination | Explicit rejection before destination creation |

These are local synthetic measurements, not provider latency or throughput claims. No general speedup is claimed. The four new test methods run in normal CI through `scripts/test.sh`; they also passed under Python `-O` and `-OO`. Their subprocess limit is three seconds around a requested one-second work deadline; existing timeouts and tests were not relaxed.

The focused post-change run passed in **11.631 seconds**: the new bounds tests, existing recovery snapshot tests, immutable publication verification, and five-journal recovery-set tests. This includes committed WAL content, v1/v2 compatibility, permanent quarantine, stale-copy claim denial, migration lineage, tamper/path rejection, aggregate size limits, writer exclusion, fault injection and killed capture. Python compilation, shell syntax and `git diff --check` passed.

Linux host and OCI/Workcell verification: [run 38349145665](https://github.com/kujolang/payments/actions/runs/38349145665), source revision `7766181d0732104c9d979de9467e821762f711d9`. **Both jobs passed.** The host job ran the full synthetic suite. The containment job rebuilt the pinned Workcell runtime and passed the actual OCI credential, environment/process, socket, command, mount/symlink, network and artifact-isolation checks. No readiness claim extends beyond these fixtures.

## Boundaries reviewed

| Area | Source and evidence | Outcome |
| --- | --- | --- |
| Recovery and filesystem publication | `scripts/maintenance/{recovery_snapshot,verify_recovery,recovery_set}.py`, frozen SQL profiles, recovery fixtures | Fixed initial validation bounds; retained observation-only quarantine, private publication, no-overwrite behavior, fixed manifest paths and source write reservations. |
| Trusted operator setup | `src/executor/{sandbox_configure,control}.kujo`, shell entrypoints and `scripts/private-sandbox.sh` | No new evidence justified changing the installed administrator authority or sandbox configuration contracts. Same-user/host-administrator access remains outside isolation guarantees. |
| Financial lifecycle and authority | `src/application/execution.kujo`, `src/storage/port.kujo`, provider contract, lifecycle and interrupted-execution fixtures | Existing permanent-claim, approval-binding, one-use dispatch and reconciliation tests passed. No financial state, schema or retry behavior changed. |
| Agent-facing transport and processes | Gateway HTTP, public client modules, MCP/Dispatch/Agents SDK launchers, process tests | Existing authenticated tenant boundaries, filtered environments and bounded MCP outputs retained. These wrappers alone are not OS isolation. |
| Dependencies and package | Locked optional MCP dependencies, real package-install fixture, Fence mutation checks | Fresh npm audit reports zero advisories across 94 dependency entries. No dependency or architecture change. Baseline package fixture passed with 105 files and 160,266 archive bytes. |

The baseline still exposes two MCP tools: descriptors **3,065 UTF-8 bytes**, pending summary **182 bytes**, envelope **438 bytes**, and native process counts project/request/inspect **1/13/9**. These are byte counts, not token measurements. The post-change Linux host run confirmed those same sizes and process counts. The maintenance-only change adds no tool, model-visible payload or provider operation.

## Compatibility and limits

Payment Ability definitions, package exports, financial schemas, CLI flags, JSON results, storage profiles and successful recovery formats are unchanged. Only invalid private Python calls using boolean/fractional bounds now fail earlier. Valid CLI calls already parse bounds as integers.

Deadlines remain cooperative: SQLite progress checks and bounded lock waits do not interrupt arbitrary blocked OS filesystem calls. Failed capture may leave a private empty directory for inspection, as before. The fix does not authenticate a snapshot, establish complete financial history or authorize restoring financial execution.

Native Link client provisioning, verified grant/funding authority, and an actual provider-backed sandbox purchase with independent Stripe confirmation remain release gates. This sweep does not establish beta or production readiness. No new unresolved finding or sibling-repository change was required.

The [machine-readable evidence](repository-hardening-second-pass-evidence.json) records revisions, measurements, test results and hashes of ignored local logs. It contains synthetic results only.
