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
"$KUJO_BIN" run tests/lifecycle.kujo
"$KUJO_BIN" run tests/contracts.kujo
