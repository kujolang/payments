# Installed client package

Payments remains experimental and has not passed the real-money release gates. There is no Payments registry release or production deployment implied by the packaging fixture. Choose a reviewed full commit in a project's Kennel dependency manifest and retain the generated lockfile. The manifest declares Kujo 1.4.0 as its minimum; the recorded verification uses pinned 1.4.0 binaries, not arbitrary later releases. Retain the exact Ability dependency pin and verify runtime upgrades before use.

The supported installed import modules are flat Kujo modules:

```kujo
from payments import purchase_request, purchase_status, purchase_inspect_revision, purchase_cancel
from payments_http import http_transport
```

The root shims forward to the existing client implementation. `package.exports` describes those exports but does not create runtime namespaces: do not use `payments.client` or `payments.http_client`. No custom `KUJO_MODULE_PATH` is required in the tested fresh consumer project. The package's `public_api = false` and experimental status remain unchanged.

The deterministic transport callback receives the existing request/status/cancellation envelope. The HTTP transport is configured by trusted harness code with a scoped gateway token and the canonical output schema, available as `output_schema` in `contracts/abilities/inspect.json`. That transport token authorizes the limited gateway operations; it is not a provider payment credential and must not be supplied by model arguments. Constructing an HTTP transport does not make a request. The normal agent surface remains request and status; revision inspection/cancellation are optional programmatic controls.

The native registry packaging allowlist includes the two shims, `src`, `contracts`, administrative maintenance scripts, operational documentation, README, license and core lockfile. It excludes tests, evidence directories, local state, optional integration dependencies, CI configuration and unrelated repository files. Kennel's publisher additionally rejects common credential/environment files and packages only the selected Git commit. This is a reproducible source package, not an executor image or a secret scanner. Unreviewed secrets committed inside an allowed ordinary source file can still be packaged; source review and repository secret controls remain necessary.

GitHub/file installation and registry archive installation are distinct Kennel paths. A Git checkout can contain additional tracked development files even when registry packaging excludes them; do not infer a process isolation boundary from either file selection or module exports. Administrative Python scripts and provider source in the archive are privileged code, not agent tools. Run executor/deployment setup and the complete development suite from an exact source checkout using the repository instructions. The archive is not a supported live restore or a turnkey payment service.

`tests/network/package_install_test.py` checks the actual pinned Kennel builder and installer, not a replacement archive generator. It creates a disposable Git fixture and synthetic release metadata, builds twice to verify deterministic output, inspects and extracts the native archive, checks deliberately tracked forbidden-path sentinels, runs real Kennel add/install validation into a fresh consumer, then imports both client modules in VM and interpreter modes with custom module paths removed. Callback envelopes and HTTP factory construction are exercised; no HTTP/provider call or money movement occurs. No tag, registry artifact or release is created in the Payments repository or published externally. The test fetches the pinned public Kennel and Ability sources; it is synthetic, not fully offline.
