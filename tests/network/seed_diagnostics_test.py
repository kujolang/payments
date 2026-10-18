"""Different seed failures must survive stress reporting without private output."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('stress', ROOT/'scripts/acceptance/reconciliation_stress.py')
stress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stress)
real_run = subprocess.run

for fault, state, code, charge in (
        ('preflight', 'ready', 'ability_audit_failed', 0),
        ('observation', 'executing', 'storage_failure', 1)):
    executions = []
    def inject(args, **kwargs):
        kwargs['env'] = {**kwargs['env'], 'PAYMENTS_TEST_SEED_FAULT': fault}
        p = real_run(args, **kwargs)
        assert p.returncode != 0 and 'unknown_after_charge' in p.stderr
        assert 'SENTINEL' not in p.stdout+p.stderr
        db = kwargs['env']['PAYMENTS_TEST_DB']
        with sqlite3.connect(db) as core:
            assert core.execute('SELECT state,claimed FROM executions').fetchall() == [(state, charge)]
        with sqlite3.connect(db+'.processor') as processor:
            assert processor.execute('SELECT count(*) FROM fixture_charges').fetchone() == (charge,)
        executions.append(p.returncode)
        return p
    with patch.object(stress.subprocess, 'run', side_effect=inject):
        result = stress.sample(0)
    assert len(executions) == 1, 'failed financial seed was retried'
    assert not result['ok'] and result['process_exit'] == executions[0]
    assert result['claimed'] == result['consumed'] == result['charges'] == charge
    assert result['seed_diagnostic'] == {
        'schema': 'kujo.payments.seed-failure/v1', 'status': state,
        'code': code, 'claimed': charge, 'charges': charge}

base = {'schema': 'kujo.payments.seed-failure/v1', 'status': 'executing',
        'code': 'SENTINEL_PRIVATE_ERROR', 'claimed': 1, 'charges': 1}
assert stress.seed_diagnostic(json.dumps(base))['code'] == 'unrecognized'
for value in ('SENTINEL', 'x'*4097, '{}', 'null', '[]',
              json.dumps({**base, 'status': 'SENTINEL'}),
              json.dumps({**base, 'claimed': True}),
              json.dumps({**base, 'charges': -1}),
              json.dumps({**base, 'private': 'SENTINEL'})):
    assert stress.seed_diagnostic(value) is None
# Even a successful process is not accepted if its output contains a canary.
with patch.object(stress.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{"ok":true}', 'SENTINEL')):
    result = stress.sample(1)
assert not result['ok'] and result['code'] == 'sentinel_output'
assert 'SENTINEL' not in json.dumps(result)
with patch.object(stress.subprocess, 'run', side_effect=subprocess.TimeoutExpired([], 30, output='SENTINEL')):
    result = stress.sample(2)
assert not result['ok'] and result['code'] == 'timeout' and result['process_exit'] is None
assert 'SENTINEL' not in json.dumps(result)
print('Seed diagnostics: actual pre-claim audit and post-charge storage faults distinguished, no retry, scalar sanitization, sentinel-output and timeout rejection passed')
