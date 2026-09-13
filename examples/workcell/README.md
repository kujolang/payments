# Workcell intent export and trusted payment intake

This example runs an untrusted agent fixture in Workcell's stable Docker lifecycle. The workload has no network, credential mounts, request token, provider environment or payment executor source. It first runs the hostile filesystem/process/socket/network probes, then exports a single `intent.json`. Workcell cleans up the workload and verifies its evidence. A separate trusted harness can validate that untrusted intent through the Payments gateway; authorization and execution remain in the separate private Payments executor.

Workcell receipt verification establishes artifact integrity, not the correctness of a purchase or permission to spend. The gateway still validates canonical request fields, resolves the principal and preserves stable idempotency. The fixture only reaches `awaiting_authorization`; it never moves money. Scheduling, model inference and workflow pause/resume are outside this workload definition.

## Run the fixture

The host needs Git, Python 3, Rust/Cargo, Docker, and Workcell's pinned Kujo host runtime. `scripts/deployment/setup_workcell.py` clones exact Workcell/runtime commits from `source.lock.json`, builds the runtime with Cargo's lockfile and records its binary hash. The host runtime is Kujo 1.2.1 because that is Workcell's tested pin. Payments and the isolated agent use the independently checksum-pinned Kujo 1.4.0 image; do not silently replace Workcell's host pin with the Payments runtime.

From Payments root:

```bash
python3 scripts/deployment/fetch_runtime.py
python3 scripts/deployment/setup_workcell.py
docker buildx build --load --platform linux/amd64 -f deployment/Dockerfile --target workcell-agent -t kujo-payments-workcell-agent:local .
docker image inspect kujo-payments-workcell-agent:local --format '{{.Id}}'
```

Pass the observed image digest, exact installed paths and a new private evidence directory:

```bash
python3 examples/workcell/run.py \
  --workcell-root "$PWD/deployment/.workcell/workcell" \
  --runtime "$PWD/deployment/.workcell/runtime/target/release/kujo" \
  --image-digest sha256:REPLACE_WITH_OBSERVED_IMAGE_ID \
  --output /absolute/private/payment-workcell-evidence
```

The helper stages and commits only `agent.kujo` and the public hostile probe in a temporary clean repository. It does not mount the Payments checkout. It renders `definition.template.json` with the supplied immutable local image ID, validates it, runs Workcell with `--no-pull --summary`, verifies the receipt/manifest and reads only the bounded declared intent artifact. Existing output directories must be private and owned by the invoking user. The returned intent remains untrusted; this helper does not submit it or grant approval.

Adapt the workload source to another agent while preserving the boundary: no secrets/environment allowlist, no network, isolated source, bounded resources and declared artifacts only. If a deployment needs model or tool network access, design and test that separate egress profile; this fixture's no-network proof does not cover it.

## Exact ownership and limits

- Workcell owns disposable source, Docker policy, output/artifact bounds, receipt integrity and ownership-scoped cleanup.
- The trusted harness owns artifact selection and payment-client transport credentials. Do not put either provider secrets or the request/status token into Workcell `secrets`, environment, artifact declarations or caller context.
- Payments owns intent validation, principal resolution, financial authorization, idempotency, execution and reconciliation. Workcell does not become a payment executor.
- Stable Workcell v1 does not accept `--context`; the example correlates Workcell run ID and payment execution ID in separate trusted evidence. It does not adopt an alpha lifecycle merely to attach correlation metadata.
- The local image is pinned by observed image-ID provenance and is not signed. This is a synthetic development/CI profile, not a production image-governance claim. The rootful Docker fixture uses a non-root workload UID, private IPC/PID namespaces, read-only root, dropped capabilities and no-new-privileges. Daemon/kernel/admin compromise is outside this proof; no microVM, Podman or hosted-adapter guarantee is inferred.

## Verification and retained evidence

When `PAYMENTS_WORKCELL_ROOT` and `PAYMENTS_WORKCELL_KUJO` are set, `tests/network/containment_test.py` keeps a separate privileged service with a positive credential canary alive, runs the real Workcell workload, verifies its manifest and submits the exported intent through a separate trusted container. It scans Workcell artifacts, logs, receipts and harness output for the provider canary and request token. The ordinary Docker probe remains an independent control.

Set `PAYMENTS_WORKCELL_EVIDENCE` to a new destination to preserve the Workcell output tree and `boundary.json` after successful checks. CI retains this synthetic evidence as `payments-workcell-evidence` for 14 days. The combined record binds exact source/runtime/image identities and receipt hash to the payment execution ID. Its sensitive service directory and credential values are never copied. Workcell source is unchanged by this integration. Passing scope is limited to the tested Docker host and synthetic canaries; full provider isolation/all-sink acceptance remains a release gate.

The host wrapper requests cancellation through Workcell's operator-owned `--cancel-file` after 60 seconds, then allows 30 seconds for receipt/cleanup completion. An unresponsive coordinator is terminated with bounded escalation; this is reported as **cleanup unconfirmed**, never success. Inspect retained run ownership evidence before scoped operator recovery. The wrapper does not run global Workcell/Docker cleanup or retry the workload. Unit fixtures exercise this escalation; the ordinary successful OCI run does not prove daemon-failure cleanup.
