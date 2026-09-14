# Stripe sandbox confirmation for the Link adapter

Status: implemented private read-only component; tested with synthetic Stripe responses. No provider-backed purchase has been verified by this component yet.

`src/providers/link/stripe_sandbox.kujo` supplies merchant observation and the existing core confirmation port. It introduces no public Ability, provider SPI method, dependency, or agent tool. It can verify a direct merchant charge in a Stripe sandbox. It does not establish Link payer identity, prove that Link supplied the funding credential, create a payment, or establish final bank settlement.

## Installation

Only the privileged executor may construct these ports. Supply a server-side test key, the expected merchant Stripe account ID, an explicitly selected Stripe API version, and a trusted clock to `stripe_sandbox_api`. Live and publishable keys are rejected. The production transport permits only GET of `/v1/account` and a single exact `/v1/payment_intents/pi_…` identifier at `https://api.stripe.com`. It disables redirects, pins DNS, denies private destinations, caps each response at 64 KiB and each request at one second. It has no retry or write operation.

Construct `stripe_sandbox_evidence(account_id, lookup, api, clock_ms)`. Install its `observe` callback in `merchant_http`, and its `confirmation` object in the worker installation. Observation needs more than two seconds of remaining execution time; an exhausted budget returns unknown. Independent confirmation performs another bounded read, allowing 2.5 seconds for its two requests. Short submission budgets may therefore require a later reconciliation step.

The trusted `lookup(execution_id, snapshot_digest)` must read an immutable merchant-owned journal and return:

```json
{
  "snapshot_digest": "<exact approved snapshot digest>",
  "stripe_account_id": "acct_…",
  "payment_intent_id": "pi_…"
}
```

Return null when no binding is available. Never populate this lookup from model arguments, a checkout response body, an amount/time search, or an unverified webhook. The merchant must persist the intended binding crash-safely, and create the PaymentIntent with `metadata.kujo_snapshot_digest` and `metadata.kujo_execution_id`. One PaymentIntent must not be assigned to multiple purchases. The private `sandbox_merchant.kujo` component now implements this journal and its lookup. The merchant HTTP endpoint still needs integration. The bounded test-only creation transport described below is implemented; provider-backed acceptance remains outstanding.

## Acceptance rule

Both authenticated account identity and the exact PaymentIntent ID must match the installation. A successful observation additionally requires:

- `livemode` is the boolean false and status is `succeeded`;
- integer amount and amount received both equal the approved exact charge;
- currency matches and the integer capturable balance is zero;
- metadata matches the execution and snapshot digest;
- a charge ID exists, with no `on_behalf_of` or `transfer_data` routing.

Any missing, malformed, pending, partial, mismatched or inaccessible record remains unknown. An absent record is not proof that no effect occurred and never authorizes resubmission. Connect routing is deliberately outside this sandbox installation; this is not a restriction on generic Payments semantics.

Native account and PaymentIntent bodies stay private. Only the existing observation fields and a hashed evidence reference leave the component. Link's submission port applies its existing additional evidence hash. The confirmation callback re-reads Stripe and checks this exact reference and binding before core can accept success. An arbitrary `succeeded` observation cannot substitute for that read.

## Evidence and remaining acceptance

`tests/stripe_sandbox.kujo` exercises successful observation through the real Link sanitization port and independent confirmation, plus account/ID/mode/status/amount/currency/routing/metadata mismatches, missing records, provider exceptions, private-field suppression, deadline refusal and transport route/key restrictions. Normal CI performs no network calls to Stripe and moves no money. These fixtures do not verify the deployed transport or account permissions.

Official contracts reviewed September 14, 2026:

