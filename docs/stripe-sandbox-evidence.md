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

## Private merchant launcher

`scripts/sandbox-merchant.sh` now provides `check`, `serve` and `recover` commands. This closes the standalone merchant/operator entrypoint gap; it does not yet provide the buyer's Link login or a complete installed Payments workflow.

Create a directory accessible only to the merchant operator (mode 0700). Put these two regular files inside it, owned by that operator and mode 0600:

- `stripe-test-key`: the merchant sandbox's server-side test key, entered locally. Never paste it into chat or pass it on the command line.
- `merchant.json`: the reviewed installation object below, including the exact snapshot and challenge from the trusted purchase preparation.

The launcher rejects symlinked directory/files, group/other access, unexpected ownership and oversized files. It uses umask 077 for journal creation and checks existing SQLite sidecars. These checks are not protection from another process running as the same OS user or a privileged administrator. Use a separate principal/container and inaccessible mounts for an untrusted agent. Keep this directory out of the requesting runtime, repository artifacts, backups accessible to agents and telemetry.

The configuration has exactly eight fields:

| Field | Required value |
| --- | --- |
| `schema` | `kujo.stripe-sandbox-merchant/v1` |
| `account_id` | Expected merchant `acct_…` |
| `api_version` | Explicit Stripe API version selected for the sandbox |
| `port` | Local listener port, 1024–65535 |
| `snapshot` | Trusted prepared snapshot conforming to `contracts/snapshot.schema.json` |
| `challenge` | Matching unexpired MPP challenge string |
| `expected` | Installed MPP constraints described by `validate_mpp_challenge` |
| `body` | Exact POST body string, at most 8192 bytes |

The journal is fixed at `merchant.db` inside this directory. Config cannot select another database/key path or bind address. The handler listens only on `127.0.0.1` at `/purchase`. The operator must bind the intended merchant route to this service; deployment routing, TLS and agent/executor network separation remain deployment requirements.

```bash
export KUJO_BIN=/absolute/path/to/reviewed/kujo
export PAYMENTS_SANDBOX_DIR=/absolute/path/to/private/merchant
bash scripts/sandbox-merchant.sh check
bash scripts/sandbox-merchant.sh serve
```

`check` validates configuration, test-key shape, exact money/body/challenge binding and expiration offline without creating a journal or contacting Stripe. It does not attest to API permissions, Link connection, account identity, runtime header multiplicity or payment success. `serve` starts the route; the handler still refuses credentialed execution on released Kujo v1.4.0 as documented above. Use a supervising process with bounded lifetime and shutdown appropriate to the installation.

For recovery, an authenticated local operator supplies only a candidate non-secret transaction ID; the snapshot remains in trusted configuration:

```bash
PAYMENTS_SANDBOX_PAYMENT_INTENT=pi_candidate bash scripts/sandbox-merchant.sh recover
```

Recovery may read Stripe but cannot create a charge. It requires the matching existing claim and authenticated evidence; a candidate ID alone is insufficient. It can run after snapshot expiration. Local authorization is the private OS environment, not a new remote authentication scheme. Run buyer reconciliation separately after recovery records the ID.

`tests/network/sandbox_operator_test.py` runs the actual launcher using a fake key: offline validation, permission/symlink/live-key refusals, missing-claim recovery and uncredentialed HTTP 402 startup. No credentialed Stripe request is made. The separate source-runtime endpoint test proves credential parsing with a synthetic callback; it does not substitute for real sandbox acceptance.

## Build matching buyer and merchant configuration

Use `scripts/sandbox-configure.sh` to publish both configurations into a new private directory without manually copying snapshot digests. Its input is a reviewed private plan file, not model-supplied checkout content:

```bash
export KUJO_BIN=/absolute/path/to/reviewed/kujo
export PAYMENTS_SANDBOX_PLAN=/absolute/path/to/reviewed-plan.json
export PAYMENTS_SANDBOX_DIR=/absolute/path/to/new-private-directory
bash scripts/sandbox-configure.sh
```

