# Kujo Payments

Kujo Payments lets an agent request a purchase, wait for approval, and check what happened. Payment credentials belong in a separate, trusted executor—not in the agent's context.

For example: **“Pay this merchant up to $55 USD for this purchase.”** The agent works with that request and its status. The executor handles the provider connection and records the outcome.

## We're building this in public

**Developer alpha. Active work. Not ready for real-money use.**

We're building Payments here, in this repository, with code, tests, and documentation committed as the work lands. Expect changes to the API, setup, and documentation. You can follow the [commits](https://github.com/kujolang/payments/commits/main/) and [test runs](https://github.com/kujolang/payments/actions), try the examples, and help shape what comes next.

The local purchase flow works with simulated payments. A Stripe Link adapter is implemented and tested with synthetic provider responses; real Link sandbox validation and deployment acceptance are still ahead. No live provider is enabled by default.

[Watch the narrated demo](docs/videos/payments-alpha-demo/kujo-payments-alpha-narrated.mp4) or read its [transcript](docs/videos/payments-alpha-demo/narration/TRANSCRIPT.md). The demo is simulated and moves no money.

## What it does

- **Accepts a purchase request:** merchant, currency, spending limit, and a named payment profile such as `default`.
- **Binds approval to the action:** the approved terms must match the action being executed.
- **Controls execution:** a stored, single-use claim prevents another worker from blindly submitting the same payment again.
- **Handles uncertain results:** if a request times out after a possible charge, Payments checks the outcome instead of assuming it failed and retrying.
- **Returns a compact status and receipt reference:** agents can track the purchase without receiving provider payment credentials.

The code includes an authenticated request/status service, private operator controls, crash and concurrency tests, and optional agent integrations. Keeping credentials out of reach also requires the right deployment boundaries; a tool response alone cannot provide that isolation.

Link is the first provider adapter. The payment contracts are designed to support other providers without making Link's API the public interface. Payments uses [Ability](https://github.com/kujolang/ability) for operation contracts and approval binding. Workflows and policy evaluation stay with the applications and tools that already own them.

This is the buyer side of a purchase. [Kujo Commerce](https://github.com/kujolang/commerce) serves the seller side. Payments is not a wallet dashboard, merchant checkout service, or general financial-management tool. Recurring payments, transfers, and raw-card browser entry are outside the first release.

## Try a simulated purchase

You need **Kujo 1.4.0**, Git, and Python 3. The example uses no payment account, API key, or real funds.

### 1. Install Kujo

The [Kujo installer](https://kujolang.ai/install.sh) installs Kujo and the core Kujo development tools on supported macOS and Linux systems:

```sh
curl -fsSL https://kujolang.ai/install.sh -o /tmp/kujo-install.sh
KUJO_RELEASE_VERSION=v1.4.0 bash /tmp/kujo-install.sh --core
export PATH="$HOME/.local/bin:$PATH"
kujo --version
```

Already have Kujo 1.4.0? Skip the installer. This project is tested against that version; verify newer runtimes before using them. The installer also brings in other core tools—it is not a Payments installation or a Kujo-only download.

### 2. Get Payments and its pinned dependencies

```sh
git clone https://github.com/kujolang/payments.git
cd payments
export KUJO_BIN="$(command -v kujo)"
python3 scripts/ci/bootstrap.py
```

The bootstrap script downloads and verifies the exact dependency versions recorded in this repository, including those used by the optional integration examples. It needs internet access and can take a few minutes.

### 3. Run the example

```sh
export PAYMENTS_DEMO_DIR="$(mktemp -d)"
"$KUJO_BIN" run examples/local-fixture/main.kujo --interpreter
```

You should see an approval-pending status followed by a successful simulated payment. These are the relevant fields from the two results:

```json
{"status":"awaiting_authorization","next_action":"await_authorization"}
{"status":"succeeded","next_action":"inspect_receipt"}
```

The example simulates both approval and payment confirmation in one trusted process. It does not demonstrate real human approval or credential isolation. Use a fresh temporary directory for each run; the two SQLite files remain there for inspection. See the [example guide](examples/local-fixture/README.md) for details.

## Develop and integrate

After the setup above, install the MCP example's Node dependencies and run the host test suite. You'll also need Node.js and npm; CI uses Node 24.20.0.

```sh
npm ci --prefix examples/mcp --ignore-scripts --no-audit --no-fund
bash scripts/test.sh
```

Normal tests use synthetic data and never move money. Node is used by the development suite and MCP example; it is not a core Payments dependency. Agents SDK, MCP, Dispatch, and Workcell integrations are optional.

For an application importing Payments, start with the [package installation guide](docs/package-installation.md). There is no registry release yet. Executor setup and the development examples require a source checkout.

## What's next

Before real-money use, we need to validate the selected Link account and payment authority, confirm merchant settlement, finish acceptance testing for credential handling and deployment isolation, and verify operational recovery. The [release checklist](docs/release-checklist.md) tracks those gates. Passing simulated tests does not close them.

Useful places to go deeper:

- [Implementation history](docs/implementation-status.md): what has been built and the evidence behind it.
- [Deployment guide](docs/deployment.md): where the service, operator, worker, and credentials belong.
- [Operator guide](docs/operator.md): reviewing approvals and running bounded execution steps.
- [Architecture checks](docs/architecture-enforcement.md): dependency boundaries enforced by tests.
- [Cancellation](docs/cancellation.md): programmatic controls and their limits.

Want to help? [Open an issue](https://github.com/kujolang/payments/issues) with a confusing setup step, a reproducible failure, or a concrete provider use case. Developer feedback and sandbox integration work are useful right now.
