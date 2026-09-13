#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${KUJO_BIN:?Set KUJO_BIN to an absolute Kujo executable}"
"$KUJO_BIN" run tests/domain.kujo
python3 scripts/binding_vectors.py --check
"$KUJO_BIN" run tests/bindings.kujo
store_dir=$(mktemp -d)
trap 'rm -rf "$store_dir"' EXIT
PAYMENTS_TEST_DB="$store_dir/state.db" "$KUJO_BIN" run tests/storage.kujo
python3 scripts/concurrency_test.py
python3 tests/network/migration_test.py
"$KUJO_BIN" run tests/lifecycle.kujo
"$KUJO_BIN" run tests/contracts.kujo
"$KUJO_BIN" run tests/approval_bindings.kujo --interpreter
PAYMENTS_TEST_DB="$store_dir/observations.db" "$KUJO_BIN" run tests/observations.kujo
PAYMENTS_TEST_DB="$store_dir/execution.db" "$KUJO_BIN" run tests/execution.kujo
PAYMENTS_TEST_DB="$store_dir/gateway.db" "$KUJO_BIN" run tests/gateway.kujo
python3 tests/network/http_test.py
python3 tests/network/provision_test.py
python3 scripts/architecture_test.py
python3 tests/network/operator_test.py
python3 tests/network/control_test.py
python3 tests/network/recovery_test.py
python3 tests/network/worker_test.py
PAYMENTS_TEST_DB="$store_dir/link-authorization.db" "$KUJO_BIN" run tests/link_authorization.kujo --interpreter
python3 tests/network/link_issuance_test.py
python3 scripts/mpp_vectors.py --check
"$KUJO_BIN" run tests/mpp.kujo --interpreter
PAYMENTS_TEST_DB="$store_dir/link-submit.db" "$KUJO_BIN" run tests/link_submission.kujo --interpreter
PAYMENTS_TEST_DB="$store_dir/link-provider.db" "$KUJO_BIN" run tests/link_provider.kujo --interpreter
python3 tests/network/merchant_http_test.py
