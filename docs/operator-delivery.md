# Reviewed private operator delivery

`src/executor/operator_delivery.kujo` composes the existing operator review, payer scope and incident-pause checks with a trusted private renderer. It introduces no login service, approval object, policy engine, scheduler or agent tool. The complete delivery payload stays inside the privileged executor/operator boundary.

The host installs one authority configuration, execution ID, canonical Ability definition, explicitly reviewed binding digest, clock and renderer. Authority configuration is trusted only because the host authenticates the operator and controls access to that configuration. A caller-supplied operator name or tenant is not authentication. Use the same administrator/OS boundary described in [operator approval](operator.md).

## Composition

1. Prepare the payment and obtain a fresh operator review using `review_payment_delivery(store, payer, execution_id, definition, now_ms)` from `src/executor/approval.kujo`.
2. Present those exact terms in the private operator channel. Retain the explicitly reviewed `binding_digest`; do not automatically substitute a later review digest.
3. Construct `reviewed_operator_sink(store, authority, execution_id, definition, reviewed_digest, render, clock_ms)`.
4. Supply that sink to the provider's private delivery component. For Link, `deliver_link_approval` passes its previously validated private URL payload to this sink after the native fetch/outbox lookup.

The sink re-reads the actual payment journal at handoff. It requires the configured payer and tenant, exact canonical definition/Ability binding, matching execution/snapshot/expiry, an unclaimed payment and active incident control. It caps the renderer deadline at snapshot expiry, accepts only literal `true`, and checks state, binding, pause and clock again afterward. Unexpected return values and exceptions become `false`; private payloads and raw error details never become tool results.

Provider consent may occur before or after the Kujo grant. The delivery-only review therefore accepts both `awaiting_authorization` and unclaimed `ready`. The original financial review/grant path still accepts only `awaiting_authorization`: delivery cannot mint, replace, replenish or consume a grant. Already-claimed, closed and expired payments cannot enter the renderer. Financial execution separately validates provider authorization before taking its permanent claim; delivery success is not financial authorization or settlement evidence.

## Concurrency and deployment limits

Cancellation or pause during the provider fetch is detected before rendering. If it occurs during rendering, the result becomes false afterward, but the callback may already have displayed or transmitted the URL. No database transaction spans a remote renderer, and there is no atomic delivery/retraction guarantee. There is also a possible race after the final pre-render state check. Treat a false/unknown renderer result as ambiguous and do not automatically resend.

The host must enforce renderer authentication, deadline/process bounds, private file permissions, dedicated browser/session isolation, redirect policy and retention of operator-side artifacts. The guard does not open a browser, send email, host a web endpoint or log the URL. Never install this executor module, its databases or renderer in an agent Workcell. The Link outbox's [logical retirement](link-approval-maintenance.md) does not erase a renderer's previously retained copy.

## Verification scope

Nineteen native integration cases combine the real core journal, Link authorization/outbox and reviewed renderer. They cover both consent orders; wrong tenant/payer/execution/snapshot/definition/review binding; claimed, expired and paused payments; cancellation/pause during fetch and rendering; renderer exceptions and unexpected objects. The private output file uses mode 0600 beneath a private test directory. The tests assert that delivery itself neither creates nor consumes a financial grant/claim and that provider/OAuth sentinels never appear outside the allowed private artifacts.

The containment seed now creates a real reviewed private operator artifact alongside its core/outbox/vault controls. The agent probes include this artifact, its private journal paths and the executor module. These are synthetic deployment-profile tests, not production operator authentication or browser certification. Both pinned Linux jobs passed at `15253d1` in [run 34737608492](https://github.com/kujolang/payments/actions/runs/34737608492). Archive/manifest integrity, the reviewed renderer/outbox/vault controls, both 24-file probes and complete cleanup were verified. Source-scoped evidence: `docs/evidence/operator-delivery-ci.json`.
