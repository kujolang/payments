# Payments tools in an Agents SDK harness

This optional example projects the canonical Payments request/inspect Ability definitions into exactly two SDK tools: `purchase_request` and `purchase_status`. `tools.kujo` accepts installed client callbacks, not provider handlers or credentials. The server still owns principal resolution, actual Ability execution, final authorization and financial claims. Request keys derive from the host namespace and business purchase reference, remaining stable across agent runs.

No Agents SDK or AI SDK source change is required. The example pins Agents SDK and its own transitive Ability dependency in a separate Kennel project; Payments core keeps its independent Ability pin. Run from a clean checkout after `scripts/ci/bootstrap.py` to install all development dependencies, or install this example's manifest with the pinned Kennel workflow.

`run.py` stages the exact public Payments client sources, canonical request/inspect definitions and installed SDK in an isolated temporary module tree. This avoids mixing the SDK's documented `src.agents.*` imports and dependency resolution with Payments' own `src` tree. It copies no Payments executor, provider, database or private configuration. Python only stages/supervises the example; SDK invocation and HTTP client code are Kujo.

The trusted harness needs `KUJO_BIN`, `PAYMENTS_CLIENT_ENDPOINT`, a request/status-only `PAYMENTS_CLIENT_TOKEN`, and `PAYMENTS_PURCHASE_JSON`. Then run `python3 examples/agents-sdk/run.py`. HTTPS is the default. `PAYMENTS_LOCAL_FIXTURE=true` permits only the existing explicit loopback fixture profile. Normal CI starts a temporary synthetic server and never reaches a payment provider.

`main.kujo` is the short composition example. `conformance.kujo` exercises the real SDK registry against the HTTP service: exactly two tools, cross-run replay, current status, changed-term conflict, caller-principal/hidden-operation denial and normalized callback exceptions. `tests/network/http_test.py` also verifies unchanged stored terms and no token output/persistence.

## Receipt and privilege boundaries

`register_ability_gateway_tool` requires a canonical Ability gateway-call response with a full matching receipt. Payments' HTTP endpoint intentionally returns compact domain summaries. This example therefore uses the SDK's existing `register_ability_tool` to bind a safe client function; it does not fabricate a receipt or claim SDK execution evidence is the server's financial journal. Model results contain compact status, while authoritative records remain server-side.

The SDK tool handler runs in the trusted harness. Do not give an untrusted Workcell the harness environment, callback objects, client token or filesystem. An LLM tool interface alone does not enforce that physical boundary. Use the separately tested agent/harness/executor deployment separation and validate it for the actual harness. No provider credential belongs anywhere in this example.

SDK approval policies can govern invocation of the request tool; they never replace Payments' final approval. Callback errors are normalized before the SDK's exception wrapper, and unexpected transport fields are rejected. These checks are not a completed all-sink secret-leak conformance suite.

## Recovering an incomplete request

A validated 409 error observation remains a failed SDK tool call. The normalized handler error has kind `payments_operation_incomplete` and contains only the compact summary in `details.payment`; the SDK preserves it under `error.details.handler_error`. The example entrypoint extracts that execution ID and performs a fresh status read. It does not claim request success or retry intake. A status response must match the requested execution ID even when it carries an error observation.

`tests/network/recovery_projections_test.py` runs the actual SDK client against synthetic incomplete, malformed, authentication-failure and server-error responses. Schema/envelope violations and unrelated errors cannot supply an observation; no private error text is forwarded. The independent core crash fixtures prove how an authentic gateway produces such observations.
