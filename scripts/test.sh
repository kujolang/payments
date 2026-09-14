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
export PAYMENTS_IDENTITY_VECTORS="$store_dir/identity-vectors.json"
python3 scripts/ability_identity_vectors.py --output "$PAYMENTS_IDENTITY_VECTORS"
"$KUJO_BIN" run tests/ability_identities.kujo
"$KUJO_BIN" run tests/ability_identities.kujo --interpreter
"$KUJO_BIN" run tests/approval_bindings.kujo --interpreter
python3 tests/network/identity_profile_test.py
PAYMENTS_TEST_DB="$store_dir/application-identity.db" "$KUJO_BIN" run tests/application_identity.kujo --interpreter
PAYMENTS_TEST_DB="$store_dir/observations.db" "$KUJO_BIN" run tests/observations.kujo
PAYMENTS_TEST_DB="$store_dir/execution.db" "$KUJO_BIN" run tests/execution.kujo
PAYMENTS_TEST_DB="$store_dir/gateway.db" "$KUJO_BIN" run tests/gateway.kujo
python3 tests/network/http_test.py
python3 tests/network/cancellation_test.py
python3 tests/network/interrupted_gateway_test.py
python3 tests/network/recovery_projections_test.py
python3 tests/network/dispatch_test.py
python3 tests/network/mcp_process_test.py
python3 tests/network/workcell_process_test.py
python3 tests/network/provision_test.py
python3 scripts/architecture_test.py
python3 tests/network/package_install_test.py
python3 tests/network/operator_test.py
python3 tests/network/operator_delivery_test.py
python3 tests/network/control_test.py
python3 tests/network/recovery_test.py
python3 tests/network/recovery_verification_test.py
python3 tests/network/recovery_set_test.py
python3 tests/network/worker_test.py
python3 tests/network/interrupted_execution_test.py
python3 tests/network/reconciliation_test.py
PAYMENTS_TEST_DB="$store_dir/link-authorization.db" "$KUJO_BIN" run tests/link_authorization.kujo --interpreter
"$KUJO_BIN" run tests/stripe_sandbox.kujo --interpreter
"$KUJO_BIN" run tests/sandbox_create.kujo --interpreter
PAYMENTS_TEST_DB="$store_dir/sandbox-merchant.db" "$KUJO_BIN" run tests/sandbox_merchant.kujo --interpreter
python3 tests/network/sandbox_merchant_test.py
python3 tests/network/sandbox_recovery_test.py
python3 tests/network/link_issuance_test.py
python3 tests/network/link_payment_journal_test.py
python3 tests/network/link_credentials_test.py
python3 tests/network/link_revocation_test.py
python3 tests/network/link_enrollment_test.py
python3 tests/network/private_seed_test.py
python3 tests/network/containment_process_test.py
python3 tests/network/link_approval_delivery_test.py
python3 tests/network/link_approval_retention_test.py
python3 scripts/mpp_vectors.py --check
"$KUJO_BIN" run tests/mpp.kujo --interpreter
PAYMENTS_TEST_DB="$store_dir/link-submit.db" "$KUJO_BIN" run tests/link_submission.kujo --interpreter
python3 tests/network/link_performance_test.py
python3 tests/network/merchant_http_test.py
