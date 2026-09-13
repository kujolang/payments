"""Separate operator/worker processes; synthetic provider never moves money."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2]
KUJO=os.environ['KUJO_BIN']

def run(script,env):
    p=subprocess.run([KUJO,'run',script,'--interpreter'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert p.returncode==0,(p.stdout,p.stderr)
    return json.loads(p.stdout)

for scenario in ('crash_after_charge','concurrent','incident_pause'):
    with tempfile.TemporaryDirectory(prefix='payments-worker-') as directory:
        root=Path(directory)
        v=json.loads((ROOT/'tests/fixtures/domain.json').read_text())
        time_ms=int(time.time()*1000)
        v['intent']['expires_at_ms']=time_ms+120000
        v['snapshot']['expires_at_ms']=time_ms+120000
        v['capabilities'].update(observed_at_ms=time_ms,valid_until_ms=time_ms+120000)
        fixture=root/'fixture.json';fixture.write_text(json.dumps(v))
        database=root/'payments.db'
        env={**os.environ,'PAYMENTS_TEST_DB':str(database),'PAYMENTS_WORKER_FIXTURE':str(fixture),'PAYMENTS_FIXTURE_BEHAVIOR':'success'}
        for _ in range(2):
            pending=run('tests/worker.kujo',env)
            assert pending['ok'] and pending['result']['status']=='awaiting_authorization',pending
        with sqlite3.connect(str(database)+'.processor') as db:
            assert db.execute('SELECT count(*) FROM fixture_authorizations').fetchone()[0]==1
            assert db.execute('SELECT count(*) FROM fixture_charges').fetchone()[0]==0
        config=root/'operator.json'
        config.write_text(json.dumps({'schema':'kujo.payment-operator/v1','database':str(database),'authority':{'payer':v['intent']['principal'],'operator':{'type':'human','id':'operator_1','tenant_id':'tenant_1'},'issuer_ref':'local-operator-v1','ttl_ms':60000}}))
        config.chmod(0o600)
        operator={**env,'PAYMENTS_OPERATOR_CONFIG':str(config),'PAYMENTS_EXECUTION_ID':'exec_1','PAYMENTS_OPERATOR_ACTION':'review'}
        review=run('src/executor/operator.kujo',operator)
        operator.update(PAYMENTS_OPERATOR_ACTION='approve',PAYMENTS_REVIEW_DIGEST=review['binding_digest'])
        assert run('src/executor/operator.kujo',operator)['status']=='ready'
        if scenario=='incident_pause':
            control=root/'control.json'
            control.write_text(json.dumps({'schema':'kujo.payment-control/v1','database':str(database),'actor_ref':'admin'}))
            command={**env,'PAYMENTS_CONTROL_CONFIG':str(control),'PAYMENTS_CONTROL_ACTION':'pause','PAYMENTS_CONTROL_REVISION':'0'}
            assert run('src/executor/control.kujo',command)['control']['mode']=='paused'
            deferred=run('tests/worker.kujo',env)
            assert deferred=={'ok':False,'code':'execution_deferred'},deferred
            with sqlite3.connect(database) as db:
                assert db.execute('SELECT count(*) FROM ability_calls').fetchone()[0]==0
                assert db.execute('SELECT consumed FROM approvals').fetchone()[0]==0
            command.update(PAYMENTS_CONTROL_ACTION='resume',PAYMENTS_CONTROL_REVISION='1')
            assert run('src/executor/control.kujo',command)['control']['mode']=='active'
        if scenario=='crash_after_charge':
            # Adapter exception after the independently committed charge, then a
            # fresh process observes it. SIGKILL coverage lives in concurrency_test.
            unknown=run('tests/worker.kujo',{**env,'PAYMENTS_FIXTURE_BEHAVIOR':'throw_after'})
            assert unknown['result']['status']=='reconciliation_required',unknown
            control=root/'control.json'
            control.write_text(json.dumps({'schema':'kujo.payment-control/v1','database':str(database),'actor_ref':'admin'}))
            command={**env,'PAYMENTS_CONTROL_CONFIG':str(control),'PAYMENTS_CONTROL_ACTION':'pause','PAYMENTS_CONTROL_REVISION':'0'}
            assert run('src/executor/control.kujo',command)['control']['mode']=='paused'
            # The normal worker must reconcile an earlier charge while paused.
        else:
            with ThreadPoolExecutor(max_workers=4) as pool:
                outputs=list(pool.map(lambda _:run('tests/worker.kujo',env),range(4)))
            assert any(x.get('result',{}).get('status')=='succeeded' for x in outputs),outputs
        for _ in range(2):
            settled=run('tests/worker.kujo',env)
            assert settled['result']['status']=='succeeded',settled
        with sqlite3.connect(str(database)+'.processor') as db:
            assert db.execute('SELECT count(*) FROM fixture_charges').fetchone()[0]==1
        with sqlite3.connect(database) as db:
            assert db.execute('SELECT consumed FROM approvals').fetchone()[0]==1
        for path in root.iterdir():
            if path.is_file():
                data=path.read_bytes()
                assert b'SENTINEL_SPT' not in data and b'SENTINEL_PROVIDER_SECRET' not in data
print('Bounded worker: asynchronous operator grant, native authorization dedupe, four-process dispatch race, post-charge reconciliation and terminal replay passed')
