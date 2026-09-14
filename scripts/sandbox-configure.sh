#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
: "${KUJO_BIN:?Set an absolute Kujo executable}"
: "${PAYMENTS_SANDBOX_PLAN:?Set a reviewed sandbox plan file}"
: "${PAYMENTS_SANDBOX_DIR:?Set a new absolute private output directory}"
case "$KUJO_BIN" in /*) ;; *) exit 1;; esac
case "$PAYMENTS_SANDBOX_DIR" in /*) ;; *) exit 1;; esac
if test -e "$PAYMENTS_SANDBOX_DIR" || test -L "$PAYMENTS_SANDBOX_DIR"; then
    echo 'Refusing to replace an existing sandbox directory' >&2; exit 1
fi
exec "$KUJO_BIN" run src/executor/sandbox_configure.kujo --interpreter
