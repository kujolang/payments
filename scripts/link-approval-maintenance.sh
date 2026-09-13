#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
: "${KUJO_BIN:?Set KUJO_BIN to an absolute executable}"
: "${PAYMENTS_APPROVAL_MAINTENANCE_CONFIG:?Set the private administrator configuration path}"
"$KUJO_BIN" run src/providers/link/approval_maintenance.kujo --interpreter
