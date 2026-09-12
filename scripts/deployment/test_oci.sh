#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 scripts/deployment/fetch_runtime.py
for target in gateway agent-probe harness-probe; do
    docker buildx build --load --platform linux/amd64 -f deployment/Dockerfile --target "$target" -t "kujo-payments-$target:local" .
done
for test in domain bindings contracts lifecycle storage observations execution gateway operator; do
    docker run --rm --network none --read-only --cap-drop=ALL --security-opt=no-new-privileges --user 65532:65532 --pids-limit 64 --memory 512m --tmpfs /tmp:rw,nosuid,nodev,noexec,size=32m --mount "type=bind,src=$PWD/tests,dst=/app/tests,readonly" --env PAYMENTS_TEST_DB=/tmp/test.db --entrypoint /usr/local/bin/kujo kujo-payments-gateway:local run "tests/$test.kujo"
done
python3 tests/network/containment_test.py