- [Retrieve a PaymentIntent](https://docs.stripe.com/api/payment_intents/retrieve)
- [PaymentIntent fields](https://docs.stripe.com/api/payment_intents/object)
- [Shared Payment Tokens](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens)

Before declaring the Link sandbox example usable, implement the merchant journal and endpoint, wire supported Link authentication, exercise test-only SPT issuance and purchase, then verify recovery against the selected Stripe sandbox. A standard sandbox account alone does not prove access to every preview API. Keep account-specific failures explicit rather than substituting a fixture success.

## Durable sandbox merchant journal

`open_sandbox_merchant(db)` initializes a separate private SQLite database with a strictly checked versioned schema. `sandbox_merchant(db, account_id, create_payment_intent, clock_ms)` provides `submit(snapshot, spt, deadline_ms)` and the exact `lookup` callback above. These are privileged internal methods, not agent tools. Wire `lookup` into `stripe_sandbox_evidence`.

Submission commits a permanent claim before calling the installed Stripe creation port. It supplies exact amount/currency, the SPT, `confirm=true`, and the execution/snapshot metadata. The callback must be an account-bound, test-key-only Stripe transport; the journal is not an authorization boundary and must only receive the already validated, authorized snapshot and credential from the private executor. No raw SPT or provider response is persisted. The optional native idempotency key is stable, but the journal never resends a claimed creation request, regardless of Stripe's retention window.

A validated test PaymentIntent ID can be attached once. It cannot be replaced, removed or reused for another purchase. `recorded=true` only means this identifier was saved; the separate read-only evidence component decides whether payment succeeded. Concurrent callers and process restarts cannot obtain another creation claim. Initialization rejects a missing or modified trigger rather than silently repairing the database.

If the process dies after Stripe accepts creation but before the identifier is durably saved, the claim remains without a lookup result. The private recovery function below can verify an operator-supplied candidate ID and attach it to the existing claim. Until that verification succeeds, the purchase remains unresolved; never infer failure or automatically create another PaymentIntent. An authenticated operator command and end-to-end merchant HTTP service remain unfinished. The module also refuses to execute inside a caller-owned transaction so a later rollback cannot erase its reservation after a provider call.

`tests/sandbox_merchant.kujo` covers successful recording, lost/malformed provider responses, binding mismatches, receipt-write failure, immutable identifiers, unique transaction ownership, caller-transaction refusal and restart. `tests/network/sandbox_merchant_test.py` runs four independent Kujo processes against a fake API ledger with no deduplication: both successful and lost-response cases produce one call. These are synthetic process tests, not Stripe account conformance or protection against an operator deleting the database.

## Test-only creation transport

`stripe_sandbox_create(secret_key, account_id, api_version, clock_ms)` in `sandbox_create.kujo` is the concrete `create_payment_intent` callback for the merchant journal. It reuses the read transport's test-key, account and API-version validation. Before its single POST, it retrieves `/v1/account` with the same key and checks the installed merchant account. The only write destination is `https://api.stripe.com/v1/payment_intents`; redirects, retries and alternate routing fields are absent. Each request has a one-second timeout, pinned DNS, private-address denial and a 64 KiB response cap. Two seconds of remaining budget are required before account preflight.

The current [Stripe seller SPT documentation](https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens?agent-seller=seller), read September 14, 2026, specifies `payment_method_data[shared_payment_granted_token]`. The transport encodes that nested field, exact integer amount/currency, `confirm=true` and the two binding metadata fields. The journal callback shape was updated to match. Unknown fields, live/publishable keys, malformed IDs, and form-injection characters are rejected. The amount ceiling in this adapter is a Stripe request constraint, not a generic Kujo money limit.

Connect the components inside the privileged merchant installation:

```kujo
create := stripe_sandbox_create(test_key, account_id, api_version, clock)
merchant := sandbox_merchant(private_db, account_id, create, clock)
read := stripe_sandbox_api(test_key, account_id, api_version, clock)
evidence := stripe_sandbox_evidence(account_id, merchant["lookup"], read, clock)
```

Call `open_sandbox_merchant(private_db)` first. Supply the `test_key` through the private installation, never a model-facing argument or command line. This snippet is component wiring, not a runnable merchant server or completed Link login flow.

`tests/sandbox_create.kujo` verifies the form contract and fail-closed preflight, and composes the real journal, creation port, Link sanitization and confirmation callbacks against a synthetic processor. Production transport HTTP/TLS behavior and actual sandbox permissions still need account-backed acceptance; these tests make no such claim. A failed or ambiguous creation remains permanently claimed by the journal, including account/preflight failures. Fix configuration and inspect the claim rather than retrying the same execution.

## Recovery after a lost creation response

`recover_sandbox_purchase(db, account_id, snapshot, payment_intent_id, read, clock_ms, deadline_ms)` is a private operator function in `sandbox_merchant.kujo`. Use the fixed-origin `stripe_sandbox_api` read callback. It is not exposed through a public Ability or HTTP endpoint. The host must authenticate the operator and load the original snapshot from trusted storage; the operator's candidate PaymentIntent ID is only a lookup hint.

Recovery requires an existing committed claim for that exact execution, snapshot and merchant account. It uses the same authenticated evidence rule as normal confirmation: succeeded test PaymentIntent, exact amount received/currency/metadata, direct charge routing and charge ID. Pending or mismatched records cannot be attached. A completed payment may be recovered after the original purchase authorization expires because recovery sends no financial action.

Only after verification does a short SQLite transaction attach the ID. The unique/immutable journal constraints remain in force. Repeating verified recovery for the same ID is idempotent; substitution cannot overwrite it. Neither missing claims nor read errors create rows, remove claims or enable retries. A failed local recovery write leaves the original claim intact and can be retried as read-only recovery. Buyer lifecycle reconciliation still needs to run afterward; recording the ID does not directly mark the buyer execution successful.

`tests/network/sandbox_recovery_test.py` kills an actual Kujo worker after a non-deduplicating synthetic processor commits its charge but before the merchant saves its receipt. Fresh processes then reject account/amount/mode/metadata/ID mismatches and missing claims, recover the original ID after authorization expiry, repeat recovery and reject replacement. The processor retains exactly one charge throughout. The test also checks that rejected candidates leave the journal untouched. This proves the tested local crash path, not a live Stripe recovery or deployed operator-authentication guarantee.

## Installed MPP HTTP handler and runtime requirement

`sandbox_purchase_handler` in `sandbox_endpoint.kujo` is a native Kujo HTTP route callback for one installed purchase. It freezes the trusted snapshot and expected MPP constraints, validates the challenge against the snapshot's terms digest, and binds the exact POST body. Register it on the configured purchase path with `server.route`. The host must restrict that route and supply the authorized snapshot; HTTP callers cannot select a new snapshot or amount. This is a handler component, not the complete provisioned server/login example.

An uncredentialed matching request receives HTTP 402 and the fixed challenge. A credentialed request must roundtrip through the same canonical MPP credential encoding, including its exact challenge and optional external ID. Private SPT decoding is confined to the handler/executor. Invalid bodies, methods, credentials or duplicate headers cannot reach the merchant submit callback. HTTP 202 means the merchant recorded a transaction identifier; it does not assert success. Uncertain or repeated submissions require reconciliation.

The actual HTTP test exposed a runtime boundary gap: Kujo v1.4.0 collapses duplicate same-case request headers in its `headers` dictionary. A source change in `kujolang/kujo` adds lowercase `header_values` arrays in both runtimes without changing the compatibility dictionary. This is unreleased. This new sandbox handler requires that field for credentialed requests and returns HTTP 503 `runtime_header_values_required` on the released binary. Do not advertise this endpoint as installable with v1.4.0 alone. No runtime release or installer update has been performed here.

`tests/network/sandbox_endpoint_test.py` verifies the released-runtime refusal by default. Set `PAYMENTS_HEADER_VALUES_RUNTIME=1` with a built supporting runtime to require the positive HTTP path and duplicate-header rejection. The test uses a synthetic merchant callback and never contacts Stripe. The host still owns bounded ingress, TLS/route deployment, authentication, no-header/body logging and process isolation. There is no implication that all other Kujo HTTP handlers automatically reject duplicates.
