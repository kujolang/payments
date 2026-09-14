#!/usr/bin/env bash
set -euo pipefail
umask 077
if (( $# > 1 )); then echo 'Use check, serve or recover' >&2; exit 1; fi
cd "$(dirname "$0")/.."
: "${KUJO_BIN:?Set an absolute Kujo executable}"
: "${PAYMENTS_SANDBOX_DIR:?Set the private sandbox merchant directory}"
case "$KUJO_BIN" in /*) ;; *) exit 1;; esac
case "$PAYMENTS_SANDBOX_DIR" in /*) ;; *) exit 1;; esac
private_path() {
    local item="$1" maximum="$2" task_owner task_mode task_size
    test ! -L "$item" || return 1
    if test "$(uname -s)" = Darwin; then
        read -r task_owner task_mode task_size < <(stat -f '%u %Lp %z' "$item")
    else
        read -r task_owner task_mode task_size < <(stat -c '%u %a %s' "$item")
    fi
    [[ "$task_mode" =~ ^[0-7]{3,4}$ && "$task_size" =~ ^[0-9]+$ ]] || return 1
    test "$task_owner" = "$(id -u)" || return 1
    (( (8#$task_mode & 077) == 0 && task_size <= maximum ))
}
if ! test -d "$PAYMENTS_SANDBOX_DIR" || ! private_path "$PAYMENTS_SANDBOX_DIR" 1048576; then
    echo 'Sandbox directory must be private, owned by the operator, and not a symlink' >&2; exit 1
fi
for task_file in merchant.json stripe-test-key; do
    if ! test -f "$PAYMENTS_SANDBOX_DIR/$task_file" || ! private_path "$PAYMENTS_SANDBOX_DIR/$task_file" 65536; then
        echo 'Sandbox configuration and key must be private regular files' >&2; exit 1
    fi
done
for task_file in merchant.db merchant.db-wal merchant.db-shm; do
    if test -e "$PAYMENTS_SANDBOX_DIR/$task_file" || test -L "$PAYMENTS_SANDBOX_DIR/$task_file"; then
        if ! test -f "$PAYMENTS_SANDBOX_DIR/$task_file" || ! private_path "$PAYMENTS_SANDBOX_DIR/$task_file" 1073741824; then
            echo 'Sandbox journal files must be private regular files' >&2; exit 1
        fi
    fi
done
export PAYMENTS_SANDBOX_ACTION="${1:-check}"
case "$PAYMENTS_SANDBOX_ACTION" in check|serve|recover) ;; *) echo 'Use check, serve or recover' >&2; exit 1;; esac
exec "$KUJO_BIN" run src/executor/sandbox_merchant.kujo --interpreter
