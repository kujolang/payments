# Core SQLite schema migration

Core storage is now schema version 2. This private database version is independent of the canonical payment and Ability schema versions. New stores initialize all tables, guards and their provenance record in one transaction. Existing v2 stores must match the frozen required SQL definitions and provenance; missing safety objects are rejected rather than silently recreated.

The supported upgrade is the complete v1 schema frozen in `contracts/storage/v1-baseline.json`, from Payments commit `2a16d9e`, to the v2 schema in `contracts/storage/v2-baseline.json`. Earlier experimental variants, foreign databases, altered required tables/triggers and future versions are not automatically migrated. Extra application-owned objects are tolerated, but cannot replace required objects or the new migration history. Keep these baseline files immutable; a later structural change requires a new version and reviewed migration.

## Procedure

1. Quiesce all privileged workers using the database, including workers on older code. Pause alone cannot revoke their earlier claims or provider requests. Keep the database and private provider journals under administrator ownership.
2. Create a private [observation-only recovery snapshot](recovery-snapshots.md) of the original core journal. The snapshot tool validates the frozen v1 or v2 SQL profile. It is not a coordinated backup of provider state and cannot later resume spending.
3. Use a private administrator configuration matching `contracts/control.schema.json`, for example `{"schema":"kujo.payment-control/v1","database":"/private/live/payments.db","actor_ref":"migration-admin"}`. From the repository root, run:

   ```sh
   PAYMENTS_CONTROL_CONFIG=/private/migration-admin.json \
     "$KUJO_BIN" run src/executor/migrate.kujo --interpreter
   ```

4. Inspect the result. A successful v1 upgrade reports schema version 2 and leaves the original store paused. Start only current-version observation workers, inspect retained financial state and reconcile uncertain effects before deciding whether the original store may resume. Use the separate revision-checked incident control for that decision. A quarantined recovery copy remains permanently unable to resume.

Run migration under a bounded administrator process supervisor. SQL lock waits are capped at five seconds; whole-journal integrity work can take longer. SIGKILL before commit is tested to roll back the upgrade, but this is not a hard real-time filesystem guarantee.

## Atomicity and provenance

The migrator checks the exact required v1 SQL objects, database integrity and foreign keys, then acquires a write transaction and revalidates the version/profile. It pauses the store with an immutable control event, replaces the constrained version marker, installs the v2 history schema and records the source-baseline digest, actor and timestamp. All of that commits together. Financial execution rows, claims, approvals, request keys, receipts, observations, keyed Ability records and quarantine markers are preserved.

Concurrent migration commands serialize. Only the first v1-to-v2 upgrade writes history; later commands validate the current version and return its current control state without implicitly pausing or resuming it. A failed control-event write or process death before commit leaves the previous schema and financial records intact. New-store initialization is also transactional, so death before its first commit leaves an empty store that can be initialized normally.

There is no automatic downgrade. Replacing the live database with an old backup can resurrect approvals or lose a real claim; use quarantined copies for recovery inspection. Safe financial-history merge, coordinated provider-journal backups and interrupted Ability-invocation recovery remain separate release requirements.

## Verification

`tests/network/migration_test.py` exercises eight concurrent initializers, four concurrent migrators, exact preservation of consumed approvals/claims/receipts/evidence, permanent quarantine across upgrade, unknown schema and missing-trigger rejection, event-write rollback and SIGKILL during both migration and first initialization. Fault injection modifies only an isolated source copy; production code has no crash-hook environment variable. Normal CI never moves real money.
