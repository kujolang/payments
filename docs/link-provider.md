# Link reference provider implementation

Status: internal authorization components only. They are not a complete selectable provider, a live-tested integration or a readiness claim. Link is an adapter; no core schema contains SpendRequest, SPT, LPT, card or CLI concepts.

## Source provenance

The native implementation follows the reviewed [Stripe Link source commit](https://github.com/stripe/link-cli/tree/4aa62ba34eaeb884d00041681f5c7801521c0bf8), SDK 0.4.1 and CLI 0.19.1, reviewed September 12, 2026. `deployment/link-source.lock.json` records exact file digests. This is source evidence, not a claim that the remote HTTP API is immutable or version-negotiated. The SDK defaults to `https://api.link.com`; its reviewed implementation adds bearer authentication but no explicit API-version header. We do not invent one.

Relevant primary files are `packages/sdk/src/resources/spend-request.ts`, `resources/interfaces.ts`, `types/index.ts`, `config.ts`, `resources/base.ts`, and the CLI's `commands/mpp/pay.tsx`, `decode.ts`, `utils/format-amount.ts`. The formatter explicitly treats amounts as minor units. The reviewed MPP flow creates an SPT spend request with integer amount, currency and network ID, then retrieves an SPT after approval. Kujo uses exact minor-unit integers and does not adopt the CLI's JavaScript numeric parsing or automatic retry loops.

## Implemented boundary

`src/providers/link/api.kujo` constructs a private bearer-authenticated transport to the fixed official origin. It permits only spend-request creation and retrieval paths, refuses delegated creation and arbitrary URLs, uses DNS pinning/private-address denial, disables redirects, caps requests/responses, and requires enough deadline for a bounded five-second call. It does not retry HTTP 401 or any other error. Raw error bodies and exceptions become fixed private error codes. Successful native bodies remain privileged adapter data, never generic receipts or tool output. No CLI or shell is invoked.

`authorization.kujo` owns a private SQLite issuance journal distinct from the generic payment store. It reserves a reference before the POST and makes that reservation permanent. The native idempotency key binds snapshot, tenant, account alias, provider network, payment-method selection and test mode. It supplements the local one-shot reservation; unknown native idempotency retention is not treated as permission to recreate a request after a lost response.

A returned native ID is stored without the response body; it cannot be replaced or shared by two local references. Subsequent calls observe the existing request. If a create succeeded remotely but its response/ID was lost, the state remains unknown and requires an independently verified provider lookup/import workflow. This component deliberately has no speculative search-and-match recovery and never issues a replacement.

Approved status is accepted only with the known native ID and exact integer amount, currency, credential type and network binding. Those fields are optional in the broad SDK TypeScript type; missing or unexpected values therefore fail closed here. Actual account/API fixtures must establish their availability before this path is enabled. Native `succeeded` is not proof that a registered merchant settled the Kujo purchase. No native state is converted into a financial receipt.

Native bodies may contain PAN, CVC, SPT, LPT, approval URLs or other private information even when not requested. The adapter drops these from authorization results and persistence. It does not fetch expanded SPT data during approval observation. A future execution-only path may request the SPT, keeping it exclusively within the privileged executor. Approval URL delivery requires a separate authenticated operator channel; it is not an agent tool result.

## Verification and remaining work

Synthetic fixtures cover approved, malformed and mismatched native responses, unknown/succeeded statuses, provider exceptions, lost create responses, restart, permanent issuance tombstones, changed native parameters and sentinel suppression. Four actual Kujo processes share a journal against a deliberately non-deduplicating fake API ledger and produce exactly one native issuance, including the lost-response case. Transport denial tests prove invalid paths/delegated creation/expired deadlines stop before network access; they are not a live HTTPS test.

Remaining implementation: full five-method provider SPI, immutable registered MPP challenge validation, SPT retrieval and one-shot merchant submission, authoritative merchant correlation/observation, provider account/profile identity verification, operator-only approval URL delivery, credential lifecycle and sandbox/live conformance. OAuth acquisition/refresh must stay in a privileged credential service; credentials must not enter the model or generic journal. LPT, raw virtual cards and browser injection remain excluded from V1. Keep the provider unavailable until these required gates have evidence.
