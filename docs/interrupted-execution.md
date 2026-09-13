# Interrupted financial execution

An unfinished Ability invocation is not permission to retry a financial action. The current implementation supports safe closure of an unclaimed payment and observation of a claimed payment. It does not support reopening the original execution invocation, replacing its approval or transferring a lost dispatch permit to a new worker.

## Operator procedure

Use the authoritative live database, not a recovery copy. If the incident requires blocking other new claims, apply the existing [incident pause](execution-control.md). Pause does not stop a claim already won or revoke provider authority.

1. An authenticated caller with explicit `inspect_revision` permission reads the payment's current status and revision. An operation timeout, old log or missing receipt is insufficient evidence of financial state.
2. For an unclaimed `ready` or `awaiting_authorization` payment that should be abandoned, use the existing [conditional cancellation](cancellation.md) with the inspected revision and a fresh cancellation key. This is an explicit decision to close the purchase, not a retry of execution.
3. Inspect again after any conflict or uncertain cancellation response. A committed cancellation produces `closed` with the private reason `cancelled`. A stale revision or claim that won first must be treated as a conflict.
4. For a claimed payment, use observation-only reconciliation. Neither `executing` nor `reconciliation_required` may return to a spendable state. A claim committed immediately before a process crash can remain ambiguous even when the fixture supervisor knows submission did not occur; production recovery cannot infer that fact from silence.
5. Retain the execution, approval, original Ability invocation, provider authorization and evidence journals. Closing the Kujo execution does not cancel a merchant order, release a provider hold, revoke a token or delete private approval material. Use the installed provider's supported operations for those separate responsibilities when authorized.

Do not delete an Ability idempotency record, fabricate its receipt, clear `claimed`, extend expiry, generate a replacement business reference automatically or reuse the approval for a different action. A same-business-reference intake retains the original closed execution. Any later purchase is a separately reviewed business decision with fresh authorization; this procedure makes no claim that a new reference deduplicates an existing merchant order.

## Why no recovery generation is added

Cancellation and the financial claim contend on the same scoped SQLite row. Cancellation requires `claimed=0` and the reviewed revision, changes the state to `closed` and increments the revision. A late original worker then loses its claim even if it passed earlier policy, provider authorization and approval checks. If the claim wins first, cancellation cannot succeed. No assumption that a timed-out worker is dead is needed.

Adding a new invocation generation would change approval identity and introduce another path to provider submission. That complexity is unnecessary for safe abandonment. Resuming an abandoned purchase remains unsupported; it would require a separate contract and compatibility review, not a repair script that edits the journal.

## Verified scope

`tests/network/interrupted_execution_test.py` exercises the actual private operator, bounded worker, Ability execution, SQLite claim and fixture provider in separate Kujo processes. Cancellation uses the actual canonical gateway/Ability path with a fixture authentication callback; real HTTP admission is covered separately by `cancellation_test.py`.

Five checkpoints each run with a killed original and a still-live original:

| Checkpoint | Required disposition |
| --- | --- |
| Before Ability reservation | Cancellation closes the payment; a late original cannot claim. |
| After committed Ability reservation | Concurrent exact retries cannot submit; cancellation retains the original reservation. |
| Before financial claim | Cancellation wins against the late original's captured revision. |
| After committed claim, before permit issuance | Cancellation fails. A killed original remains observation-only; a live original may submit once. |
| After processor charge, before observation persistence | Cancellation fails; a restarted worker observes the single charge. |

The suite also verifies authentication/tenant/stale-revision denial, four concurrent retries at both reserved pre-claim checkpoints, immutable terms and expiry, retained approval/provider journals, and unchanged unfinished execution records after SIGKILL. The fake processor has no financial uniqueness constraint. No real money moves.

This establishes safe abandonment and reconciliation routing for the declared SQLite implementation. It does not establish live financial-history restoration, provider hold cancellation, arbitrary-store correctness, power-loss durability or safe financial re-entry.
