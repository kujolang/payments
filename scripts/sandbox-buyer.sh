#!/usr/bin/env bash
set -euo pipefail
umask 077
if (( $# > 1 )); then exit 1; fi
cd "$(dirname "$0")/.."
: "${KUJO_BIN:?Set an absolute Kujo executable}"
: "${PAYMENTS_SANDBOX_DIR:?Set the private sandbox merchant directory}"
case "$KUJO_BIN" in /*) ;; *) exit 1;; esac
case "$PAYMENTS_SANDBOX_DIR" in /*) ;; *) exit 1;; esac
. scripts/private-sandbox.sh
if ! test -d "$PAYMENTS_SANDBOX_DIR" || ! private_path "$PAYMENTS_SANDBOX_DIR" 1048576; then
    echo 'Sandbox directory must be private, owned by the operator, and not a symlink' >&2; exit 1
fi
for task_file in merchant.json buyer.json buyer-host.json stripe-test-key; do
    if ! test -f "$PAYMENTS_SANDBOX_DIR/$task_file" || ! private_path "$PAYMENTS_SANDBOX_DIR/$task_file" 65536; then
        echo 'Sandbox configuration and key must be private regular files' >&2; exit 1
    fi
done
for task_file in merchant.db merchant.db-wal merchant.db-shm buyer.db buyer.db-wal buyer.db-shm link.db link.db-wal link.db-shm enrollment.db enrollment.db-wal enrollment.db-shm vault.db vault.db-wal vault.db-shm; do
    if test -e "$PAYMENTS_SANDBOX_DIR/$task_file" || test -L "$PAYMENTS_SANDBOX_DIR/$task_file"; then
        if ! test -f "$PAYMENTS_SANDBOX_DIR/$task_file" || ! private_path "$PAYMENTS_SANDBOX_DIR/$task_file" 1073741824; then
            echo 'Sandbox journal files must be private regular files' >&2; exit 1
        fi
    fi
done
export PAYMENTS_SANDBOX_ACTION="${1:-status}"
case "$PAYMENTS_SANDBOX_ACTION" in request|status|connection|step|review|approve) ;; *) echo 'Use request, status, connection, step, review or approve' >&2; exit 1;; esac
exec "$KUJO_BIN" run src/executor/sandbox_buyer.kujo --interpreter
