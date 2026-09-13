# Kujo Payments

Buyer-side payment intent, authorization, one-shot execution and reconciliation through Ability. In development; no live provider is enabled.

The requesting agent receives purchase aliases and compact status. A separately deployed trusted executor owns provider credentials and financial dispatch. Commerce remains seller-side; Payments does not provide a workflow engine or policy language.

## Build status

Implementation follows the accepted September 12 architecture review in kujolang/docs.kujolang.ai, commits d10480e and b99d0e8. See [implementation status](docs/implementation-status.md). The full objective remains open until its implementation and required verification gates pass. Review fixtures do not certify a payment executor.

## Development

Set `KUJO_BIN` to an absolute Kujo 1.4.0 executable. Run `python3 scripts/ci/bootstrap.py` to install and verify the locked core and optional integration dependencies, then `npm ci --prefix examples/mcp --ignore-scripts --no-audit --no-fund`. The full host suite additionally uses Python 3 and Node (CI pins 24.20.0). Run `bash scripts/test.sh` from this directory. Normal tests use synthetic data and never move money. Core Payments itself has no Node, MCP, Agents SDK or Dispatch dependency.

## Package imports

Installed consumers use `from payments import purchase_request, purchase_status` and the trusted transport factory `from payments_http import http_transport`. See [package installation](docs/package-installation.md) for the experimental package boundary and tested installation path. Executor setup and development examples require a source checkout.

## Runnable fixture

See [local fixture](examples/local-fixture/README.md) for a synthetic purchase through the gateway, provider authorization, host Ability approval, one-use submission and authoritative observation. Optional [programmatic cancellation](docs/cancellation.md) uses explicit revision inspection. Agent-facing operations are request and status; the executor and provider callbacks remain private to trusted host code.

The injected gateway authentication callback is an embedding boundary. The [deployment guide](docs/deployment.md) documents the scoped-token HTTP service and tested OCI profile. Operator financial authorization, Link execution and remaining live-provider gates are still required before real payment credentials are used.

[Architecture enforcement](docs/architecture-enforcement.md) documents the checked dependency graph and negative tests.

[Operator approval and bounded worker](docs/operator.md) describes the private review/approval command and host-driven lifecycle step.
