# Dispatch payment wait/resume composition

This optional trusted-host example uses Dispatch's existing workflow, plugin, persistence, lock and approval-checkpoint APIs. It requests a payment through the public Payments HTTP client, persists only the returned execution ID, and exits while Dispatch is paused. A separately scheduled wakeup loads the run and reads authoritative payment status. Pending, ready, executing and reconciliation-required payments keep the checkpoint paused. Failed status reads leave persisted workflow state unchanged. Succeeded or closed payments release the workflow checkpoint, then a status tool reads the final compact outcome.

The Dispatch checkpoint is **workflow continuation**, not financial authorization. Its internal `auto_approve` flag is set only from a fresh terminal status read. It never produces a Payment/Ability authorization or reaches a payment execution API. Dispatch's generic approval trace text describes that checkpoint; it is not proof of the user's financial consent. `closed` finishes the observer workflow but does not mean a purchase succeeded. Consult the payment status/receipt for the financial outcome.

## Run and wake up

Install the example's committed Kennel lock, or run `scripts/ci/bootstrap.py` from the Payments root with `KUJO_BIN` configured. Set these trusted-host values:

- `KUJO_BIN`: absolute runtime executable.
- `PAYMENTS_CLIENT_ENDPOINT` and `PAYMENTS_CLIENT_TOKEN`: request/status client configuration.
- `PAYMENTS_DISPATCH_OUTPUT`: absolute private directory for durable workflow artifacts.
- `PAYMENTS_PURCHASE_JSON`: canonical request input with a stable business `purchase_ref`.

Run `python3 examples/dispatch/run.py`. Retain the returned `run_id`. To wake up the same workflow, set `PAYMENTS_DISPATCH_RUN_ID` to that ID and run the same command again. The resume path ignores purchase input and never calls intake. The host should schedule bounded wakeups or react to authenticated notifications; notification content is not trusted as payment evidence. No polling loop lives in Payments or this example.

The initial request key derives from the example namespace and purchase reference. If the host crashes after intake but before saving the workflow ID, repeating the original request uses that same key. This can create another observer workflow but must not create another payment. The Payments gateway owns financial idempotency. Dispatch's cached steps never authorize financial retries.

`run.py` stages only public Payments client sources and pinned Dispatch dependencies in a temporary module tree. Durable state lives at the explicitly supplied output directory, outside that temporary tree. The subprocess uses an environment allowlist and a 30-second supervisor timeout. Native client calls have their own five-second bound; no in-process custom tool is falsely marked as Dispatch-reviewed deadline-isolated. No model bridge is used. Normal HTTPS remains required; `PAYMENTS_LOCAL_FIXTURE=true` permits the client's explicit loopback test profile only.

## Trust and dependency scope

Run this in the trusted harness, outside the requesting agent runtime. Protect its state directory and client token with deployment permissions. The example does not attest filesystem integrity or create a new OS isolation boundary. It receives no provider credentials or financial approvals. Existing private Payments worker/operator processes independently perform authorization, execution and reconciliation.

Dispatch source is pinned at `9eb16c72316744d8a691d9ef5ec5be4f12018408`. The sole upstream change from the reviewed source was changing AI SDK's unchanged SHA from `ref` to `commit` in its Kennel manifest. The former declaration failed clean installation because Kennel resolves a named ref differently from a commit. No Dispatch runtime changes were required; core Payments has no Dispatch dependency. The example's transitive AI SDK is pinned but is not invoked for model execution.

`tests/network/dispatch_test.py` runs the actual pinned Dispatch VM and public native HTTP client in separate processes against a synthetic service. It verifies durable pause/resume, pending and failed wakeups, terminal completion, absence of intake replay, and suppression of token, unrelated provider sentinel and purchase details across generated artifacts. This complements the actual Payments HTTP tests; it is not a live provider test or a complete cross-integration leak suite.

## Incomplete intake observation

When the original intake returns a validated 409 error observation with an execution ID, the example can create an observer workflow for that existing payment. It still fetches fresh status before deciding whether to pause or resume. Even a stale terminal status in the error response cannot release the checkpoint. This is successful observer setup, not a successful payment-request receipt. No additional intake call, financial approval or provider operation occurs. Generic, unauthorized, malformed and server-error responses remain failures.

The recovery projection test runs the actual pinned Dispatch process and verifies compact persisted state, fresh pending status and one intake request. Broader interrupted invocation repair stays with the Payments/application journal; Dispatch does not repair it.
