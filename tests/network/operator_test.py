"""Real separate-process local operator review and durable grant; synthetic intent."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']

def run(script, env, success=True):
    result = subprocess.run([KUJO, 'run', script, '--interpreter'], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=20)
    assert (result.returncode == 0) == success, (result.stdout, result.stderr)
    value = json.loads(result.stdout)
    assert value['ok'] == success, value
    return value

with tempfile.TemporaryDirectory(prefix='payments-operator-') as directory:
    root = Path(directory)
    database = root/'payments.db'
    env = {**os.environ, 'PAYMENTS_TEST_DB':str(database)}
    setup = run('tests/operator.kujo', env)
    config = root/'operator.json'
    config.write_text(json.dumps({'schema':'kujo.payment-operator/v1','database':str(database),'authority':setup['authority']}))
    config.chmod(0o600)
    env.update(PAYMENTS_OPERATOR_CONFIG=str(config),PAYMENTS_EXECUTION_ID='exec_1',PAYMENTS_OPERATOR_ACTION='review')
    review = run('src/executor/operator.kujo', env)
    assert review['binding_digest'] == setup['review_digest']
    assert review['snapshot']['principal'] == setup['payer']
    assert review['snapshot']['charge'] == {'minor':5500,'currency':'USD'}
    env.update(PAYMENTS_OPERATOR_ACTION='approve',PAYMENTS_REVIEW_DIGEST='wrong')
    assert run('src/executor/operator.kujo',env,False)['code']=='review_changed'
    env['PAYMENTS_EXECUTION_ID']='other_execution'
    run('src/executor/operator.kujo',env,False)
    env.update(PAYMENTS_EXECUTION_ID='exec_1',PAYMENTS_REVIEW_DIGEST=review['binding_digest'])
    approved=run('src/executor/operator.kujo',env)
    assert approved['status']=='ready'
    assert run('src/executor/operator.kujo',env,False)['code']=='not_reviewable'
    with sqlite3.connect(database) as db:
        state,claimed=db.execute('SELECT state,claimed FROM executions').fetchone()
        assert (state,claimed)==('ready',0)
        assert db.execute('SELECT count(*) FROM approvals').fetchone()[0]==1
        approval=json.loads(db.execute('SELECT approval_json FROM issued_approvals').fetchone()[0])
        assert approval['binding_digest']==review['binding_digest']
        assert approval['approved_by']==setup['authority']['operator']
        assert approval['expires_at_ms']-approval['issued_at_ms']==60000
    config.write_text('invalid SENTINEL_OPERATOR_CONFIG')
    failed=run('src/executor/operator.kujo',env,False)
    assert failed=={'ok':False,'code':'operator_failed'}
print('Operator: scope, review binding, changed definition, expiry, durable separate-process grant, replay denial and normalized errors passed')
