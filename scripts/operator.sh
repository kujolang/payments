#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
: "${KUJO_BIN:?Set KUJO_BIN to an absolute executable}"
: "${PAYMENTS_OPERATOR_CONFIG:?Set the trusted operator configuration path}"
: "${PAYMENTS_EXECUTION_ID:?Set the payment execution identifier}"
: "${PAYMENTS_OPERATOR_ACTION:?Set review or approve}"
"$KUJO_BIN" run src/executor/operator.kujo --interpreter
