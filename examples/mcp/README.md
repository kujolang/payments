# Request/status MCP frontend

This optional STDIO frontend exposes exactly `purchase_request` and `purchase_status`. Kujo MCP's pinned `ability_to_mcp_tool` projects the canonical Ability definitions, preserving their schemas and metadata. The official MCP TypeScript SDK owns JSON-RPC initialization, transport and tool dispatch. Each accepted tool call uses the existing Kujo public client in a bounded subprocess. The server never imports Payments executor/provider/storage code or accepts approval, principal, tenant, endpoint or credential arguments.

The existing Kujo Ability packaged bridge has a different gateway route contract and adds `_kujo` approval/invocation controls. This frontend deliberately uses its reusable projection layer instead of pretending the compact Payments endpoint returns full Ability receipts. `_kujo` arguments fail the canonical schema. MCP output contains only the compact domain summary, represented as text plus structured content for protocol compatibility. It is not a financial authorization or fabricated Ability receipt.

## Install and run

From Payments root, install the committed example Kennel lock and run `npm ci --prefix examples/mcp --ignore-scripts --no-audit --no-fund`. `scripts/ci/bootstrap.py` installs/verifies the Kujo development dependencies. Node 24.20.0 is the tested runtime; the example requires Node 22 or newer.

Configure the trusted host with absolute `KUJO_BIN`, `PAYMENTS_CLIENT_ENDPOINT` and request/status-only `PAYMENTS_CLIENT_TOKEN`. Launch `python3 examples/mcp/run.py` as an MCP STDIO server from the Payments root. No endpoint/token appears in tool arguments. A host configuration can use `command: python3`, an absolute path to `examples/mcp/run.py` in `args`, and those trusted environment entries. Keep credentials out of committed host configuration. HTTPS is required except the explicitly enabled loopback fixture profile (`PAYMENTS_LOCAL_FIXTURE=true`).

The launcher stages only public client files, canonical definitions and pinned MCP dependencies. Its child environment is allowlisted. This is file selection, not an OS sandbox: the host must keep the requesting agent outside the trusted harness principal/filesystem/environment. The requesting agent must not launch this server with a provider credential store mounted or readable. The separate Payments executor owns financial secrets and authority. This example needs no Kujo SaaS.

## Bounds and retry behavior

- MCP frames are at most 8,192 bytes with valid UTF-8; the SDK buffer is additionally bounded. Malformed numeric tool-call wire tokens (fractions/exponents/unsafe integers) close the connection before JavaScript can round them into apparently valid integer money. This is stricter than general MCP numeric syntax; reconnect and send integer minor units. Numeric-looking strings remain strings.
- At most four native calls run concurrently. Excess calls return a fixed failure. Client HTTP deadline is five seconds; subprocess deadline is seven seconds, output bound 32 KiB and Node heap limit 128 MiB. No raw child stdout/stderr exception is forwarded.
- One native process generates the catalog at startup; it is cached for the connection. Each accepted call starts one native public-client process. This trades process overhead for reuse of the canonical Kujo money/schema/HTTP checks; it is not claimed to be latency-optimized.
- Request keys derive from a stable example namespace and business purchase reference. Reconnect/retry never invents another key for that reference. Cancellation or frontend loss does not undo completed intake; inspect the existing payment. This frontend cannot dispatch funds.
- Launcher termination cleans up its Node/native process group. Normal child errors and provider/client failures produce fixed messages. No debug flag returns exception bodies or environment values.

## Evidence and dependency scope

`tests/network/http_test.py` uses an actual MCP SDK client against this STDIO frontend and the actual Kujo Payments HTTP service. It verifies exactly two tools, canonical IDs, request replay, status, changed terms, forbidden identity/approval fields, hidden operations and raw numeric/frame rejection. Four total fixture executions across direct, native-client, Agents SDK and MCP paths remain unclaimed. Token scans cover service artifacts and subprocess output. These are component checks, not all-sink or real-provider acceptance.

Pinned Kujo MCP: `07845898ee9f2662d0e0e364973d77cdaac04762`, with its independent Ability dependency. Official transport SDK: `@modelcontextprotocol/sdk` 1.30.0, source gitHead `2d889f2b329e46680ec9bdd565de4616c497825a`; npm lock pins all transitive artifacts/integrities. Install scripts are disabled. Registry audit on 2026-09-13 reported zero known dependency advisories; that is not a security certification. These are optional example dependencies, not core Payments dependencies.

Primary sources reviewed 2026-09-13: [official TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk), [2025-11-25 STDIO transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), and [structured tool results](https://modelcontextprotocol.io/specification/2025-11-25/schema). This example follows the pinned SDK's supported protocol negotiation; it does not claim conformance to later experimental protocol revisions or remote Streamable HTTP deployment.

Local baseline (2026-09-13, Node 24.20.0 and local Kujo 1.4.0; one fixture sample): both tool descriptors total 3,065 compact UTF-8 bytes; one status summary is 182 bytes. Startup/discovery took 786 ms, first request 270 ms, exact replay 227 ms and status 234 ms. These are observed development-host values, not latency promises or tokenizer counts. The conformance run emits the same fields in Linux CI so comparisons retain their environment. Broader performance/token evaluation remains open.

## Incomplete request observations

A validated gateway 409 response may carry a current payment summary even though the operation was not confirmed. This frontend retains it as `structuredContent` with `isError: true` and a fixed explanatory text prefix. It never converts that response into a successful tool result. Keep the execution ID and call `purchase_status`; do not infer that a failed request means no purchase exists. Status observations must match the requested ID. Unauthorized/server failures, invalid summaries and extra envelope fields return the fixed failure without structured content.

`recovery_conformance.mjs` and `tests/network/recovery_projections_test.py` exercise the real SDK, launcher and native HTTP client against bounded synthetic responses. The catalog and its two tools are unchanged. Success text remains the compact JSON summary; only explicitly incomplete error observations add the fixed explanation.
