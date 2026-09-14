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

Return null when no binding is available. Never populate this lookup from model arguments, a checkout response body, an amount/time search, or an unverified webhook. The merchant must persist the intended binding crash-safely, and create the PaymentIntent with `metadata.kujo_snapshot_digest` and `metadata.kujo_execution_id`. One PaymentIntent must not be assigned to multiple purchases. The private `sandbox_merchant.kujo` component now implements this journal and its lookup. The merchant HTTP endpoint and production Stripe creation transport still need integration; the journal does not claim those exist.

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

If the process dies after Stripe accepts creation but before the identifier is durably saved, the claim remains without a lookup result. This remains unresolved and requires an authenticated operator recovery process; never infer failure or automatically create another PaymentIntent. Such recovery and an end-to-end merchant HTTP service remain unfinished. The module also refuses to execute inside a caller-owned transaction so a later rollback cannot erase its reservation after a provider call.

`tests/sandbox_merchant.kujo` covers successful recording, lost/malformed provider responses, binding mismatches, receipt-write failure, immutable identifiers, unique transaction ownership, caller-transaction refusal and restart. `tests/network/sandbox_merchant_test.py` runs four independent Kujo processes against a fake API ledger with no deduplication: both successful and lost-response cases produce one call. These are synthetic process tests, not Stripe account conformance or protection against an operator deleting the database.
