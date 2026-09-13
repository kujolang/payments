# Private Link approval URL retention

The approval outbox is private provider state. Version 2 keeps an immutable delivery identity after replacing an expired URL with SQL `NULL` and recording `retired_at_ms`. Its principal, snapshot, execution and expiry cannot change. The database rejects deletion, URL replacement and restoration after retirement. The active-URL expiry index supports bounded cleanup batches without scanning retired records. No operation authorizes, cancels, retries or settles a payment.

New installations create v2. Existing v1 databases are refused by the normal opener and require the explicit upgrade below. The exact v1 schema from commit `6b3464737d9268c4280ffdbcba52d4e507ae4ca3` is frozen in `approval_schema.kujo`; the independent fixture is `tests/fixtures/approval-outbox-v1.json`. Do not modify either baseline to accept schema drift. Credential-vault and core-journal schema versions are unchanged.

## Upgrade

1. Stop every process using the outbox, including older delivery workers. The `quiesced` flag is an operator assertion, not a process-isolation mechanism.
2. Preserve any required private backup under secret-storage controls. This is not a coordinated financial recovery procedure, and a stale outbox backup must not replace the active store: it can reintroduce retired URLs.
3. Save a mode-0600 configuration beneath an administrator-only directory:

   ```json
   {"schema":"kujo.link-approval-maintenance/v1","database":"/private/link-approval-outbox.db","action":"migrate","quiesced":true}
   ```

4. Run from the trusted host with the reviewed Kujo interpreter:

   ```sh
   PAYMENTS_APPROVAL_MAINTENANCE_CONFIG=/private/approval-migration.json \
     bash scripts/link-approval-maintenance.sh
   ```

   Set `KUJO_BIN` to the installed absolute executable first. Run under a bounded administrator process supervisor. SQL lock waits are limited to five seconds, but whole-store migration duration depends on database size and storage.

The migrator acquires a write transaction, checks the exact v1 schema and database integrity, copies every delivery binding and URL, installs v2 guards/index, removes v1 objects and changes `user_version` atomically. Repeated migration validates v2 and reports `migrated:false`. Concurrent migration callers produce one upgrade. Foreign, altered and future schemas fail closed. Older openers refuse the new version. Only v2 processes may resume afterward.

## Retire expired URLs

Use a separate private configuration:

```json
{"schema":"kujo.link-approval-maintenance/v1","database":"/private/link-approval-outbox.db","action":"retire","batch_limit":100}
```

Run the same command. It uses the host's current clock and processes at most 1–1000 expired active records in one transaction, returning only `ok` and the count retired. The host decides when to run another batch; Payments adds no scheduler. An incorrect forward clock can retire a URL prematurely, so clock trust is an operator responsibility. Clock rollback cannot restore a retired row. Staging the same native request again and delivering from that row remain denied after restart.

This is logical retention control, not secure media erasure or provider revocation. SQLite pages, journals, filesystem snapshots, backups, operator delivery sinks and already-running processes can retain earlier URL bytes. Keep them secret-classified and apply the deployment's retention/at-rest protection separately. The component cannot retract a URL already handed to an operator callback, clear its browser, or revoke a provider-side approval. Quiesce delivery workers when immediate cessation of in-memory delivery matters.

## Evidence scope

Native tests exercise frozen v1 preservation, new/old opener separation, four-process upgrade and cleanup races, exact batch bounds, permanent identity/retirement guards, re-staging/direct-delivery denial, administrator validation, disk-full rollback, and SIGKILL rollback during migration and retirement. Normal CI uses synthetic URLs and does not call Link or move money. Full release requirements remain in [the release checklist](release-checklist.md).
