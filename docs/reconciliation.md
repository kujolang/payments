# Private reconciliation Ability

`reconcile_payment(store, principal, execution_id, key, definition, provider, observation_schema, confirmation, host)` dispatches the existing `kujo.payments.execution.reconcile@1.0.0` definition through Ability. Its canonical identity and keyed semantics are unchanged. This is a trusted executor API; it is absent from the HTTP gateway and the two model-visible tools.

The caller installs the canonical reconciliation definition, a provider matching the immutable snapshot, trusted confirmation code and the existing `clock_ms`, `policy(snapshot, invocation)` and `audit` callbacks. The principal must satisfy the closed Payments/Ability profile. The execution must already have a permanent financial claim and snapshot. Unknown scope, incompatible identity, substituted definition/provider or invalid key fails before observation.

Policy explicitly distinguishes reconciliation from financial execution using the Ability ID. An `allow` decision permits observation; `deny` or `approval_required` without a separate supported grant fails closed. A spent financial approval is never repurposed to authorize observations. Reconciliation can run while financial execution is paused or a core copy is quarantined, subject to ordinary host policy and availability of the matching private provider journal. It cannot re-enable that copy for spending.

## Keys and crash behavior

Keys are nonempty strings of at most 128 characters, chosen by the trusted host for one logical observation. The worker requires `installed.reconciliation_definition` and `host.reconciliation_key` when it encounters claimed nonterminal work. Missing configuration returns `reconciliation_configuration_required`; there is no fallback around Ability. Fixture hosts use UUIDs for independent steps; deterministic hosts should persist the chosen key with their own task.

- An exact completed retry returns the retained Ability operation receipt without another provider observation.
- An interrupted operation remains `ability_invocation_in_progress`. Retrying its key never restarts its handler or resets its journal.
- A deliberately new observation uses a new key, including after an interrupted observation. This permits a fresh evidence read, never financial resubmission. The original operation may still be running; normal evidence CAS and terminal-state rules apply.
- Reusing a key for another execution conflicts. Storage additionally binds the authenticated scope, execution and immutable snapshot using field framing; legacy receipt algorithms and existing operation rows are unchanged.
- Provider failures become unknown financial status. Observation-write failures retain the financial claim. Receipt or completed-audit failure can leave authoritative financial success with an unsuccessful Ability operation.

The private result contains `ok`, a freshly inspected compact `result`, and `ability_result`. The fresh domain summary is intentionally separate from an older replayed operation receipt. `ok: false` must not be interpreted as proof that no charge occurred. The worker strips the detailed Ability result; agents continue to inspect compact authoritative status.

## Boundary and proof

The handler calls only the existing observation path, which selects `provider.observe`, validates normalized evidence, invokes installed confirmation and transactionally records evidence/receipt. It never calls `prepare`, `request_authorization`, `submit`, approval consumption or dispatch-permit construction. The lower-level exported `reconcile_execution` remains a trusted internal composition function; importing it inside a privileged process is not an access-control boundary. Untrusted callers must remain outside that process.

`tests/network/reconciliation_test.py` exercises real Ability policy/audit/idempotency hooks with an independent non-deduplicating synthetic processor. It covers policy and identity denial, substituted definitions/providers, provider and persistence failures, keyed replay, a four-process observation race, different-execution key conflict, fresh observations and SIGKILL before observation, after evidence persistence and before Ability receipt completion. The fixture makes submission and native-authorization callbacks fail if touched. Existing worker and Link fixtures exercise the integrated path. Normal CI does not contact a provider or move funds.

Privileged wrapped callbacks use the supported interpreter path. These tests do not establish live merchant settlement, coordinated backup restoration, physical isolation for arbitrary deployments, hard preemption of an injected callback or a repair mechanism for abandoned Ability invocations. Provider implementations must keep `observe` free of credential issuance and financial submission; reviewed adapter code and deployment isolation enforce that responsibility.
