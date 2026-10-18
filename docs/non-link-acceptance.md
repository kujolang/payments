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