The plan contains exactly `installed`, `intent`, `execution_id`, `currency_table`, `region`, `challenge`, `route`, `local_fixture`, and `merchant`. `installed` is the existing Link provider installation (`snapshot`, `capabilities`, `expected`, `payment_method`, `test_mode`); test mode must be true. `merchant` contains account ID, API version and local port. `route` is the existing immutable merchant HTTP route. The intent, capabilities, currency table, region and resulting snapshot must pass the existing domain validation. The actual merchant URL, body digest and route identities must match the installation.

The provider and setup command now share `assemble_link_snapshot`, so capability digest, intent digest, execution/principal binding, challenge terms and expiration clamps cannot drift through duplicated setup logic. The live provider still probes and validates the merchant independently; offline configuration does not bypass that check or prepopulate its journal. `tests/sandbox_config.kujo` compares generated merchant terms with the actual provider factory's preparation and checks rejected test-mode, money, body, origin and expiration changes.

Successful setup atomically publishes mode-private `merchant.json` and `buyer.json` without replacing an existing directory. It creates no keys, approval, credential store, provider session, financial claim or payment. Place the merchant's test key locally in `stripe-test-key` afterward as described above. Treat these files as sensitive operator configuration; they contain purchase/principal and private payment-profile references, not agent-facing outputs.

`buyer.json` records the intended Link installation, route and expected snapshot digest. A complete authenticated buyer runner is still required. Generating the file does not establish Link access or prove the deployed merchant route is reachable. Local fixture mode only permits explicit loopback HTTP; it is not a deployment isolation guarantee. A real HTTPS route needs operator-controlled routing to the loopback service.

## Buyer connection and lifecycle runner

`sandbox_link_connection` in `sandbox_connection.kujo` composes the existing accepted-enrollment guard with `link_credential_api`. It does not copy a CLI session, register a client, accept raw tokens from model input or supply provider-account attestation. The installation must already have completed supported, verified enrollment into its private vault.

For this sandbox installation, the enrollment binding's `tenant_id` must equal the intent tenant, `payer_ref` must equal `principal_digest(intent.principal)`, and `account_ref` must equal the installed Link account reference. The principal digest includes principal type and tenant; matching a display name or bare user ID is insufficient. The guard checks accepted enrollment, active vault state and expiry beyond the operation deadline before each request, then retains the enrollment and native credential guards. Pending acceptance, disablement and expiry fail closed. This checks the local binding; it does not prove how the host originally verified the provider account.

`sandbox_buyer_runtime` in `src/executor/sandbox_buyer_runtime.kujo` supplies private `request`, `status`, `step`, `review` and `approve` callbacks. It accepts the generated buyer config, core store, private provider database, guarded connection, merchant port, authoritative confirmation, schemas and trusted host callbacks. It uses the existing core intake, worker, Ability approval and operator authority. No workflow engine or provider-shaped public tools were added.

Before unclaimed execution advances, `step` requires a ready connection. This avoids permanently reserving a Link authorization request when enrollment is not usable. Each prepared snapshot must match the generated expected digest. `approve` requires the existing reviewed Ability binding digest and the installed operator authority. The callbacks are private operator/programmatic controls, not an agent-visible projection or a complete CLI launcher.

A claimed payment can still reconcile with the merchant when Link credentials expire or are disabled. It must not need an active wallet merely to determine whether an earlier payment succeeded. No automatic polling, refresh or financial retry occurs. An operator/Dispatch host invokes one bounded step at a time.

`tests/sandbox_connection.kujo` exercises real enrollment/vault helper composition using synthetic device responses, cross-scope rejection, pending/accepting guards, expiry and disablement. `tests/sandbox_buyer.kujo` exercises real core/Ability/Link runner composition with synthetic ports: idempotent intake, no provider request before connection readiness, configuration-drift rejection, explicit correct-digest approval, lost-response reconciliation after wallet disablement and exactly one charge. Normal CI makes no Link or Stripe request. The top-level authenticated buyer launcher and real enrollment acceptance remain unfinished.
