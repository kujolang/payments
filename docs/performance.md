# Bounded performance evidence

The normal HTTP conformance suite measures the real MCP client, STDIO frontend, public Kujo client and authenticated gateway against a synthetic pending purchase. It records one cold request, eight additional sequential replay/status samples each, five extra tool catalog lookups and a 250 ms idle observation. Existing conformance checks still assert exact replay, one business purchase per reference and zero financial claims. The fixture never authorizes or submits a payment.

Run `KUJO_BIN=/absolute/path/to/kujo python3 tests/network/http_test.py` after installing the repository's locked optional harness dependencies. It emits one `MCP measurements:` JSON record to stdout; normal Linux CI runs the same fixture. See [local evidence](evidence/mcp-performance-local.json) for the runtime hash, source hashes and measured platform. No additional benchmark service or dependency is required.

## Measured boundary

A temporary executable observer records only closed phase names (`project`, `request`, `inspect`) before replacing itself with the selected Kujo executable. It does not record arguments, inputs, environment values, credentials or receipts. Its Python startup adds overhead, so these timings must not be compared directly with earlier uninstrumented single-sample results. The observer is only part of the test harness; product code is unchanged.

The local Kujo 1.3.1 / Node 24.20.0 run measured 3,065 compact UTF-8 bytes for both tool descriptors, 182 bytes for the pending summary and 438 bytes for the MCP response envelope. The envelope includes text and structured content for MCP consumers; callers should place one summary in model context. Warm replay/status medians were approximately 214/221 ms over eight samples each. The reported p95 uses nearest-rank over eight samples and is therefore the sample maximum, not an estimate of production tail latency.

Observed native counts were one catalog projection, 13 request client processes and nine status client processes. The request count includes three intentionally rejected calls (changed terms and forbidden principal/approval fields); two unknown tool names start no native client. Five repeated catalog lookups cause no additional projection. The 250 ms idle observation causes no additional native invocation; this is a bounded observation, not a claim about every deployment scheduler.

A second local run used the official checksum-verified Kujo 1.4.0 macOS x64 release with the same Node and fixture sources. It passed the full HTTP/SDK/MCP conformance path with the same byte sizes and native counts; eight-sample warm medians were approximately 216/226 ms. Its first replay took 535 ms, illustrating why one sample is not a latency guarantee. [Version 1.4 evidence](evidence/mcp-performance-1.4-local.json) records exact measurements and runtime provenance. Neither local run replaces pinned Linux CI or establishes a release-to-release performance comparison.

## Enforced budgets

CI limits the combined two-tool descriptor JSON to 4,096 bytes, the compact pending summary to 512 bytes and its full MCP response envelope to 1,024 bytes. These are explicit fixture regression budgets with room for modest compatible changes. Exceeding them requires reviewing the model-visible contract rather than quietly growing it. They are byte budgets, not tokenizer counts or universal bounds for all providers/statuses. Timings are recorded without brittle host-speed thresholds; existing process and transport deadlines remain enforced.

## Remaining evaluation

Full provider authorization/submission/reconciliation latency, supported deployment concurrency, failure/recovery response sizes, tokenizer-specific context cost and broader SDK/Dispatch comparisons remain open. Current measurements show a native process per tool invocation; replacing that with a resident worker would add a lifecycle and isolation boundary and is not justified by this small local sample alone. Human approval remains asynchronous and outside invocation latency.

## Complete synthetic Link lifecycle

`tests/network/link_performance_test.py` now runs the existing full Link/worker/Ability fixture in eight fresh native interpreter processes, each covering success, response loss after charge, changed checkout challenge and an unconfirmed HTTP 2xx. Every original financial/identity/secret assertion still runs. The normal host suite uses this driver instead of a separate single invocation of the same fixture.

Five phase intervals are measured with the runtime performance clock: preparation plus native authorization request, one explicit authorization poll, synthetic operator review/grant, submission attempt, and the next worker step. The business clock remains fixed for deterministic authorization tests. No scheduler, background polling or benchmark service is added. Each native process has a 30-second timeout; accepted captured output is limited to 32 KiB and scanned for sentinel secrets. The output-size assertion is after subprocess capture, not a hard memory limit on an arbitrary executable.

The initial verified Kujo 1.4.0 macOS x64 sample produced these median milliseconds over eight flows per scenario:

| Scenario | Prepare/authorize | Poll | Review/grant | Submit attempt | Follow-up |
| --- | ---: | ---: | ---: | ---: | ---: |
| Success | 100.0 | 51.5 | 166.6 | 251.8 | 12.2 |
| Lost response after charge | 95.3 | 55.2 | 170.5 | 244.6 | 183.1 |
| Changed challenge | 96.6 | 54.6 | 171.7 | 235.3 | 181.9 |
| Unconfirmed 2xx | 100.6 | 53.1 | 168.4 | 254.8 | 185.9 |

A native process runs all four scenarios and includes startup, fixture/journal creation and the original conformance assertions; its median was approximately 3.29 seconds. It is not a single-payment latency measurement. Phase timings cover local validation, SQLite work, Ability dispatch and in-process synthetic provider/merchant callbacks. They exclude real network latency, TLS, provider processing, human approval and production load. Follow-up is a terminal read for success and a reconciliation attempt for the other scenarios. The operator interval is an automated fixture grant, not a human response-time estimate. Nearest-rank p95 over eight samples is the sample maximum, not a production tail estimate. No host-speed pass/fail threshold or caching optimization is inferred from these samples.

Each flow made one native authorization POST and two merchant probes. Success, lost-response and unconfirmed-2xx flows made three native GETs, including one credential retrieval, and one merchant payment attempt. The changed challenge made two GETs, no credential retrieval and no payment attempt. The credential count is a subset of GETs, not an additional request. These are observed callback counts in the synthetic fixture; a merchant attempt is not proof of a charge. Reconciliation did not resubmit. No Link CLI subprocess is used.

Pending, first-result and follow-up summaries were 109–114 UTF-8 bytes and passed a 512-byte regression budget in every scenario. Those samples use the short `exec_1` fixture identifier; they do not replace the realistic MCP identifier measurements above or establish a universal maximum for every contract-valid identifier. Counts and sizes must agree across all repeated flows. Only closed phase/scenario names, timings, counts, status names and byte sizes are emitted; no payment journal, credential, URL, private response or approval object is included.

This expands the bounded fixture evidence to consequential execution and ambiguous/failure paths. Real provider latency, production concurrency, deployment-specific recovery costs, model-tokenizer costs and broader optional SDK/Dispatch comparisons still require separate evidence. It does not close provider sandbox/live acceptance or establish an SLO.
