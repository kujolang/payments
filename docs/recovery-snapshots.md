# Observation-only recovery snapshots

The administrative snapshot tool copies a supported core SQLite journal into a new private directory and permanently disables financial execution in that copy. It does not change the source journal or recover missing financial history. It uses Python's SQLite backup API for maintenance; financial application code remains Kujo.

```sh
python3 scripts/maintenance/recovery_snapshot.py \
  --source /private/live/payments.db \
  --output-dir /private/recovery/incident-001
```

The destination must not exist. Defaults are 256 MiB and a 30-second work deadline; explicit bounds are available through `--max-bytes` and `--timeout-seconds` (maximum 16 GiB and 300 seconds). Backup progress, SQL integrity checks and streaming hashes enforce these work limits; a blocked OS filesystem operation is not a guaranteed hard real-time cancellation point. Run under the trusted database administrator identity.

A successful result produces `payments.db` and `manifest.json`, both mode 0600 in a mode 0700 directory. The database is published without overwriting any existing file only after quarantine and its control event commit. The manifest records the snapshot hash before quarantine and the database hash at publication. These are integrity/provenance references, not signatures or proof that the source contained all real financial effects. Later reconciliation writes change the database hash. Interrupted publication may leave a quarantined database without a complete manifest; inspect it privately and use another new destination for a retry.

## What the copy can do

The SQLite backup includes committed WAL pages without copying live database files piecemeal. The tool validates integrity, foreign keys and the frozen v1/v2 core SQL profile. A permanent quarantine marker and SQL guards prevent financial claims, new native authorization reservations and normal resume. Reopening through Kujo retains those guards. Paused state is set with an immutable control event; executing claims become reconciliation-required without clearing their tombstones. A second snapshot of a recovery copy retains its original quarantine lineage.

Status inspection, evidence review and observation of retained claimed executions remain possible. Configure any reconciliation executor with the correct separately retained provider journal and observation authority. Missing provider references stay unknown; they do not authorize new issuance or submission. This tool handles only the core journal. It does not bundle Link's private journal, credentials, profiles or application configuration, and is not a complete disaster-recovery system.

## What the copy cannot prove

A snapshot may precede a charge whose claim is absent from that snapshot. Neither its hash, its unused approvals nor an empty claim table proves that charge did not happen. Therefore there is no supported switch to make a recovery copy spend again. Do not drop the quarantine marker, clear receipts or transplant old approvals into a new live store. Restore a quarantined copy through this tool; manually replacing live database files bypasses the maintenance boundary and is unsupported.

Re-enabling operations after loss of the authoritative journal requires separately verified financial-history recovery and preservation of all replay evidence. A quarantined v1 copy can use the explicit [v1-to-v2 migration](schema-migrations.md), retaining quarantine. Cross-journal backup coordination, evidence merge, retention and interrupted Ability-invocation recovery remain release requirements. A live original database remains governed by its own incident control and original claims; creating a snapshot never resumes it.

## Tested scope

`tests/network/recovery_test.py` verifies committed WAL inclusion, a source claim committed after a pre-claim snapshot, denied claims/resume/SQL bypasses from that stale copy, post-claim observation recovery, repeated quarantine, private permissions, publication hash, no overwrite, size refusal and future-schema refusal without source changes. The tests use temporary synthetic journals. They do not establish power-loss durability on every filesystem, live provider reconciliation or protection against a database/host administrator deliberately removing guards.
