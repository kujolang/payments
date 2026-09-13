# Request service and tested credential boundary

## Local service

Install the pinned Ability dependency. Provision a **new** private directory:

```sh
export KUJO_BIN=/absolute/path/to/kujo
export PAYMENTS_PROVISION_DIR=/absolute/private/payments
export PAYMENTS_PRINCIPAL_JSON='{"type":"user","id":"your-user","tenant_id":"your-tenant"}'
bash scripts/provision.sh
export PAYMENTS_SERVICE_CONFIG="$PAYMENTS_PROVISION_DIR/service.json"
export KUJO_HTTP_SERVER_READ_TIMEOUT_MS=1000
"$KUJO_BIN" run src/executor/gateway.kujo --interpreter
```

Provisioning uses private directory/file permissions, generates a high-entropy scoped request token, stores only its constant-time HMAC verifier in service settings and refuses an existing directory. It prints neither the token nor provider credentials. The example currency table must be reviewed for the deployment. The token expires after 24 hours; restart with reviewed credential settings to rotate or disable it. Keep the token in trusted harness configuration, outside model context. This is a transport credential for requesting/inspecting intents; it grants no provider or execution operation.

The only HTTP route is `POST /v1/payments` with JSON and bearer authentication. Default credentials permit `request` and `inspect`; explicitly scoped programmatic credentials may also permit `inspect_revision` and `cancel` (see [conditional cancellation](cancellation.md)). Credential records bind a principal and allowed operations. Startup validates the [Payments/Ability identity profile](identity-compatibility.md) before opening the database; a structurally valid domain identity can still be unsupported by the installed Ability runtime. The server accepts no caller principal, financial approval or execute endpoint. Response/error projections are bounded. The client rejects redirects, uses DNS pinning and requires HTTPS except explicitly enabled loopback fixtures. Unknown transport outcomes must be inspected with the original request identity. [Interrupted invocation observations](interrupted-invocations.md) can recover a committed purchase summary on an exact retry without claiming operation success.

The service defaults to loopback. Do not expose its plain HTTP listener on a public network. Remote deployments need an authenticated TLS edge, request/header limits, rate limits and protected internal routing. Set an 8 KiB body limit at that edge; Kujo's native reader imposes an 8 MiB hard ceiling before the application's stricter 8 KiB JSON check. The native server is a bounded synchronous service, not a high-volume edge proxy. `--interpreter` is required for this HTTP route callback in the tested runtime. API tokens, headers and raw request bodies must not enter edge/application logs.

## OCI reference profile

`deployment/Dockerfile` pins the amd64 Ubuntu manifest and verifies the official Kujo 1.4.0 executable. `deployment/runtime.lock.json` pins archive and executable SHA-256 values. Downloads happen at image build time, never during a payment. Build and run the probe:

```sh
# A connected Docker engine and the pinned Ability package are prerequisites.
export PAYMENTS_CONTAINMENT_RECEIPT=/absolute/path/to/containment-receipt.json
bash scripts/deployment/test_oci.sh
```

The tested topology is:

```mermaid
flowchart LR
  A[Untrusted Kujo workload\nnetwork none; client files only]
  H[Trusted harness\nscoped request token]
  G[Trusted request service\nprivate internal Docker network]
  V[Private mount and service environment\nsynthetic credential canary]
  A -->|safe request through host orchestration| H
  H -->|authenticated HTTP| G
  G --- V
```

The hostile workload and trusted service use separate filesystem, PID and network namespaces. Both are non-root, read-only, capability-dropped, no-new-privileges, with bounded processes/memory and private tmpfs. The workload receives no host home, vault, database, browser profile, Docker socket or payment environment. Its language-level private-network restriction is deliberately disabled in the probe so OS network isolation bears the test.

The test first proves the service can access its private canary. It then checks workload file/process-env/socket/command/symlink/network denial and verifies a distinct trusted harness can submit an intent. `/usr/bin/link` in Ubuntu is a coreutils hard-link utility, not Stripe's wallet CLI; the probe checks absence of the privileged provider executable/mounts rather than conflating those programs. Test fixture mounts use permissive fixture file modes to prove namespace separation; production vault ownership must additionally be restrictive.

This proves the recorded profile's synthetic checks, not resistance to kernel/hypervisor escape, host administrators, a compromised trusted service, or all providers. Docker Desktop's Linux VM is part of the trusted platform; this is not a microVM-per-payment claim. Production Link executor egress, key custody, real approval identity and all-sink leakage tests remain separate release gates. Workcell can supply the agent containment layer, but its profile must reproduce these controls; merely declaring secrets in Workcell would expose them to the workload.

## Financial execution

The network service currently accepts and tracks intent only. Its embedding executor API and fixture example exercise authorization/submission/reconciliation; the operator-facing worker/approval flow and Link live adapter are still under construction. Do not inject real payment credentials into this service merely because the synthetic containment probe passes.

The OCI test runner requires Docker Buildx and explicitly loads built images into the local engine before verification. A successful build-cache export alone is insufficient evidence that the tested local image contains current source.

## Clean Linux verification

The [CI run at 8d44c4d](https://github.com/kujolang/payments/actions/runs/34727010312) passed both the synthetic host suite and current-image OCI checks, including the newer operator and Link modules. `docs/evidence/linux-ci.json` records source/runtime pins, job IDs and full-log hashes. This supersedes the earlier missing current-build coverage, not the limits of the containment threat model. The hosted runner image is recorded by GitHub but is not itself a hermetically pinned build environment. The application runtime and container base are pinned.

For a clean Linux checkout, run `python3 scripts/deployment/fetch_runtime.py`, export `KUJO_BIN` to the resulting absolute `deployment/.runtime/kujo` path, then run `python3 scripts/ci/bootstrap.py` and `bash scripts/test.sh`. Docker Buildx is additionally required for `bash scripts/deployment/test_oci.sh`. Bootstrap downloads pinned public development sources; it does not obtain payment credentials or perform a financial operation.
