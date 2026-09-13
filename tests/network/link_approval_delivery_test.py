"""Only the private outbox/operator sink may contain the approval URL sentinel."""
from concurrent.futures import ThreadPoolExecutor
import json,os,sqlite3,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];KUJO=os.environ['KUJO_BIN']
def run(env,action,mode='success'):
    p=subprocess.run([KUJO,'run','tests/link_approval_delivery.kujo','--interpreter'],cwd=ROOT,env={**env,'PAYMENTS_DELIVERY_ACTION':action,'PAYMENTS_DELIVERY_MODE':mode},capture_output=True,text=True,timeout=20)
    assert 'SENTINEL' not in p.stdout+p.stderr,'secret in caller output'
    assert p.returncode==0,(p.stdout,p.stderr)
    return json.loads(p.stdout)
modes=['success','merchant_origin','userinfo','http','fragment','html','backslash','changed_amount','changed_currency','changed_id','changed_network','approved','expired','tenant','callback_throw','callback_object','callback_after_write','callback_late','callback_rollback','delivery_tenant','delivery_principal','delivery_execution','delivery_amount','delivery_expired']
for mode in modes:
    with tempfile.TemporaryDirectory(prefix='payments-private-approval-') as directory:
        root=Path(directory);auth=root/'auth.db';outbox=root/'outbox.db';sink=root/'operator.json';sink.touch(mode=0o600)
        env={**os.environ,'PAYMENTS_DELIVERY_AUTH':str(auth),'PAYMENTS_DELIVERY_OUTBOX':str(outbox),'PAYMENTS_DELIVERY_SINK':str(sink),'PAYMENTS_DELIVERY_CLOCK':str(root/'clock')}
        assert run(env,'init')['ok'];outbox.chmod(0o600)
        if mode=='success':
            with ThreadPoolExecutor(max_workers=4) as pool: stages=list(pool.map(lambda _:run(env,'stage'),range(4)))
            assert all(x==stages[0] and x['ok'] for x in stages)
        if mode=='success':
            assert run(env,'stage','changed_url')['ok'] is False
        result=run(env,'deliver',mode)
        assert result['ok']==(mode=='success'),(mode,result)
        staged=mode=='success' or mode.startswith(('callback_','delivery_'))
        with sqlite3.connect(outbox) as db:
            rows=db.execute('SELECT approval_url FROM link_approval_outbox_v2').fetchall()
            assert len(rows)==int(staged)
            if rows:assert rows[0][0]=='https://approve.example/consent/SENTINEL_APPROVAL_URL'
        assert ('SENTINEL_APPROVAL_URL' in sink.read_text())==(mode in ['success','callback_after_write','callback_late','callback_rollback'])
        assert sink.stat().st_mode&0o777==0o600
        for f in root.iterdir():
            data=f.read_bytes()
            for secret in ['SENTINEL_SPT','SENTINEL_LPT','SENTINEL_PAN','SENTINEL_CVC','SENTINEL_OAUTH','SENTINEL_REFRESH','SENTINEL_API_SECRET','SENTINEL_EXCEPTION']:
                assert secret.encode() not in data,(mode,f.name,'unselected provider secret persisted')
            if not f.name.startswith('outbox.db') and f!=sink: assert b'SENTINEL' not in data,(mode,f.name,'URL escaped private sink')
print('Private Link approval delivery: 24 binding/URL/callback cases, four-process staging, persistent private operator sink and zero unselected-secret/caller-output leakage passed')

with tempfile.TemporaryDirectory(prefix='payments-retired-delivery-') as directory:
    root=Path(directory);sink=root/'operator.json';sink.touch(mode=0o600)
    env={**os.environ,'PAYMENTS_DELIVERY_AUTH':str(root/'auth.db'),'PAYMENTS_DELIVERY_OUTBOX':str(root/'outbox.db'),'PAYMENTS_DELIVERY_SINK':str(sink),'PAYMENTS_DELIVERY_CLOCK':str(root/'clock')}
    assert run(env,'init')['ok'];staged=run(env,'stage');assert staged['ok']
    assert run(env,'retire')=={'ok':True,'retired':1}
    assert run(env,'stage')['ok'] is False
    assert run({**env,'PAYMENTS_DELIVERY_REF':staged['delivery_ref']},'deliver_retired')['ok'] is False
    assert sink.read_text()==''
print('Retired approval URL cannot be restaged or delivered after restart/clock rollback')
