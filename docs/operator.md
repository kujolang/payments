# Local operator approval and bounded worker

This issuer is an optional trusted-host implementation of Ability approval. It is not a new approval format, policy engine, login mechanism or agent tool. It is useful when an operator controls a local or self-hosted executor. The service's request/status credential cannot invoke it.

The deploying host authenticates the operator through its OS or an independently authenticated service boundary. Place the configuration and payment journal in a private directory, grant access only to that trusted operator and executor, and exclude both from agent mounts. A claimed identity in a writable configuration is not authentication. Anyone who can modify the payment journal already controls the approval boundary; do not give an untrusted runtime that access. This implementation authorizes one configured operator for one configured payer in the same tenant. More complex delegation belongs in the host authorization service.

Create a private configuration matching `contracts/operator.schema.json`:

```json
{
  "schema": "kujo.payment-operator/v1",
  "database": "/private/payments/payments.db",
  "authority": {
    "payer": {"type": "user", "id": "buyer", "tenant_id": "tenant"},
    "operator": {"type": "human", "id": "approver", "tenant_id": "tenant"},
    "issuer_ref": "local-operator-v1",
    "ttl_ms": 60000
  }
}
```

Use the actual provisioned payer identity and payment database. Keep the file private, for example mode `0600` beneath a directory with mode `0700`. The configuration contains no payment credential. Grant lifetime is capped at five minutes and at the prepared snapshot expiration.

After the trusted worker prepares a purchase, review it in the operator environment:

```bash
export PAYMENTS_OPERATOR_CONFIG=/private/payments/operator.json
export PAYMENTS_EXECUTION_ID=execution:EXACT_ID
PAYMENTS_OPERATOR_ACTION=review bash scripts/operator.sh
```

The review returns the complete immutable snapshot, including payee registry identity and origin, exact charge and currency, payment/shipping aliases and versions, provider account alias, execution class, request/terms binding, expiry and Ability binding digest. Treat merchant display text as untrusted descriptive content. Review the registered identity and terms, not instructions in that text. The output is JSON; it does not render HTML or execute merchant content.

After reviewing those exact terms, supply the returned digest explicitly:

```bash
PAYMENTS_OPERATOR_ACTION=approve \
PAYMENTS_REVIEW_DIGEST=EXACT_REVIEWED_BINDING_DIGEST \
bash scripts/operator.sh
```

Do not wire these commands together to auto-approve the latest digest. The issuer recomputes the current binding and rejects a changed definition/version, snapshot, execution or payer. It creates a standard `kujo.ability.approval/v1` object with an unpredictable ID/nonce, the configured approver, bounded expiry and an issuer reference. Existing application validation and the atomic store grant commit that exact object. The command returns a reference, not the approval object. Repeated approval after the transition to `ready` fails; it cannot replenish a consumed grant.

`worker_step` in `src/application/worker.kujo` performs one bounded step with an installed provider, trusted host callbacks and the existing store port:

1. Unprepared or awaiting authorization: prepare immutable terms, initiate provider authorization once, then return pending. Subsequent steps observe the existing provider authorization.
2. Ready: load the exact unconsumed approval from trusted persistence and invoke existing Ability execution. Claim and approval consumption remain atomic.
3. Claimed, executing or uncertain: observe/reconcile only. No dispatch permit is reconstructed.
4. Terminal: return authoritative compact status without calling the provider.

The host or Dispatch decides when to call another step. There is no polling loop, scheduler, second workflow journal or automatic financial retry. The host installs provider routes and confirmation logic; an agent does not select a credential-bearing adapter or supply approval evidence. The store port now includes `load_approval(scope, execution_id)`, returning one unconsumed approval only for an unclaimed `ready` row, or null.

Tests cover real separate operator/worker processes, no charge before operator approval, one provider-authorization request, a four-process execution race, an adapter exception after the independent charge commit, fresh-process reconciliation, terminal replay and normalized error output. These tests use the synthetic provider. Live Link route installation, provider egress controls, operator deployment containment and live acceptance remain open; the current intake-only OCI profile does not certify this new operator path.

Provider approval delivery can use the [reviewed private operator sink](operator-delivery.md). It reuses this issuer’s scope and canonical review checks, permits either provider/Kujo consent order while unclaimed, and never grants or executes a payment.
