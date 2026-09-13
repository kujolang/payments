#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
: "${KUJO_BIN:?Set KUJO_BIN to an absolute executable}"
: "${PAYMENTS_CONTROL_CONFIG:?Set a private database administrator configuration path}"
: "${PAYMENTS_CONTROL_ACTION:?Set inspect, pause or resume}"
"$KUJO_BIN" run src/executor/control.kujo --interpreter
