# Choose and accept a deployment

Payments has no approved production installation yet. Start with a **staging-only
Linux x86-64 host**, synthetic identities and no provider credentials. The
repository's OCI profile is a test reference, not a turnkey hosted service.
A developer machine can run the rehearsal; it cannot certify a different server.

## What the owner needs to decide

Only the first two decisions are needed to start staging:

1. **Host and access:** an existing Linux server or a new staging machine; its
   owner and the approved way an administrator connects. Do not send passwords,
   SSH private keys, API tokens or payment credentials in chat.
2. **Exposure:** keep the service private initially. If remote clients need it,
   identify the domain and who manages its TLS edge and firewall.
3. **Operators:** who may approve payments, pause execution, inspect private
   evidence and restore backups. The agent runtime must not share their identity.
4. **Recovery targets:** maximum acceptable interruption and loss of journal
   history. A stale backup cannot authorize another charge. If these targets are
   unknown, leave them undecided; do not invent production guarantees.
5. **Custody:** where encrypted backups and restricted logs live, who can read
   them, and when they expire. Do not place private recovery sets in Git or a
   normal evidence collector.

No hosting purchase is necessary for repository verification. Host provisioning,
public exposure and real-money testing are separate actions, not implied by a
request to prepare release checks.

## Installation acceptance record

Keep one private record for the selected installation. Record evidence references
and hashes rather than secrets or copied journals. Mark each row `not run`,
`passed`, `failed` or `blocked`, with date, operator and immutable source/image
identity. A checkbox or self-reported configuration is not test evidence.

| Gate | Evidence required on the selected host |
| --- | --- |
| Artifact | Source commit, runtime hash, dependency lock and image digest; install from those exact inputs into a clean directory. Retain build provenance. Resolve and validate the executor project’s own locked dependencies; consumer client imports do not prove executor imports. |
| Process boundary | Separate agent and executor identities/namespaces; no shared vault, journal, home, browser profile or privileged socket. Run hostile file/environment/process/socket/network probes against this topology. |
| Private storage | Owner-only configuration, journal and SQLite sidecars; restrictive service umask; inspect filesystem ACLs, mounts and backup access separately. |
| Transport | Private listener; if remote, valid TLS and protected upstream route. Prove unauthenticated requests fail, wrong principals cannot inspect another tenant, redirects do not carry tokens, and configured body/header/time/rate limits are enforced. |
| Lifecycle | Synthetic request, exact replay, status and restart; same execution survives. No provider or execute endpoint is exposed. |
| Operator | Authenticated operator session, exact bound review, approval and incident pause. Prove an agent cannot invoke the private issuer or control process. |
| Logs | Unique fake secret canaries absent from edge/application/process/debug/telemetry/artifact output, including failures. Examine the actual configured destinations privately. |
| Egress | Agent cannot reach privileged services; executor destinations and DNS behavior match the reviewed allowlist. Provider-specific egress remains a later acceptance step. |
| Recovery | Inventory every journal; pause/drain writers; capture a coordinated private set; verify original bytes and quarantine; reconcile a separate copy with independent synthetic evidence; prove financial resume stays denied. |
| Operations | Service restart and host reboot preserve claims; disk-full, read-only storage and observation failure do not trigger financial resubmission. Record incident owner and monitoring path. |
| Upgrade | Retain old immutable artifact and private backup; rehearse documented migration on synthetic copies, preserving claims/quarantine. Do not restore an old live journal to roll back code. Unsupported schema rollback is a stop condition. |

Run the repository baseline and OCI/Workcell checks using
[deployment instructions](deployment.md) first. Then repeat the relevant probes
against the **actual installation**. The Docker reference run cannot prove its
host's public TLS, external log sinks, backup custody or a different runtime.

## Recovery acceptance boundary

Follow [recovery snapshots](recovery-snapshots.md) and
[non-Link acceptance](non-link-acceptance.md). Today the supported recovery result
is quarantined, observation-only evidence. There is no supported procedure to
resume spending from restored copies. A declared journal set cannot detect an
omitted journal or a remote charge absent from local history.

Production financial-history recovery therefore stays blocked until the chosen
provider/merchant supplies authoritative settlement evidence, replay history is
preserved, and a reviewed recovery procedure demonstrates that missing local
state cannot cause a duplicate charge. Link setup alone does not close this gate.

## Stop conditions and handoff

Stop on missing authority/history, unknown financial outcome, leaked canary,
shared agent/executor privileges, changed artifacts or unsupported migration.
Pause new claims and preserve private evidence; do not retry a financial action
to discover whether it happened.

Hand off only the redacted acceptance record, source/runtime/image identities,
pass/fail counts and evidence hashes. Record unresolved items explicitly. A
synthetic staging pass is not permission to move money or a production-grade
claim. See the [release checklist](release-checklist.md) for independent gates.
