#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")/.."
: "${KUJO_BIN:?Set KUJO_BIN to an absolute executable}"
: "${PAYMENTS_PROVISION_DIR:?Set an absolute new private directory}"
: "${PAYMENTS_PRINCIPAL_JSON:?Set the authenticated principal object}"
case "$PAYMENTS_PROVISION_DIR" in /*) ;; *) echo 'An absolute directory is required' >&2; exit 1;; esac
if test -e "$PAYMENTS_PROVISION_DIR"; then echo 'Refusing to overwrite an existing directory' >&2; exit 1; fi
mkdir -m 700 "$PAYMENTS_PROVISION_DIR"
"$KUJO_BIN" run scripts/provision.kujo --interpreter
