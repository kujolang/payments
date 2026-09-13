# Provider authority binding

Decision, reviewed 2026-09-13: retain the current universal contract and native Link adapter. Clarify the acceptance requirement as verified binding to the intended payment authority, rather than requiring every provider to expose a global payer identifier. This does not accept the current fixture callbacks as deployment evidence or enable live credentials.

## Three distinct identities

- The **payment principal** is the authenticated host identity requesting/authorizing the Kujo operation, including its tenant. Ability approval binds that principal to the exact execution.
- **`provider.account_ref`** is an opaque host-owned installation alias in the immutable snapshot. It selects a configured payment authority; it is neither a bearer capability nor an assertion of a provider's global customer ID.
- The **provider authority** is the account, delegated grant, corporate credential or mandate actually capable of funding the action. Trusted installation must establish why that authority is permitted for the principal/tenant and preserve that binding across rotation and execution.

The three need not identify the same person. A corporate funding account can serve an authorized employee, and a delegated grant can authorize a requester without disclosing an account owner's personal identity. Requiring one universal provider-user identifier would encode an unnecessary account model into machine-native and delegated providers. Conversely, inventing an alias or hashing an unverified token cannot establish permission to use it.

## What existing code proves

`contracts/snapshot.schema.json` defines `account_ref` as a bounded opaque string. `src/domain/binding.kujo` includes it in the independent immutable snapshot digest. Link's issuance journal binds that snapshot and alias to the native authorization reference. The credential binding frames tenant, payer reference, account alias, client identity and scopes; generation CAS protects rotation. Enrollment's acceptance callback must verify the binding before installation, and its publication guard denies an interrupted acceptance.

These mechanisms prove consistency with trusted installation inputs. They do not independently prove that those inputs describe the intended external authority. Tests for changed bindings, tenant confusion, rotation races and interrupted acceptance remain relevant, but synthetic callback success cannot fill the missing external assertion. No hash, schema, receipt, callback signature or financial state transition changes in this decision.

## Required installation evidence

A supported installation must show:

1. An authenticated host principal/tenant explicitly selects the installation alias and the permitted funding authority, including any delegation. The requesting agent cannot supply the verifier or credential source.
2. A provider-supported account assertion **or a verified authorization/grant provisioning flow** links the acquired authority to that selection. Provider account IDs are useful where available, not a universal mandatory field. An operator's bare `true`, email equality or a generic "logged in" status is insufficient. Any operator-mediated verification must establish the actual selected authority and bind its review to this exact enrollment/installation.
3. Client, scope, credential family and generation remain bound through refresh, revocation, re-enrollment and every installed route. Switching a global session file, token environment variable or account behind an existing alias must not silently switch funding authority. Uncertain transitions remain unavailable until reconciled.
4. The exact payment intent still requires Kujo authorization and provider-native financial controls. Enrollment or account linking grants neither an Ability approval nor permission to resubmit an ambiguous execution.

These are acceptance conditions for the existing trusted ports, not a new identity service, policy engine or universal attestation object. A proposed provider-specific verifier must supply its evidence and negative tests before installation. Core cannot certify an arbitrary host callback.

## Link routes reviewed

The [pinned Link README](https://github.com/stripe/link-cli/blob/4aa62ba34eaeb884d00041681f5c7801521c0bf8/README.md#integrating-into-agents) documents agent CLI use, separate auth files and a client display name, while directing consumer-native integrations to its support route. It leaves SDK authentication/persistence to embedding applications. This is not evidence of a registered Kujo native client. The CLI's [auth implementation](https://github.com/stripe/link-cli/blob/4aa62ba34eaeb884d00041681f5c7801521c0bf8/packages/cli/src/auth/auth-resource.ts) uses its own client identity; a display label does not register another one. The reviewed [UserInfo contract](https://github.com/stripe/link-cli/blob/4aa62ba34eaeb884d00041681f5c7801521c0bf8/packages/sdk/src/resources/user-info.ts) does not establish the missing authority linkage.

Two implementation routes are conceptually possible: a supported native client using the existing executor, or an officially supported CLI executed entirely inside a separately reviewed privileged adapter. Running the official CLI is distinct from copying its client ID or credentials into Kujo's native OAuth flow. Neither route eliminates authority verification, merchant settlement evidence, isolation, idempotency or acceptance testing.

Do not add a CLI fallback merely to make a readiness gate appear closed. The current adapter does not install or run the CLI. A future CLI adapter would require executable/source pinning, an isolated session per authority, bounded argument-array execution, environment filtering, explicit refresh ownership, sanitized output and complete failure/reconciliation tests. It must retain the five-method semantic SPI and two-tool agent projection. No provider capability or production approval is inferred from this review.

## Current disposition

The Link gate remains open: supported native client provisioning, an implemented and validated authority-binding verifier, authenticated operator/installer deployment, authoritative merchant observations and provider acceptance have not been demonstrated. No contact, login, account call or payment was performed. The Link repository main HEAD check matched the already-reviewed Link source pin; cached web text was not used to change dependencies. `docs/evidence/provider-authority-review.json` records the inspected source hashes and scope.
