# Bounded performance evidence

The normal HTTP conformance suite measures the real MCP client, STDIO frontend, public Kujo client and authenticated gateway against a synthetic pending purchase. It records one cold request, eight additional sequential replay/status samples each, five extra tool catalog lookups and a 250 ms idle observation. Existing conformance checks still assert exact replay, one business purchase per reference and zero financial claims. The fixture never authorizes or submits a payment.

Run `KUJO_BIN=/absolute/path/to/kujo python3 tests/network/http_test.py` after installing the repository's locked optional harness dependencies. It emits one `MCP measurements:` JSON record to stdout; normal Linux CI runs the same fixture. See [local evidence](evidence/mcp-performance-local.json) for the runtime hash, source hashes and measured platform. No additional benchmark service or dependency is required.

## Measured boundary

A temporary executable observer records only closed phase names (`project`, `request`, `inspect`) before replacing itself with the selected Kujo executable. It does not record arguments, inputs, environment values, credentials or receipts. Its Python startup adds overhead, so these timings must not be compared directly with earlier uninstrumented single-sample results. The observer is only part of the test harness; product code is unchanged.

The local Kujo 1.3.1 / Node 24.20.0 run measured 3,065 compact UTF-8 bytes for both tool descriptors, 182 bytes for the pending summary and 438 bytes for the MCP response envelope. The envelope includes text and structured content for MCP consumers; callers should place one summary in model context. Warm replay/status medians were approximately 214/221 ms over eight samples each. The reported p95 uses nearest-rank over eight samples and is therefore the sample maximum, not an estimate of production tail latency.

Observed native counts were one catalog projection, 13 request client processes and nine status client processes. The request count includes three intentionally rejected calls (changed terms and forbidden principal/approval fields); two unknown tool names start no native client. Five repeated catalog lookups cause no additional projection. The 250 ms idle observation causes no additional native invocation; this is a bounded observation, not a claim about every deployment scheduler.

## Enforced budgets

CI limits the combined two-tool descriptor JSON to 4,096 bytes, the compact pending summary to 512 bytes and its full MCP response envelope to 1,024 bytes. These are explicit fixture regression budgets with room for modest compatible changes. Exceeding them requires reviewing the model-visible contract rather than quietly growing it. They are byte budgets, not tokenizer counts or universal bounds for all providers/statuses. Timings are recorded without brittle host-speed thresholds; existing process and transport deadlines remain enforced.

## Remaining evaluation

Full provider authorization/submission/reconciliation latency, supported deployment concurrency, failure/recovery response sizes, tokenizer-specific context cost and broader SDK/Dispatch comparisons remain open. Current measurements show a native process per tool invocation; replacing that with a resident worker would add a lifecycle and isolation boundary and is not justified by this small local sample alone. Human approval remains asynchronous and outside invocation latency.
