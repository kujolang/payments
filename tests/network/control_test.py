"""Database-wide incident pause across real processes; no financial API."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']

def run(script, env, ok=True):
    result = subprocess.run([KUJO, 'run', script, '--interpreter'], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=25)
    value = json.loads(result.stdout)
    assert (result.returncode == 0) == ok and value['ok'] == ok, (result.stdout, result.stderr)
    return value

with tempfile.TemporaryDirectory(prefix='payments-control-') as directory:
    root = Path(directory)
    db = root/'payments.db'
    env = {**os.environ, 'PAYMENTS_TEST_DB': str(db), 'PAYMENTS_TEST_CONTROL': 'setup'}
    assert run('tests/control.kujo',env)['control'] == {'mode':'paused','revision':1}
    config = root/'control.json'
    config.write_text(json.dumps({'schema':'kujo.payment-control/v1','database':str(db),'actor_ref':'incident-admin'}))
    config.chmod(0o600)
    env.update(PAYMENTS_CONTROL_CONFIG=str(config),PAYMENTS_CONTROL_ACTION='inspect')
    assert run('src/executor/control.kujo',env)['control']['mode']=='paused'
    env['PAYMENTS_TEST_CONTROL']='claim'
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        claims=list(pool.map(lambda _:run('tests/control.kujo',env),range(4)))
    assert not any(c['won'] for c in claims)
    env.update(PAYMENTS_CONTROL_ACTION='resume',PAYMENTS_CONTROL_REVISION='0')
    assert run('src/executor/control.kujo',env,False)['code']=='control_conflict'
    env['PAYMENTS_CONTROL_REVISION']='1.0'
    assert run('src/executor/control.kujo',env,False)['code']=='control_revision_invalid'
    env['PAYMENTS_CONTROL_REVISION']='1'
    assert run('src/executor/control.kujo',env)['control']=={'mode':'active','revision':2}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        claims=list(pool.map(lambda _:run('tests/control.kujo',env),range(4)))
    assert sum(c['won'] for c in claims)==1
    env.update(PAYMENTS_CONTROL_ACTION='pause',PAYMENTS_CONTROL_REVISION='2')
    assert run('src/executor/control.kujo',env)['control']=={'mode':'paused','revision':3}
    env['PAYMENTS_TEST_CONTROL']='recover'
    assert run('tests/control.kujo',env)['status']=='reconciliation_required'
    config.write_text('SENTINEL_PRIVATE_CONTROL_CONFIG invalid')
    assert run('src/executor/control.kujo',env,False)=={'ok':False,'code':'control_failed'}
print('Execution control: persistent pause, stale resume denial, transactional audit rollback, concurrent claim denial, at-most-one resumed claim and paused recovery passed')
