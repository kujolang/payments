# Kujo Payments

Buyer-side payment intent, authorization, one-shot execution and reconciliation through Ability. In development; no live provider is enabled.

The requesting agent receives purchase aliases and compact status. A separately deployed trusted executor owns provider credentials and financial dispatch. Commerce remains seller-side; Payments does not provide a workflow engine or policy language.

## Build status

Implementation follows the accepted September 12 architecture review in kujolang/docs.kujolang.ai, commits d10480e and b99d0e8. See [implementation status](docs/implementation-status.md). The full objective remains open until its implementation and required verification gates pass. Review fixtures do not certify a payment executor.

## Development

Kujo 1.4.0 or later is required. Install the commit-pinned Ability dependency with `kennel install` (or `kujo run /path/to/kennel/kennel.kujo --interpreter -- install`). Set `KUJO_BIN` to a built Kujo executable and run `bash scripts/test.sh` from this directory. Normal tests use synthetic data and never move money.

## Runnable fixture

See [local fixture](examples/local-fixture/README.md) for a synthetic purchase through the gateway, provider authorization, host Ability approval, one-use submission and authoritative observation. Agent-facing operations are request and status; the executor and provider callbacks remain private to trusted host code.

The injected gateway authentication callback is an embedding boundary. A network server, real identity adapter and tested physical separation are still required before connecting untrusted agent processes or real provider credentials.
