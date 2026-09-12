# Local fixture purchase

From the repository root, with the pinned Ability dependency installed:

```sh
export PAYMENTS_DEMO_DIR="$(mktemp -d)"
"$KUJO_BIN" run examples/local-fixture/main.kujo
```

The example prints a compact pending summary and then a successful synthetic payment summary. Use a new directory each run; journal identities are deliberately retained. The two SQLite files remain available for inspection.

This example runs trusted code in one process. Its fixed clock, synthetic channel, simulated approval issuer and in-process audit callback are fixtures, not authentication or human approval for real funds. It does not demonstrate physical isolation and must not receive provider credentials. The fixture provider cannot move money.
