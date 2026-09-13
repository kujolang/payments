# Incident execution control

The private administrator entrypoint controls new execution claims for the entire database. It is separate from payer-scoped approval authority and from agent tools. Filesystem access to the control configuration and database is its authentication boundary; deploy it under the database administrator's OS identity, outside the requesting runtime.

Store this configuration privately with mode 0600 in an administrator-owned directory:

```json
{"schema":"kujo.payment-control/v1","database":"/private/payments.db","actor_ref":"incident-admin"}
```

Set `KUJO_BIN` to an absolute runtime path and `PAYMENTS_CONTROL_CONFIG` to that file. Run `PAYMENTS_CONTROL_ACTION=inspect bash scripts/control.sh` to retrieve the current mode and revision. Pause with `PAYMENTS_CONTROL_ACTION=pause PAYMENTS_CONTROL_REVISION=0 bash scripts/control.sh`, substituting the inspected revision. Resume with action `resume` and the newly inspected revision. A stale revision fails instead of undoing another administrator's decision. Configuration paths, arbitrary notes and raw errors are not returned.

## Guarantees and limits

A committed pause blocks new SQLite financial claims and new native authorization reservations. The control check, one-use approval consumption and execution claim share a write transaction. Database triggers also reject direct claim/native-reservation bypasses. Pause and resume append an immutable actor/revision/time event atomically; an event-write failure rolls back the mode change. Pausing does not consume approvals or clear claims. A preflight check avoids starting an Ability invocation when the store is already paused. All conforming stores must implement `execution_enabled()` and enforce incident control atomically in `claim`, regardless of that advisory preflight check.

Pause leaves intake, status, existing authorization observation and financial reconciliation available. It does not revoke a claim won before the pause, stop an in-flight process or reverse a provider operation. For an incident requiring immediate cessation, also quiesce privileged workers and revoke outbound/provider authority as appropriate; retain all journals and reconcile uncertain effects. An administrator with direct database/host control can bypass these controls and is outside the requesting-agent threat model.

Resume enables future claims; it is not a retry command. If pause races an Ability invocation after its idempotency reservation but before approval consumption, the invocation may retain a rejected Ability receipt while the payment remains unclaimed. Resume never erases that receipt or invents another invocation/approval. Such interrupted invocations require a separately reviewed recovery procedure; automatic reopening is not implemented. Already-claimed payments remain observation-only under every mode.

## Restore restriction

This switch is not rollback detection or a backup-restore implementation. A copied old database can lack financial claims that exist at the provider. Do not open a restored database for execution. Supported restore must enter observation-only operation before any worker can claim, preserve replay tombstones and reconcile against authoritative provider state. An observation-only snapshot tool now enforces a permanent restore quarantine; see [recovery snapshots](recovery-snapshots.md). Complete disaster recovery, live-history merge and migration remain release gates.

## Verification

`tests/network/control_test.py` runs real Kujo processes against one database: persistent pause, four blocked claimants, stale/invalid resume rejection, one successful claim after resume, paused crash recovery, immutable control/audit records and transactional event-write failure. `tests/network/worker_test.py` additionally verifies a paused ready payment creates no Ability idempotency record and can execute after a normal resume. Financial effects are synthetic. These checks do not claim immediate interruption of requests already in flight or completed restore safety.
