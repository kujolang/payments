"""Real Ability dispatch, independent processor counts and killed observation workers."""
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
COMMAND = [KUJO, 'run', 'tests/reconciliation.kujo', '--interpreter']

def call(env, mode='', key='observe-1'):
    p = subprocess.run(COMMAND, cwd=ROOT, env={**env, 'PAYMENTS_TEST_MODE': mode, 'PAYMENTS_TEST_KEY': key}, capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, (mode, p.stdout, p.stderr)
    assert 'SENTINEL' not in p.stdout + p.stderr
    return json.loads(p.stdout)

def count(path, query):
    with sqlite3.connect(path) as db:
        return db.execute(query).fetchone()[0]

def invariants(path):
    assert count(path, 'SELECT claimed FROM executions') == 1
    assert count(path, 'SELECT consumed FROM approvals') == 1
    assert count(str(path)+'.processor', 'SELECT count(*) FROM fixture_charges') == 1
    assert count(str(path)+'.processor', "SELECT count(*) FROM observations WHERE id='FORBIDDEN'") == 0
    with sqlite3.connect(path) as db:
        assert 'SENTINEL' not in repr(db.execute('SELECT * FROM audit').fetchall())
        assert 'SENTINEL' not in repr(db.execute('SELECT * FROM ability_calls').fetchall())

def fixture(root):
    path = root/'payments.db'
    env = {**os.environ, 'PAYMENTS_TEST_DB': str(path), 'PAYMENTS_TEST_STOP': ''}
    assert call(env, 'seed')['ok']
    return path, env

for mode in ('deny', 'approval', 'preflight_fail', 'foreign', 'nested', 'provider_mismatch', 'version_mismatch', 'definition', 'completed_fail', 'receipt_fail', 'observation_fail', 'provider_throw', 'paused', ''):
    with tempfile.TemporaryDirectory(prefix='payments-reconcile-') as directory:
        path, env = fixture(Path(directory))
        result = call(env, mode)
        denied = mode in ('deny', 'approval', 'preflight_fail', 'foreign', 'nested', 'provider_mismatch', 'version_mismatch', 'definition')
        assert result['ok'] is (mode in ('paused', '', 'provider_throw')), (mode, result)
        assert count(str(path)+'.processor', 'SELECT count(*) FROM observations') == (0 if denied else 1), (mode, result)
        if mode in ('completed_fail', 'receipt_fail', 'paused', ''):
            assert result['result']['status'] == 'succeeded', result
        if mode in ('observation_fail', 'provider_throw'):
            assert result['result']['status'] == 'reconciliation_required', result
        invariants(path)

with tempfile.TemporaryDirectory(prefix='payments-reconcile-replay-') as directory:
    path, env = fixture(Path(directory))
    first = call(env, 'unknown')
    assert first['ok'] and first['result']['status'] == 'reconciliation_required', first
    with ThreadPoolExecutor(max_workers=4) as pool:
        retries = list(pool.map(lambda _: call(env), range(4)))
    assert all(x['ok'] and x['result']['status'] == 'reconciliation_required' for x in retries), retries
    assert count(str(path)+'.processor', 'SELECT count(*) FROM observations') == 1
    fresh = call(env, key='observe-2')
    assert fresh['ok'] and fresh['result']['status'] == 'succeeded', fresh
    replay = call(env)
    assert replay['result']['status'] == 'succeeded', replay
    assert replay['ability_result']['receipt']['result']['status'] == 'reconciliation_required', replay
    assert count(str(path)+'.processor', 'SELECT count(*) FROM observations') == 2
    invariants(path)

for checkpoint in ('before_observe', 'after_observation', 'before_complete'):
    with tempfile.TemporaryDirectory(prefix='payments-reconcile-kill-') as directory:
        root = Path(directory); path, env = fixture(root); marker = root/'marker'
        killed_env = {**env, 'PAYMENTS_TEST_MODE': '', 'PAYMENTS_TEST_KEY': 'observe-1', 'PAYMENTS_TEST_STOP': checkpoint, 'PAYMENTS_TEST_MARKER': str(marker)}
        p = subprocess.Popen(COMMAND, cwd=ROOT, env=killed_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic()+15
            while not marker.exists() and p.poll() is None and time.monotonic() < deadline:
                time.sleep(.03)
            assert marker.exists(), (checkpoint, p.poll())
            p.kill(); p.communicate(timeout=5)
        finally:
            if p.poll() is None:
                p.kill(); p.communicate(timeout=5)
        prior = count(str(path)+'.processor', 'SELECT count(*) FROM observations')
        replay = call(env)
        assert not replay['ok'] and replay['ability_result']['code'] == 'ability_invocation_in_progress', replay
        assert count(str(path)+'.processor', 'SELECT count(*) FROM observations') == prior
        assert call(env, key='observe-2')['result']['status'] == 'succeeded'
        assert count(path, "SELECT count(*) FROM ability_calls WHERE operation='kujo.payments.execution.reconcile' AND receipt_json IS NULL") == 1
        invariants(path)
with tempfile.TemporaryDirectory(prefix='payments-reconcile-race-') as directory:
    path, env = fixture(Path(directory))
    for key in ('', 'x'*129):
        assert call(env, key=key)['code'] == 'invalid_idempotency_key'
    with ThreadPoolExecutor(max_workers=4) as pool:
        raced = list(pool.map(lambda _: call(env, 'slow'), range(4)))
    assert any(x['ok'] for x in raced), raced
    assert count(str(path)+'.processor', 'SELECT count(*) FROM observations') == 1
    invariants(path)
    other = {**env, 'PAYMENTS_TEST_EXECUTION': 'exec_2'}
    assert call(other, 'seed')['ok']
    changed = call(other)
    assert not changed['ok'], changed
    assert count(str(path)+'.processor', 'SELECT count(*) FROM observations') == 1
    assert count(str(path)+'.processor', 'SELECT count(*) FROM fixture_charges') == 2
    assert call(other, key='observe-2')['ok']
    assert count(str(path)+'.processor', 'SELECT count(*) FROM observations') == 2
print('Canonical reconciliation Ability: 14 policy/identity/provider/fault cases, key/execution binding, four-way claim and replay, fresh observation and three SIGKILL boundaries passed; one original charge')
