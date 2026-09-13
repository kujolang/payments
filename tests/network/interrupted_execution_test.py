"""Close unclaimed interrupted executions; never reopen a financial invocation.

Real Kujo Ability/store/provider paths, independent non-deduplicating processor,
SIGKILL and still-live originals. Gateway authentication is a fixture callback;
HTTP credential admission has separate cancellation conformance coverage.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']
EXECUTE = 'kujo.payments.execution.execute'


def run(script, env):
    process = subprocess.run([KUJO, 'run', script, '--interpreter'], cwd=ROOT,
                             env=env, capture_output=True, text=True, timeout=20)
    assert 'SENTINEL' not in process.stdout + process.stderr
    assert process.returncode == 0, (process.stdout, process.stderr)
    return json.loads(process.stdout)


def gateway(root, env, request, mode=''):
    path = root / ('request-' + str(time.time_ns()) + '.json')
    path.write_text(json.dumps(request))
    return run('tests/interrupted_gateway_fixture.kujo', {
        **env, 'PAYMENTS_TEST_REQUEST': str(path), 'PAYMENTS_TEST_MODE': mode,
        'PAYMENTS_TEST_STOP': '', 'PAYMENTS_TEST_RELEASE': '',
    })


def inspect(database):
    with sqlite3.connect(database) as db:
        row = db.execute('SELECT state,claimed,revision,intent_json,snapshot_json,'
                         'snapshot_digest,expires_at_ms FROM executions').fetchone()
        approval = db.execute('SELECT consumed FROM approvals').fetchone()[0]
        calls = db.execute('SELECT * FROM ability_calls WHERE operation=?', (EXECUTE,)).fetchall()
    with sqlite3.connect(str(database) + '.processor') as db:
        charges = db.execute('SELECT count(*) FROM fixture_charges').fetchone()[0]
        authorizations = db.execute('SELECT count(*) FROM fixture_authorizations').fetchone()[0]
    return row, approval, calls, charges, authorizations


for boundary in ('before_begin', 'after_begin', 'before_claim', 'after_claim', 'before_observation'):
    for killed in (True, False):
        with tempfile.TemporaryDirectory(prefix='payments-execution-interruption-') as directory:
            root = Path(directory)
            fixture = json.loads((ROOT / 'tests/fixtures/domain.json').read_text())
            now = int(time.time() * 1000)
            fixture['intent']['expires_at_ms'] = now + 120000
            fixture['snapshot']['expires_at_ms'] = now + 120000
            fixture['capabilities'].update(observed_at_ms=now, valid_until_ms=now + 120000)
            source = root / 'fixture.json'
            source.write_text(json.dumps(fixture))
            database = root / 'payments.db'
            marker, release = root / 'marker', root / 'release'
            env = {**os.environ, 'PAYMENTS_TEST_DB': str(database),
                   'PAYMENTS_WORKER_FIXTURE': str(source), 'PAYMENTS_FIXTURE_BEHAVIOR': 'success',
                   'PAYMENTS_WORKER_STOP': '', 'PAYMENTS_TEST_MARKER': str(marker),
                   'PAYMENTS_TEST_RELEASE': str(release)}
            assert run('tests/worker.kujo', env)['result']['status'] == 'awaiting_authorization'
            config = root / 'operator.json'
            config.write_text(json.dumps({
                'schema': 'kujo.payment-operator/v1', 'database': str(database),
                'authority': {'payer': fixture['intent']['principal'],
                              'operator': {'type': 'human', 'id': 'operator_1', 'tenant_id': 'tenant_1'},
                              'issuer_ref': 'local-operator-v1', 'ttl_ms': 60000}}))
            config.chmod(0o600)
            operator = {**env, 'PAYMENTS_OPERATOR_CONFIG': str(config),
                        'PAYMENTS_EXECUTION_ID': 'exec_1', 'PAYMENTS_OPERATOR_ACTION': 'review'}
            review = run('src/executor/operator.kujo', operator)
            operator.update(PAYMENTS_OPERATOR_ACTION='approve', PAYMENTS_REVIEW_DIGEST=review['binding_digest'])
            assert run('src/executor/operator.kujo', operator)['status'] == 'ready'
            original = subprocess.Popen([KUJO, 'run', 'tests/worker.kujo', '--interpreter'],
                                        cwd=ROOT, env={**env, 'PAYMENTS_WORKER_STOP': boundary},
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 15
                while not marker.exists():
                    if original.poll() is not None:
                        raise AssertionError(original.communicate(timeout=5))
                    assert time.monotonic() < deadline, 'execution checkpoint unavailable'
                    time.sleep(.02)
                if killed:
                    original.kill()
                    out, err = original.communicate(timeout=5)
                    assert original.returncode == -9 and 'SENTINEL' not in out + err
                before = inspect(database)
                claimed = boundary in ('after_claim', 'before_observation')
                assert before[0][1] == int(claimed) and before[1] == int(claimed)
                assert len(before[2]) == int(boundary != 'before_begin')
                assert all(call[-1] is None for call in before[2])
                assert before[3] == int(boundary == 'before_observation') and before[4] == 1
                request = {'operation': 'cancel', 'input': {'execution_id': 'exec_1',
                           'expected_revision': before[0][2]}, 'idempotency_key': 'close-interrupted'}
                # Failed authentication, wrong tenant and stale revision cannot retire it.
                for mode in ('unauthenticated', 'foreign'):
                    assert not gateway(root, env, request, mode)['ok']
                stale = {**request, 'input': {**request['input'], 'expected_revision': 0},
                         'idempotency_key': 'stale-close'}
                assert not gateway(root, env, stale)['ok']
                assert inspect(database) == before
                if boundary in ('after_begin', 'before_claim'):
                    # A retry observes the reserved Ability invocation; it cannot execute.
                    with ThreadPoolExecutor(max_workers=4) as pool:
                        results = list(pool.map(lambda _: run('tests/worker.kujo', env), range(4)))
                    assert all(not result['ok'] and result['result']['status'] == 'ready' for result in results)
                    assert inspect(database) == before
                closed = gateway(root, env, request)
                assert closed['ok'] == (not claimed), closed
                if not claimed:
                    assert closed['result']['status'] == 'closed'
                    assert gateway(root, env, request) == closed
                if not killed:
                    release.write_text('resume')
                    out, err = original.communicate(timeout=15)
                    assert original.returncode == 0 and 'SENTINEL' not in out + err, (out, err)
                    assert json.loads(out)['result']['status'] == ('succeeded' if claimed else 'closed')
                for _ in range(2):
                    observed = run('tests/worker.kujo', env)
                    expected = 'closed' if not claimed else ('reconciliation_required' if killed and boundary == 'after_claim' else 'succeeded')
                    assert observed['result']['status'] == expected, observed
                after = inspect(database)
                assert after[0][3:] == before[0][3:], 'immutable terms or expiration replaced'
                assert after[0][1] == int(claimed) and after[1] == int(claimed)
                assert after[3] == int(claimed and (not killed or boundary == 'before_observation'))
                assert after[4] == 1, 'native authorization recreated'
                if before[2]:
                    assert len(after[2]) == 1 and after[2][0][:-1] == before[2][0][:-1]
                    if killed:
                        assert after[2] == before[2], 'abandoned invocation receipt rewritten'
                # Cancellation does not revoke or delete provider authorization/approval evidence.
                with sqlite3.connect(database) as db:
                    assert db.execute('SELECT count(*) FROM issued_approvals').fetchone()[0] == 1
                    assert db.execute('SELECT count(*) FROM provider_authorizations').fetchone()[0] == 1
            finally:
                if original.poll() is None:
                    original.kill()
                    original.communicate(timeout=5)
print('Interrupted execution: five boundaries with killed/live originals, four concurrent pre-claim retries, authenticated scoped cancellation, preserved tombstones/terms, post-claim refusal and no repeated charge passed')
