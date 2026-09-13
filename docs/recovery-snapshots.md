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


## Verify a published snapshot before use

```sh
python3 scripts/maintenance/verify_recovery.py \
  --snapshot-dir /private/recovery/incident-001
```

The read-only verifier checks bounded manifest parsing (including duplicate keys), the database publication hash, private owned regular files, required frozen core schema and migration lineage, SQLite integrity/foreign keys, the permanent quarantine marker, paused control evidence and normalized claimed-execution state. SQLite WAL/SHM/journal sidecars are refused. It checks file identities and hashes again after reading and emits only a compact integrity/quarantine result. It neither opens the database for writes nor enables spending. Default and maximum time/size bounds match the snapshot creator; a blocking filesystem operation is not a guaranteed hard real-time cancellation point.

Use it on a quiescent original publication in an administrator-controlled directory before making a separate working copy for observation. Reconciliation writes change the database hash, so the original manifest will not verify that modified copy; do not regenerate a hash and treat it as independently authenticated evidence. Re-snapshotting an existing quarantined copy retains its original quarantine lineage, which can differ from the immediate pre-quarantine hash in the new manifest.

Success verifies **core integrity and quarantine**, not source authenticity, freshness, complete financial history, or arbitrary application extensions. `additional_schema_objects` reports objects outside the required core profile; their semantics require separate trusted review. A self-consistent attacker-supplied manifest is not a signature or authorization. Keep trusted custody/provenance for the source and manifest, and never use this result as permission to resume financial execution. It does not bundle or restore private provider/credential journals.

`tests/network/recovery_verification_test.py` covers current and frozen-v1 publications, repeated exports, unchanged file bytes, 20 tamper/quarantine/path cases (including recomputed malicious manifests), and bounds. Existing recovery regressions remain in place.

## Capture a declared set of private journals

The privileged `recovery_set.py` command adds a shared SQLite write barrier around the core and up to seven private journals. Use this when a core-only copy would lose the provider references, credential-generation history, enrollment state or approval tombstones needed for incident analysis. It reuses the core snapshot/quarantine implementation; it is not a backup scheduler, credential installer or financial-history merge engine.

Create a mode-0600 configuration with absolute paths and stable local aliases:

```json
{
  "schema": "kujo.payment-recovery-set/v1",
  "sources": {
    "core": "/private/payments.db",
    "provider": "/private/link-payments.db",
    "credentials": "/private/link-vault.db",
    "enrollment": "/private/link-enrollment.db",
    "outbox": "/private/link-approval-outbox.db"
  }
}
```

These paths are examples. The operator must inventory the actual installation; a successful capture cannot detect a journal omitted from the configuration. Sources must be distinct, current-user-owned, private regular files. Symlinks, hard links and duplicate source files are rejected. Run under the trusted executor administrator in a directory whose parents are under trusted custody. For planned maintenance, pause core execution and stop/drain executor, enrollment, rotation and operator writers before capture. During an incident, record any uncertain in-flight work for reconciliation; the command itself reserves SQLite writes but cannot stop a remote request already in flight.

```sh
python3 scripts/maintenance/recovery_set.py create \
  --config /private/recovery-config.json \
  --directory /private/recovery/incident-set-001

python3 scripts/maintenance/recovery_set.py verify \
  --directory /private/recovery/incident-set-001
```

The destination must not exist. The same 30-second/256-MiB defaults and 300-second/16-GiB upper bounds apply; `--max-bytes` bounds the total copied database bytes, excluding the small manifests. All declared write reservations are acquired in deterministic path order before any database is captured and held until all copies are complete. Each database is copied through SQLite's backup API, including committed WAL content. Source transactions roll back without changing application rows. The core member receives its existing permanent execution quarantine; private members retain their original rows and are treated as opaque SQLite journals. SQL integrity/foreign-key checks do not establish provider-specific semantic validity.

The manifest appears only after all copies finish and reservations release. It identifies fixed relative member paths, sizes and SHA-256 hashes, with `consistency: declared_sqlite_write_barrier`. The verifier checks those exact paths and private permissions, refuses extra files/sidecars, checks every member's integrity and unchanged bytes, and invokes the core quarantine verifier. It emits only member count and verification scope. Neither command prints source paths, journal rows, credential values or raw exceptions. A partial or killed capture has no valid set manifest and cannot pass verification; preserve it privately for incident review or dispose of it under the installation's retention procedure, then retry with a new destination.

**The entire directory is credential-bearing private material.** These copies can contain access/refresh tokens, pending device codes and approval URLs. They are not encrypted by this command. Keep them out of agent mounts, Workcell artifacts, evidence collectors, source control, telemetry and ordinary file-sharing systems. Storage encryption, trusted custody, access control and retention belong to the operator's backup infrastructure. Mode 0600/0700 does not defend against the same OS principal or a host administrator. Hashes detect alteration relative to a trusted manifest; they are not signatures, freshness proofs or evidence that the declared set is complete.

Do not attach copied private journals to a normal executor or refresh tokens from a copied vault: the live generation may have advanced, and repeating a refresh can invalidate credentials. Preserve originals for inspection and establish current account/credential authority separately before provider observation. The set is not an installable live restore. Remote settlement can precede a delayed local commit; a common database write barrier therefore cannot prove complete financial history, absence of a charge, safe approval reuse or permission to resume. Coordinated financial-history recovery and a supported operational restore procedure remain release gates.

`tests/network/recovery_set_test.py` uses the actual private OCI seed for core, authorization, vault, enrollment and outbox journals. It exercises a writer against every reserved database, committed WAL inclusion, retained sentinel credentials only in private members, immutable verification, denied core resume, 13 tamper/path cases, aggregate size refusal, bounded lock contention, injected copy failure and an actual SIGKILL after private copy. Normal CI uses synthetic credentials and makes no provider or financial calls.
