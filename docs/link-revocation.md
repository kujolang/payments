# Private Link credential revocation

`revoke_link_credentials(db, id, binding, generation, revoke, clock_ms, deadline_ms)` is an executor-only lifecycle operation. It uses the existing private vault and generation CAS; no generic payment contract, Ability definition, agent tool or provider SPI method changes.

A trusted host authenticates the operator and resolves the exact tenant/payer/account/client/scope binding. It supplies the current reviewed generation and a deadline with more than five seconds remaining. A single winner reads the retained refresh token and disables that local generation before calling the installed provider revocation function. Local disable increments the generation and clears live access/refresh columns. Other callers, stale bindings and repeated calls cannot obtain a token or repeat the provider request.

The private result is `{ok, state: "disabled", generation, provider_revocation}`. When `ok` is true, local disable committed. `provider_revocation` is `acknowledged` only when the callback returned strict boolean success within the caller's deadline and without clock rollback; otherwise it is `unknown`. It never returns a native token, response body or exception. Errors after disable may still return a generic failure; inspect the vault's local state before drawing conclusions.

Acknowledgment is an observation returned by this invocation, not a persisted provider status. The vault durably records local `disabled` only. A restart must not infer remote revocation from that state. A timeout, lost response or process crash leaves remote status unknown and local credentials disabled; this operation cannot be re-entered to recover the deleted token. Operator procedures must retain sanitized acknowledgment if required and use provider-controlled account/session management when remote status is unknown. This component does not claim durable native revocation reconciliation or coordinated vault backup recovery.

## In-flight rotation and requests

A rotation reservation already removes tokens from active vault columns. An operator can disable its current rotating generation; no token is available for a remote request, so provider status is unknown. Any later refresh completion fails its generation/state CAS and cannot restore local credentials. This does not prove that the provider failed to issue new tokens remotely.

Disabling the vault does not recall credentials already read by an in-flight request, reverse an existing financial claim, revoke a delivered approval URL or void a previously issued payment credential. Use payment incident controls and provider account controls for their separate responsibilities. No state in this module permits financial resubmission or unquarantining a recovered core database.

## Native transport and provenance

`link_oauth_revoke(clock_ms)` posts a form containing only the installed registered `client_id` and private `token` to `https://login.link.com/device/revoke`. It uses a five-second native timeout, a 32 KiB response bound, disabled redirects, DNS pinning and private-destination denial. It suppresses raw response content and accepts only HTTP 2xx as endpoint acknowledgment. Token form encoding shares the private refresh validator; caller-supplied origins, CLI defaults, shell commands, environment discovery and verbose logging are absent.

The endpoint/form/status behavior is grounded in [LinkAuthResource at the reviewed source commit](https://github.com/stripe/link-cli/blob/4aa62ba34eaeb884d00041681f5c7801521c0bf8/packages/cli/src/auth/auth-resource.ts). The upstream [logout implementation](https://github.com/stripe/link-cli/blob/4aa62ba34eaeb884d00041681f5c7801521c0bf8/packages/cli/src/commands/auth/logout.tsx) submits a refresh token and clears local storage even when revocation fails. Source hashes are recorded in `deployment/link-source.lock.json`; reviewed 2026-09-13. Kujo distinguishes local disable from provider acknowledgment explicitly.

The native HTTP port bounds its own request. An injected callback is trusted code; a post-call deadline check cannot preempt it. The enclosing private executor must enforce process/runtime bounds and contain callback output.

A 2xx response does not prove that all access tokens, sessions, grants, virtual cards or SPTs were revoked. Supported client registration, account identity, server-side propagation and actual provider revocation semantics require separate provider acceptance. No live account was contacted by these tests.

## Synthetic conformance

`tests/network/link_revocation_test.py` uses separate native Kujo processes, a private SQLite vault and an independent synthetic request ledger. It tests success, provider failure/exception/malformed results, late or rolled-back clocks, wrong binding/generation, encoded forms and pre-network denial, four-process contention, SIGKILL after the request begins and disabling during a refresh reservation. It verifies local disable before the provider callback, logical token removal, no local API/refresh use after disable, no reinstallation, no repeated provider request and no sentinel secrets in process output. This is logical credential deletion, not secure erasure or an all-sink production isolation claim.
