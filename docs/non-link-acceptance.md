# Non-Link acceptance and operator rehearsal

This procedure verifies repository-controlled behavior without payment accounts,
provider credentials or money movement. It does not approve a production
installation. Use an exact reviewed source commit; keep runtime, test results and
container evidence tied to that commit.

## Reproduce the reference checks

From a clean Linux checkout, follow [deployment setup](deployment.md#clean-linux-verification)
for the pinned runtime, development dependencies and MCP dependencies, then run:

```sh
bash scripts/test.sh
python3 scripts/acceptance/reconciliation_stress.py --samples 100 --workers 2
bash scripts/deployment/test_oci.sh
```

`KUJO_BIN` must be an absolute verified executable. Docker Buildx and the pinned
Workcell runtime are required for the last command; CI installs these separately.
The host suite has no provider financial calls. Public dependency downloads are
required for the native package fixture. Do not provide real credentials to tests.

| Gate | Executable evidence | What a pass establishes |
| --- | --- | --- |
| Request service | `tests/network/http_test.py`, `provision_test.py`, `cancellation_test.py` | Scoped credentials, tenant separation, bounded requests, replay and cancellation behavior. |
| Agent containment | `scripts/deployment/test_oci.sh` | The declared Linux namespaces, mounts and network profile deny the tested credential access paths; trusted intake still works. |
| Installation | `tests/network/package_install_test.py` | Pinned native Kennel packaging, deterministic archive, private-file exclusions, clean consumer installation and public imports in VM/interpreter. |
| Stored-state upgrade | `tests/network/migration_test.py` | The explicit frozen v1-to-v2 migration and its rejection/rollback cases. Not arbitrary runtime or package upgrades. |
| Incident/recovery | `control_test.py`, `recovery_test.py`, `recovery_verification_test.py`, `recovery_set_test.py` under `tests/network` | Pause, WAL capture, quarantine, tamper rejection, shared write barrier, bounded failure and killed capture. |
| Operator rehearsal | `tests/network/operational_recovery_test.py` | Pause an ambiguous execution, capture and verify the declared journals, reconcile only a separate quarantined working copy, retain one processor charge, deny spending resume and preserve the original publication. |
| Interrupted work | `tests/network/interrupted_execution_test.py`, `reconciliation_test.py` | Process-kill boundaries, explicit abandonment before claim, permanent claims afterward and observation replay. |
| Intermittent seed investigation | `scripts/acceptance/reconciliation_stress.py` | Bounded fresh-process samples with independent claim, approval and processor counts; failures are recorded, never retried into a pass. |

The stress report includes sample counts, worker count, runtime hash and elapsed
time. Any failed sample makes the command fail. Only scalar counts and normalized
failure categories are retained; raw process errors and private journals are not.
Passing stress does **not** resolve KPH-008's unexplained historical failure.

## Recovery rehearsal boundary

The new rehearsal uses a synthetic processor that has no charge deduplication
constraint. A charge occurs, its response is lost, and the core records an
ambiguous result. The administrator pauses execution and captures the core plus
processor evidence. This is a local stand-in for separately retained payment
history; a real provider is not backed up by copying SQLite.

Verification runs against an immutable publication. Observation writes go into a
separate working copy. That copy first receives an unknown observation, replays
it without another provider call, then obtains authoritative confirmation with a
fresh observation key from the independent processor. It becomes `succeeded`
while retaining its permanent financial claim and consumed approval. No submit
or credential-issuing method is available during this reconciliation. The
original core stays paused and ambiguous; the rehearsal does not merge state
back into it. Even after confirmation, the recovered copy cannot resume spending.

For a real incident, follow [recovery snapshots](recovery-snapshots.md), inventory
all private journals, retain custody of the original publication and use the
installed provider's supported observation authority. Never treat a historical
processor copy as current settlement evidence. Loss of authoritative history
still requires a separate recovery decision; this rehearsal adds no automatic
restore, financial re-entry or claim-reset path.

## Installation-specific work that cannot be certified by CI

Before approving a deployment, record the actual host/container image, runtime,
TLS edge, authenticated operator, journal inventory, backup destination and
retention policy. Run the hostile access probes against those exact boundaries.
Verify edge body/rate limits, token rotation, monitoring, private backup access
and observation-only recovery under the real service identities. Choose explicit
recovery-time and data-loss objectives and measure the rehearsal against them.

A generic OCI pass cannot attest to an unspecified host, external backup service,
operator renderer or production log collector. The repository does not provide a
turnkey production financial-worker service. Installing that service also needs
the provider/confirmation ports described in [deployment](deployment.md).

The native package fixture does not publish or verify a public registry release.
Before release, build/install the chosen artifact and verify the actual release
provenance and supported runtime. Neither a successful import nor a database
migration proves every upgrade safe. Preserve current journals across an app
rollback; do not restore stale spending state to roll back code.

Keep the [release checklist](release-checklist.md) open until the selected
deployment and provider acceptance records exist. No real-money or PCI readiness
claim follows from these synthetic checks.

## Recorded acceptance — October 18, 2026

[CI run 39151801328](https://github.com/kujolang/payments/actions/runs/39151801328)
passed the full host suite and actual OCI/Workcell containment at
`5b91f7ca30a77a68504a74344f6202356d3ac46b`. The full local host suite also passed.
The new operator recovery rehearsal passed locally and in Linux CI. Native
packaging installed a 109-file, 173,305-byte archive into a fresh consumer.

Fresh-process stress passed 100 local samples and 40 Linux samples, with no
failed samples retried. Forced child failure produced a nonzero result without
leaking a sentinel; invalid bounds and optimized Python were rejected. KPH-008
remains unexplained, not fixed. Source/runtime scope, result counts and retained
log hashes are in the [acceptance evidence](evidence/non-link-acceptance-20261018.json).

These results accept the named synthetic reference checks, not all production
release gates. No production host was selected or changed, no published package
was released, and no real provider enrollment or purchase was performed.

## Intermittent seed investigation — October 18, 2026

KPH-008 remains open. An additional 200 fresh processes before the diagnostic
change and 200 afterward passed with four workers. The historical log contains
only `unknown_after_charge`; the original result and journals were removed.
Passing repetitions cannot recover that missing evidence or establish a cause.

Two deterministic fault injections reproduce the same assertion with materially
different financial states:

| Injected fault | State | Claim / charge count | Normalized error |
| --- | --- | --- | --- |
| Preflight audit rejection | `ready` | 0 / 0 | `ability_audit_failed` |
| Observation persistence failure after submission | `executing` | 1 / 1 | `storage_failure` |

These are controlled examples, not diagnoses of the historical incident. The
second retains its financial claim; it must be observed, never resubmitted.

A verified diagnostic defect was fixed: the stress collector discarded the
fixture's status and error code before deleting its temporary journals. The
fixture now emits a bounded machine-readable failure object; the collector
retains only allowed scalar fields and the process exit, alongside independently
queried claim/approval/charge counts. Unrecognized codes become `unrecognized`;
raw errors and journals are not exported. Sentinel output makes even a zero-exit
child fail. Regular fixtures clear test-only fault controls.

`tests/network/seed_diagnostics_test.py` runs both actual injected failures,
checks the independent journals, verifies exactly one child invocation, and
checks malformed/oversized/private diagnostics and timeout handling. The old
collector from `f090c48` was run against the same fault-enabled fixture and lost
both status/error pairs. No payment execution, retry, approval or persistence
behavior was changed to make the original assertion pass.

On recurrence, retain the CI stress artifact and source/runtime identity. Use
`seed_diagnostic`, `process_exit` and the independent counts to locate the failing
phase before changing production behavior. Do not infer zero charges from a
missing/unreadable processor journal or close KPH-008 from another green run.

The [investigation evidence](evidence/reconciliation-investigation-20261018.json)
records the local checks and [CI run 39153564005](https://github.com/kujolang/payments/actions/runs/39153564005)
at `41d19bfb1e367c959fb5f20b59446fdb2799f381`: full Linux host suite, 40 fresh
stress samples and actual OCI/Workcell containment all passed. The original
KPH-008 release concern remains open.

## Admin and installation acceptance — October 18, 2026

The operator and control shell launchers now reject unsafe configuration, journal
and SQLite sidecar paths before entering Kujo. Tests cover 38 refusals and actual
bound review, approval and pause with no financial claim. This enforces POSIX
ownership and mode prerequisites; it does not establish host authentication,
ACL isolation or protection against a hostile process with the same user ID.
Embedded callers must enforce equivalent prerequisites.

The installed client now exercises authenticated request, replay, status and
authentication rejection against the gateway in both VM and interpreter modes.
A separate fresh consumer installed the exact source commit from GitHub through
pinned Kennel, validated its lock, matched installed source bytes, and imported
without custom module paths. No registry release or provider purchase was made.

[CI run 39155351846](https://github.com/kujolang/payments/actions/runs/39155351846)
passed the Linux host suite and actual OCI/Workcell containment at
`c7ff956d8d291bcd1c9c0fb595cd16f42c5cdc72`.
The first run exposed a recovery fixture that could leave SQLite sidecars with
public mode bits. The fixture now creates journals under a private umask and
closes read connections explicitly. This is not a diagnosis of KPH-008.

The [acceptance evidence](evidence/admin-install-acceptance-20261018.json)
preserves the initial failure, corrected run, source pins and local log hashes.
Actual deployment acceptance, authoritative financial-history recovery, release
artifact acceptance, KPH-008 and provider acceptance remain open; see the
[remaining release inputs](release-checklist.md#remaining-non-provider-acceptance-inputs).

## Installed gateway acceptance — October 18, 2026

At `82c952cadde6d466c80cb374de79a9c8af57d649`, the native package fixture
runs both client and gateway from installed files. The executor project's own
locked dependencies must be installed and validated; consumer imports alone did
not make Ability resolvable when starting the gateway from its package directory.
The corrected fixture passes authenticated request/replay/status/denial in VM and
interpreter modes without custom module paths. The existing observation-only
recovery rehearsal also passes locally. [Recorded local evidence](evidence/installed-gateway-acceptance-20261018.json)
includes runtime identity, package size and log hashes. These checks do not
publish a registry release or accept a production installation.

Use the [deployment acceptance worksheet](deployment-acceptance.md) to select
staging and record installation-specific evidence. The deployment owner has not
yet selected a host or recovery targets; these remain explicit inputs.
