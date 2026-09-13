# Link reference provider implementation

Status: an internal five-method provider factory with native authorization and immutable merchant HTTP transport. Production installation, authoritative settlement observation and live conformance remain incomplete. This is not a readiness claim. Link is an adapter; no core schema contains SpendRequest, SPT, LPT, card or CLI concepts.

## Source provenance

The native implementation follows the reviewed [Stripe Link source commit](https://github.com/stripe/link-cli/tree/4aa62ba34eaeb884d00041681f5c7801521c0bf8), SDK 0.4.1 and CLI 0.19.1, reviewed September 12, 2026. `deployment/link-source.lock.json` records exact file digests. This is source evidence, not a claim that the remote HTTP API is immutable or version-negotiated. The SDK defaults to `https://api.link.com`; its reviewed implementation adds bearer authentication but no explicit API-version header. We do not invent one.

Relevant primary files are `packages/sdk/src/resources/spend-request.ts`, `resources/interfaces.ts`, `types/index.ts`, `config.ts`, `resources/base.ts`, and the CLI's `commands/mpp/pay.tsx`, `decode.ts`, `utils/format-amount.ts`. The formatter explicitly treats amounts as minor units. The reviewed MPP flow creates an SPT spend request with integer amount, currency and network ID, then retrieves an SPT after approval. Kujo uses exact minor-unit integers and does not adopt the CLI's JavaScript numeric parsing or automatic retry loops.

## Implemented boundary

`src/providers/link/api.kujo` constructs a private bearer-authenticated transport to the fixed official origin. It permits only spend-request creation and retrieval paths, refuses delegated creation and arbitrary URLs, uses DNS pinning/private-address denial, disables redirects, caps requests/responses, and requires enough deadline for a bounded five-second call. It does not retry HTTP 401 or any other error. Raw error bodies and exceptions become fixed private error codes. Successful native bodies remain privileged adapter data, never generic receipts or tool output. No CLI or shell is invoked.

`authorization.kujo` owns a private SQLite issuance journal distinct from the generic payment store. It reserves a reference before the POST and makes that reservation permanent. The native idempotency key binds snapshot, tenant, account alias, provider network, payment-method selection and test mode. It supplements the local one-shot reservation; unknown native idempotency retention is not treated as permission to recreate a request after a lost response.

A returned native ID is stored without the response body; it cannot be replaced or shared by two local references. Subsequent calls observe the existing request. If a create succeeded remotely but its response/ID was lost, the state remains unknown and requires an independently verified provider lookup/import workflow. This component deliberately has no speculative search-and-match recovery and never issues a replacement.

Approved status is accepted only with the known native ID and exact integer amount, currency, credential type and network binding. Those fields are optional in the broad SDK TypeScript type; missing or unexpected values therefore fail closed here. Actual account/API fixtures must establish their availability before this path is enabled. Native `succeeded` is not proof that a registered merchant settled the Kujo purchase. No native state is converted into a financial receipt.

Native bodies may contain PAN, CVC, SPT, LPT, approval URLs or other private information even when not requested. The adapter drops these from authorization results and persistence. It does not fetch expanded SPT data during approval observation. The execution-only submission path requests the SPT, keeping it exclusively within the privileged executor. Approval URL delivery requires a separate authenticated operator channel; it is not an agent tool result.

## Verification and remaining work

Synthetic fixtures cover approved, malformed and mismatched native responses, unknown/succeeded statuses, provider exceptions, lost create responses, restart, permanent issuance tombstones, changed native parameters and sentinel suppression. Four actual Kujo processes share a journal against a deliberately non-deduplicating fake API ledger and produce exactly one native issuance, including the lost-response case. Transport denial tests prove invalid paths/delegated creation/expired deadlines stop before network access; they are not a live HTTPS test.

Remaining implementation: production provider configuration and authoritative account/merchant observation adapters, provider account/profile identity verification, operator-only approval URL delivery, credential lifecycle and sandbox/live conformance. OAuth acquisition/refresh must stay in a privileged credential service; credentials must not enter the model or generic journal. LPT, raw virtual cards and browser injection remain excluded from V1. Keep the provider unavailable until these required gates have evidence.


## MPP charge and submission components

`mpp.kujo` implements the supported Stripe charge profile from the integrity-pinned mppx 0.8.15 sources recorded in deployment/mpp-source.lock.json. It accepts one ASCII quoted-parameter Payment challenge, requires a UTC millisecond expiry, rejects duplicate/unknown headers and noncanonical JSON, and checks exact amount, currency, realm, network, payment-method types, recipient and request-body digest against installed expectations. Request objects use ASCII keys and string leaves; unsupported provider shapes fail closed without changing Kujo's core semantics. Opaque data remains unchanged. The complete challenge digest, including its ID and expiry, is immutable after preparation: even challenge rotation with unchanged amount requires a new authorized preparation, not silent renewal.

Credential encoding retains the validated request/opaque wire strings. The installed expectations explicitly bind externalId: null forbids an externalId, and a string requires an exact match. The credential then echoes the validated value, as required by the reviewed Stripe server verifier. No SDK code is executed by the adapter. Python fixtures independently encode the accepted wire structure; this is not yet a live mppx interoperability attestation.

`submission.kujo` records immutable preparations and permanent one-shot dispatches in the privileged provider database. Before retrieving an SPT it probes the installed merchant request without credentials and revalidates the exact challenge. It retrieves the SPT only through the private expanded Link response, then constructs the Payment credential in memory and calls the installed pay callback once. Exceptions or lost responses become unknown; repeated calls observe without another payment call. The generic executor now caps the provider deadline at both approval and snapshot expiration, and the submission path rechecks it before sending. Memory zeroization is not promised; use short-lived privileged processes and enforce the deployment boundary.

The injected merchant port has probe(context), pay(credential_header, context) and observe(reference, snapshot, context). These are trusted installed callbacks, not model-supplied endpoints. The pay response body is ignored. Observation requires exact binding and amount, removes unknown/private fields, and hashes native evidence references into opaque local references. The core still requires its separately installed authoritative confirmation rule. A 2xx or a Payment-Receipt header by itself does not mint a Kujo financial receipt. The native route factory implements HTTP delivery; real account/merchant observation remains required.

Tests cover 58 independent codec vectors, re-probe mutation rejection, missing/malformed credentials, a lost response after a fake charge, no second send, unverified HTTP success and extra-secret-field suppression. All financial effects are synthetic.

## Installed provider and merchant transport

`provider.kujo` composes describe, prepare, request_authorization, submit and observe. Immutable preparations bind the principal, tenant, execution, installation, merchant route, capabilities and exact challenge. Cached preparation cannot switch accounts, payment methods or routes. The factory consumes trusted installed callbacks; it does not expose credentials or native identifiers through the generic SPI.

`merchant_http.kujo` binds the exact URL, method, body and route identity. Uncredentialed probing and credentialed submission use bounded native HTTP, DNS pinning, private-address denial and no redirects. It accepts exactly one authentication challenge header and suppresses response bodies. Plain HTTP is available only for explicitly selected loopback fixtures. Independent HTTP tests check UTF-8 body digests, duplicate headers, redirects, deadlines, response bounds and credential placement.

A five-method integration fixture exercises the real worker, Ability operator approval, core SQLite claims and a separate fake merchant ledger. Success, post-charge response loss, changed challenges and unverified HTTP success remain distinct. These are synthetic effects, not a Link sandbox attestation.

## Settlement evidence release gate

The observer is still a trusted host port. A merchant callback or HTTP success alone is insufficient: the host confirmation rule must validate authoritative evidence for the registered merchant, order, amount, currency and provider account. The reviewed Link transaction list does not establish this complete correlation, and `/userinfo` does not document a stable account subject. Do not infer payer identity from an alias or match settlements by amount and time.

An SPT network ID is not proof of the settlement destination. The reviewed `merchant_account_id` flow applies to LPT; it must not be assumed to bind SPT settlement. The MPP challenge and TLS delivery bind the installed request but do not independently attest the merchant's acquiring account. Keep real execution unavailable until a supported account/merchant evidence integration passes sandbox conformance. No speculative endpoint or fuzzy lookup substitutes for that gate.
