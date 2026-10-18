"""Operator recovery rehearsal with a separate authoritative synthetic processor.

No provider API or credentials. A verified publication remains immutable; only
its separate working copy receives observation writes. Never resume spending.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']


def run(args, env=None, ok=True):
    p = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
    assert 'SENTINEL' not in p.stdout + p.stderr, 'secret in drill output'
    assert (p.returncode == 0) == ok, (p.stdout, p.stderr)
    return json.loads(p.stdout)


def query(path, sql):
    with sqlite3.connect(path) as db:
        return db.execute(sql).fetchall()


def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


with tempfile.TemporaryDirectory(prefix='payments-operator-recovery-') as temporary:
    root = Path(temporary)
    core = root / 'live.db'
    processor = root / 'processor.db'
    env = {**os.environ, 'PAYMENTS_TEST_DB': str(core),
           'PAYMENTS_TEST_PROCESSOR_DB': str(processor), 'PAYMENTS_TEST_EXECUTION': '',
           'PAYMENTS_TEST_STOP': '', 'PAYMENTS_TEST_MODE': 'seed', 'PAYMENTS_TEST_SEED_FAULT': ''}
    fixture = [KUJO, 'run', 'tests/reconciliation.kujo', '--interpreter']
    assert run(fixture, env)['ok']
    assert query(processor, 'SELECT count(*) FROM fixture_charges') == [(1,)]
    assert query(core, 'SELECT state,claimed FROM executions') == [('reconciliation_required', 1)]
    core.chmod(0o600)
    control = root / 'control.json'
    control.write_text(json.dumps({'schema': 'kujo.payment-control/v1',
                                  'database': str(core), 'actor_ref': 'drill-operator'}))
    control.chmod(0o600)
    admin = {**env, 'PAYMENTS_CONTROL_CONFIG': str(control),
             'PAYMENTS_CONTROL_ACTION': 'pause', 'PAYMENTS_CONTROL_REVISION': '0'}
    assert run(['bash', 'scripts/control.sh'], admin)['control']['mode'] == 'paused'
    core.chmod(0o600)
    processor.chmod(0o600)
    config = root / 'recovery.json'
    config.write_text(json.dumps({'schema': 'kujo.payment-recovery-set/v1',
                                 'sources': {'core': str(core), 'processor_evidence': str(processor)}}))
    config.chmod(0o600)
    publication = root / 'publication'
    maintenance = [sys.executable, 'scripts/maintenance/recovery_set.py']
    assert run(maintenance + ['create', '--config', str(config), '--directory', str(publication)])['ok']
    assert run(maintenance + ['verify', '--directory', str(publication)])['ok']
    original = hashes(publication)
    # The exported processor is historical evidence only. Observations must use
    # the independent live ledger, never mistake a backup for current authority.
    work = root / 'working'
    shutil.copytree(publication / 'core', work)
    restored = work / 'payments.db'
    observe = {**env, 'PAYMENTS_TEST_DB': str(restored), 'PAYMENTS_TEST_MODE': 'unknown',
               'PAYMENTS_TEST_KEY': 'drill-unknown'}
    assert run(fixture, observe)['result']['status'] == 'reconciliation_required'
    # Exact observation replay cannot re-enter the provider.
    assert run(fixture, observe)['result']['status'] == 'reconciliation_required'
    assert query(processor, 'SELECT count(*) FROM observations') == [(1,)]
    observe.update(PAYMENTS_TEST_MODE='', PAYMENTS_TEST_KEY='drill-confirmed')
    assert run(fixture, observe)['result']['status'] == 'succeeded'
    assert run(fixture, observe)['result']['status'] == 'succeeded'
    assert query(processor, 'SELECT count(*) FROM observations') == [(2,)]
    assert query(processor, 'SELECT count(*) FROM fixture_charges') == [(1,)]
    assert query(processor, "SELECT count(*) FROM observations WHERE id='FORBIDDEN'") == [(0,)]
    assert query(restored, 'SELECT state,claimed FROM executions') == [('succeeded', 1)]
    assert query(restored, 'SELECT consumed FROM approvals') == [(1,)]
    assert query(core, 'SELECT state,claimed FROM executions') == [('reconciliation_required', 1)]
    control.write_text(json.dumps({'schema': 'kujo.payment-control/v1',
                                  'database': str(restored), 'actor_ref': 'drill-operator'}))
    revision = query(restored, 'SELECT revision FROM execution_control')[0][0]
    admin.update(PAYMENTS_CONTROL_ACTION='resume', PAYMENTS_CONTROL_REVISION=str(revision))
    assert not run(['bash', 'scripts/control.sh'], admin, ok=False)['ok']
    assert query(restored, 'SELECT mode FROM execution_control') == [('paused',)]
    assert run(maintenance + ['verify', '--directory', str(publication)])['ok']
    assert hashes(publication) == original, 'original recovery evidence modified'
print('Operational recovery: pause, coordinated capture, immutable verification, separate working copy, unknown/replay/fresh reconciliation, one charge and denied resume passed')
