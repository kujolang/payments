"""Actual local admin entrypoints: private-path rejection before runtime entry."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']


def call(kind, env, ok=True):
    p = subprocess.run(['bash', 'scripts/'+kind+'.sh'], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=30)
    assert (p.returncode == 0) == ok, 'admin launcher result'
    assert 'SENTINEL' not in p.stdout+p.stderr and 'Traceback' not in p.stderr
    value = json.loads(p.stdout)
    if not ok:
        assert value == {'ok': False, 'code': 'private_admin_config_required'}
    return value


cases = ('config_mode', 'config_parent', 'config_symlink', 'config_hardlink',
         'config_missing', 'config_directory', 'duplicate', 'oversize', 'schema',
         'db_mode', 'db_relative', 'db_missing', 'db_symlink', 'db_hardlink',
         'db_parent', 'sidecar_mode', 'sidecar_symlink', 'sidecar_hardlink', 'runtime_relative')
for kind in ('operator', 'control'):
    for case in cases:
        with tempfile.TemporaryDirectory(prefix='payments-admin-refusal-') as tmp:
            root = Path(tmp); configs = root/'config'; configs.mkdir(mode=0o700)
            state = root/'state'; state.mkdir(mode=0o700)
            database = state/'payments.db'; database.write_bytes(b'SENTINEL_PRIVATE_JOURNAL'); database.chmod(0o600)
            config = configs/'admin.json'
            data = {'schema': 'kujo.payment-'+kind+'/v1', 'database': str(database)}
            config.write_text(json.dumps(data)); config.chmod(0o600)
            marker = root/'invoked'
            runtime = root/'runtime'
            runtime.write_text('#!/usr/bin/env python3\nimport os,pathlib\npathlib.Path(os.environ["TEST_ADMIN_MARKER"]).touch()\nprint("SENTINEL_UNEXPECTED_RUNTIME")\n')
            runtime.chmod(0o700)
            env = {**os.environ, 'KUJO_BIN': str(runtime), 'TEST_ADMIN_MARKER': str(marker),
                   'PAYMENTS_OPERATOR_CONFIG': str(config), 'PAYMENTS_CONTROL_CONFIG': str(config),
                   'PAYMENTS_EXECUTION_ID': 'exec_1', 'PAYMENTS_OPERATOR_ACTION': 'review',
                   'PAYMENTS_CONTROL_ACTION': 'inspect'}
            if case == 'config_mode': config.chmod(0o644)
            elif case == 'config_parent': configs.chmod(0o755)
            elif case in ('config_symlink', 'config_hardlink'):
                original = configs/'original'; config.rename(original)
                if case.endswith('symlink'): config.symlink_to(original)
                else: os.link(original, config)
            elif case == 'config_missing': config.unlink()
            elif case == 'config_directory': config.unlink(); config.mkdir(mode=0o700)
            elif case == 'duplicate': config.write_text('{"database":"SENTINEL","database":"'+str(database)+'"}')
            elif case == 'oversize': config.write_text('x'*65537)
            elif case == 'schema': config.write_text(json.dumps({**data, 'schema': 'wrong'}))
            elif case == 'db_mode': database.chmod(0o644)
            elif case == 'db_relative': config.write_text(json.dumps({**data, 'database': 'payments.db'}))
            elif case == 'db_missing': database.unlink()
            elif case in ('db_symlink', 'db_hardlink'):
                original = state/'original'; database.rename(original)
                if case.endswith('symlink'): database.symlink_to(original)
                else: os.link(original, database)
            elif case == 'db_parent': state.chmod(0o755)
            elif case.startswith('sidecar'):
                sidecar = Path(str(database)+'-wal')
                if case == 'sidecar_mode': sidecar.write_text('SENTINEL'); sidecar.chmod(0o644)
                elif case == 'sidecar_symlink': sidecar.symlink_to(database)
                else: os.link(database, sidecar)
            elif case == 'runtime_relative': env['KUJO_BIN'] = 'kujo'
            call(kind, env, False)
            assert not marker.exists(), 'runtime entered before private configuration acceptance'

with tempfile.TemporaryDirectory(prefix='payments-admin-valid-') as tmp:
    root = Path(tmp); db = root/'payments.db'
    env = {**os.environ, 'PAYMENTS_TEST_DB': str(db)}
    p = subprocess.run([KUJO, 'run', 'tests/operator.kujo', '--interpreter'], cwd=ROOT,
                       env=env, capture_output=True, text=True, timeout=30, check=True)
    setup = json.loads(p.stdout); db.chmod(0o600)
    config = root/'operator.json'
    config.write_text(json.dumps({'schema': 'kujo.payment-operator/v1', 'database': str(db), 'authority': setup['authority']})); config.chmod(0o600)
    env.update(PAYMENTS_OPERATOR_CONFIG=str(config), PAYMENTS_OPERATOR_ACTION='review', PAYMENTS_EXECUTION_ID='exec_1')
    review = call('operator', env); assert review['binding_digest'] == setup['review_digest']
    env.update(PAYMENTS_OPERATOR_ACTION='approve', PAYMENTS_REVIEW_DIGEST=review['binding_digest'])
    assert call('operator', env)['status'] == 'ready'
    control = root/'control.json'
    control.write_text(json.dumps({'schema': 'kujo.payment-control/v1', 'database': str(db), 'actor_ref': 'operator'})); control.chmod(0o600)
    env.update(PAYMENTS_CONTROL_CONFIG=str(control), PAYMENTS_CONTROL_ACTION='pause', PAYMENTS_CONTROL_REVISION='0')
    assert call('control', env)['control']['mode'] == 'paused'
    with sqlite3.connect(db) as connection:
        assert connection.execute('SELECT claimed FROM executions').fetchall() == [(0,)]
        assert connection.execute('SELECT consumed FROM approvals').fetchall() == [(0,)]
print('Admin launchers: 38 unsafe path/config/runtime refusals before runtime entry, real bound review/approval and pause, no financial claim passed')
