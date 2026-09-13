"""Real optional SDK/MCP/Dispatch processes against bounded synthetic error responses."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,os,subprocess,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TOKEN='r'*64;SECRET='SENTINEL_RECOVERY_PRIVATE_ERROR'
state={'case':'valid','requests':0,'inspects':0}
class Service(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  assert self.path=='/v1/payments' and self.headers['Authorization']=='Bearer '+TOKEN
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  request=body['operation']=='request';state['requests' if request else 'inspects']+=1
  summary={'execution_id':'exec_recovery','status':'succeeded' if request else 'awaiting_authorization','next_action':'inspect_receipt' if request else 'await_authorization','receipt_ref':'receipt:stale' if request else None}
  if not request:
   assert body['input']=={'execution_id':'exec_recovery'}
   if state['case']=='wrong_status':summary['execution_id']='different_execution'
  payload={'ok':False,'code':SECRET,'result':summary} if request else {'ok':True,'result':summary}
  if request:
   if state['case']=='extra_result':summary['provider_token']=SECRET
   if state['case']=='extra_envelope':payload['provider_token']=SECRET
   if state['case']=='no_result':del payload['result']
  raw=json.dumps(payload).encode();code=409 if request else 200
  if request and state['case']=='unauthorized':code=401
  if request and state['case']=='server_error':code=500
  self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
server=ThreadingHTTPServer(('127.0.0.1',0),Service);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 with tempfile.TemporaryDirectory(prefix='payments-recovery-projections-') as directory:
  root=Path(directory)
  env={**os.environ,'PAYMENTS_CLIENT_ENDPOINT':f'http://127.0.0.1:{server.server_port}/v1/payments','PAYMENTS_CLIENT_TOKEN':TOKEN,'PAYMENTS_LOCAL_FIXTURE':'true','KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS':'true','PAYMENTS_PRIVATE_SENTINEL':SECRET,'PAYMENTS_DISPATCH_RUN_ID':'','PAYMENTS_PURCHASE_JSON':json.dumps({'purchase_ref':'recovery-purchase','payee_ref':'merchant','amount':{'mode':'exact','minor':100,'currency':'USD'},'purpose':'Private purchase purpose','payment_profile':'default','expires_in_ms':60000})}
  for case in ['valid','wrong_status','extra_result','extra_envelope','no_result','unauthorized','server_error']:
   state['case']=case;valid=case=='valid';observed=case in ['valid','wrong_status']
   env.update(PAYMENTS_EXPECT_OBSERVATION='true' if observed else 'false',PAYMENTS_WRONG_STATUS='true' if case=='wrong_status' else 'false')
   for integration,command in [('mcp',['node','examples/mcp/recovery_conformance.mjs']),('sdk',['python3','examples/agents-sdk/run.py']),('dispatch',['python3','examples/dispatch/run.py'])]:
    output=root/(case+'-'+integration);env['PAYMENTS_DISPATCH_OUTPUT']=str(output)
    before=(state['requests'],state['inspects'])
    p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
    assert TOKEN not in p.stdout+p.stderr and SECRET not in p.stdout+p.stderr,(case,integration)
    assert (p.returncode==0)==(integration=='mcp' or valid),(case,integration,p.stdout,p.stderr)
    assert state['requests']==before[0]+1,'no automatic purchase retry'
    assert state['inspects']==before[1]+(1 if observed else 0),(case,integration,state,before)
    if p.returncode==0:
     result=json.loads(p.stdout)
     if integration=='mcp':assert result['request_is_error'] and result['observation_retained']==observed
     if integration=='sdk':assert result['status']=='awaiting_authorization'
     if integration=='dispatch':
      assert result['workflow_status']=='paused' and result['payment']['status']=='awaiting_authorization'
      saved=json.loads((output/result['run_id']/'state.json').read_text());assert saved['input']=={'execution_id':'exec_recovery'}
    if output.exists():
     for path in output.rglob('*'):
      if path.is_file():
       for value in [TOKEN,SECRET,'Private purchase purpose','recovery-purchase','"minor"']:assert value.encode() not in path.read_bytes()
 print('Recovery projections: 21 real SDK/MCP/Dispatch runs, retained error observations, fresh status, wrong-ID/unsafe-result denial, no intake retry, compact private state passed')
finally:server.shutdown();server.server_close();thread.join(timeout=3)
