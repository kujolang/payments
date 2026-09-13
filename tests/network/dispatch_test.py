"""Actual pinned Dispatch persistence/restart against a synthetic HTTP payment service."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
ROOT=Path(__file__).resolve().parents[2]
TOKEN='dispatch-fixture-'+'a'*48
PRIVATE='SENTINEL_DISPATCH_UNRELATED_PROVIDER_SECRET'
state={'status':'awaiting_authorization','requests':[],'inspects':0,'fail':False,'wrong_id':False}
class Service(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        assert self.path=='/v1/payments'
        assert self.headers['Authorization']=='Bearer '+TOKEN
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if body['operation']=='request': state['requests'].append(body)
        else:
            assert body=={'operation':'inspect','input':{'execution_id':'exec_dispatch'}}
            state['inspects']+=1
        summary={'execution_id':'exec_wrong' if state['wrong_id'] else 'exec_dispatch','status':state['status'],'next_action':'inspect_receipt' if state['status']=='succeeded' else 'await_authorization','receipt_ref':'receipt:dispatch' if state['status']=='succeeded' else None}
        payload=json.dumps({'ok':True,'result':summary} if not state['fail'] else {'ok':False,'code':PRIVATE}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
service=ThreadingHTTPServer(('127.0.0.1',0),Service)
thread=threading.Thread(target=service.serve_forever,daemon=True);thread.start()
try:
    with tempfile.TemporaryDirectory(prefix='payments-dispatch-test-') as directory:
        output=Path(directory)/'workflows'
        env={**os.environ,'PAYMENTS_CLIENT_ENDPOINT':f'http://127.0.0.1:{service.server_port}/v1/payments','PAYMENTS_CLIENT_TOKEN':TOKEN,'PAYMENTS_LOCAL_FIXTURE':'true','PAYMENTS_DISPATCH_OUTPUT':str(output),'UNRELATED_PROVIDER_SECRET':PRIVATE,'DISPATCH_AUTO_APPROVE':'true','PAYMENTS_PURCHASE_JSON':json.dumps({'purchase_ref':'dispatch-order','payee_ref':'merchant','amount':{'mode':'exact','minor':100,'currency':'USD'},'purpose':'Fixture','payment_profile':'default','expires_in_ms':60000})}
        def run(run_id='',ok=True):
            result=subprocess.run(['python3','examples/dispatch/run.py'],cwd=ROOT,env={**env,'PAYMENTS_DISPATCH_RUN_ID':run_id},capture_output=True,text=True,timeout=40)
            assert TOKEN not in result.stdout+result.stderr and PRIVATE not in result.stdout+result.stderr
            assert (result.returncode==0)==ok,(result.stdout,result.stderr)
            return json.loads(result.stdout)
        first=run();assert first['workflow_status']=='paused',first
        rid=first['run_id'];saved=output/rid/'state.json'
        persisted=json.loads(saved.read_text());assert persisted['input']=={'execution_id':'exec_dispatch'}
        second=run(rid);assert second['workflow_status']=='paused'
        assert len(state['requests'])==1,'resume must not resubmit intake'
        assert state['inspects']==2,'one fresh read per pending wakeup; no polling loop'
        before=hashlib.sha256(saved.read_bytes()).hexdigest()
        state['fail']=True;assert run(rid,False)['ok'] is False
        assert hashlib.sha256(saved.read_bytes()).hexdigest()==before,'failed status read cannot release checkpoint'
        state['fail']=False;state['wrong_id']=True
        assert run(rid,False)['ok'] is False
        assert hashlib.sha256(saved.read_bytes()).hexdigest()==before,'wrong execution must not release checkpoint'
        state['wrong_id']=False
        for status in ['ready','executing','reconciliation_required']:
            state['status']=status
            assert run(rid)['workflow_status']=='paused',status
        state['status']='succeeded'
        completed=run(rid);assert completed['workflow_status']=='completed',completed
        persisted=json.loads(saved.read_text());assert persisted['final_output']['status']=='succeeded'
        assert persisted['final_output']['receipt_ref']=='receipt:dispatch'
        assert run(rid)['workflow_status']=='completed'
        assert len(state['requests'])==1
        # A separate observer of a closed payment completes its workflow, but
        # its financial output must remain closed, never succeeded.
        state['status']='closed'
        env['PAYMENTS_PURCHASE_JSON']=env['PAYMENTS_PURCHASE_JSON'].replace('dispatch-order','closed-order')
        closed=run();assert closed['workflow_status']=='completed' and closed['payment']['status']=='closed'
        closed_state=json.loads((output/closed['run_id']/'state.json').read_text())
        assert closed_state['final_output']['status']=='closed' and closed_state['final_output']['receipt_ref'] is None
        for path in output.rglob('*'):
            if path.is_file():
                content=path.read_bytes()
                for sentinel in [TOKEN,PRIVATE,'dispatch-order','closed-order','"minor"']:
                    assert sentinel.encode() not in content,path
        print('Dispatch: persisted pause, separate-process pending/failed/success wakeups, fresh status, no intake replay and artifact suppression passed')
finally:
    service.shutdown();service.server_close();thread.join(timeout=3)
