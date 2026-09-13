"""Actual killed Ability invocations recover domain observations without re-entry."""
from concurrent.futures import ThreadPoolExecutor
import hashlib,hmac,json,os,socket,sqlite3,subprocess,tempfile,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
KUJO=os.environ['KUJO_BIN']
INPUT={'purchase_ref':'purchase','payee_ref':'merchant','amount':{'mode':'maximum','minor':5500,'currency':'USD'},'purpose':'Synthetic interruption','payment_profile':'default','expires_in_ms':120000}
REQUEST={'operation':'request','input':INPUT,'idempotency_key':'original-key'}
SECRET='fake-private-provider-sentinel-never-output'
def environment(root,request,mode='',stop=''):
 path=root/('request-'+str(time.time_ns())+'.json');path.write_text(json.dumps(request))
 return {**os.environ,'PAYMENTS_TEST_DB':str(root/'state.db'),'PAYMENTS_TEST_REQUEST':str(path),'PAYMENTS_TEST_MODE':mode,'PAYMENTS_TEST_STOP':stop,'PAYMENTS_TEST_MARKER':str(root/'marker'),'PAYMENTS_PRIVATE_SENTINEL':SECRET}
def run(root,request=REQUEST,mode=''):
 p=subprocess.run([KUJO,'run','tests/interrupted_gateway_fixture.kujo','--interpreter'],cwd=ROOT,env=environment(root,request,mode),capture_output=True,text=True,timeout=15)
 assert SECRET not in p.stdout+p.stderr
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
def kill(root,request,stop):
 marker=root/'marker';marker.unlink(missing_ok=True)
 p=subprocess.Popen([KUJO,'run','tests/interrupted_gateway_fixture.kujo','--interpreter'],cwd=ROOT,env=environment(root,request,stop=stop),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  deadline=time.monotonic()+15
  while not marker.exists():
   if p.poll() is not None:
    out,err=p.communicate(timeout=5);assert SECRET not in out+err;raise AssertionError((out,err))
   assert time.monotonic()<deadline,'checkpoint unavailable'
   time.sleep(.02)
  p.kill();out,err=p.communicate(timeout=5)
  assert p.returncode==-9 and SECRET not in out+err
 finally:
  if p.poll() is None:p.kill();p.communicate(timeout=5)
def journal(root):
 with sqlite3.connect(root/'state.db') as db:return list(db.iterdump())
def http_recovery(root,request):
 token='D'*64
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 settings={'schema':'kujo.payment-service/v1','bind':'127.0.0.1','port':port,'database':str(root/'state.db'),'namespace':'interrupted-fixture','currency_table':{'version':'fixture-v1','exponents':{'USD':2}},'credentials':[{'verifier':hmac.new(token.encode(),b'kujo.payments.transport/v1',hashlib.sha256).hexdigest(),'principal':{'type':'user','id':'user_1','tenant_id':'tenant_1'},'operations':['request','inspect','cancel'],'disabled':False,'expires_at_ms':4102444800000}]}
 path=root/'service.json';path.write_text(json.dumps(settings));path.chmod(0o600)
 p=subprocess.Popen([KUJO,'run','src/executor/gateway.kujo','--interpreter'],cwd=ROOT,env={**os.environ,'PAYMENTS_SERVICE_CONFIG':str(path)},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  deadline=time.monotonic()+15
  while True:
   wire=urllib.request.Request(f'http://127.0.0.1:{port}/v1/payments',data=json.dumps(request).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
   try:
    try:response=urllib.request.urlopen(wire,timeout=5)
    except urllib.error.HTTPError as error:response=error
    with response:
     assert response.status==409;return json.loads(response.read())
   except urllib.error.URLError:
    assert p.poll() is None and time.monotonic()<deadline
    time.sleep(.02)
 finally:
  p.terminate()
  try:out,err=p.communicate(timeout=5)
  except subprocess.TimeoutExpired:p.kill();out,err=p.communicate(timeout=5)
  assert token not in out+err and SECRET not in out+err
def copy(value):return json.loads(json.dumps(value))
with tempfile.TemporaryDirectory(prefix='payments-interrupted-') as directory:
 base=Path(directory)
 for stop in ['before_intake','after_intake','before_complete','before_cancel','after_cancel']:
  root=base/stop;root.mkdir()
  request=copy(REQUEST)
  if 'cancel' in stop:
   initial=run(root);assert initial['ok']
   request={'operation':'cancel','input':{'execution_id':initial['result']['execution_id'],'expected_revision':0},'idempotency_key':'cancel-key'}
  kill(root,request,stop)
  before=journal(root)
  with ThreadPoolExecutor(max_workers=4) as pool:recovered=list(pool.map(lambda _:run(root,request),range(4)))
  assert journal(root)==before,'observation changed the authoritative journal'
  for result in recovered:
   assert result['ok'] is False
   if stop=='before_intake':assert 'result' not in result
   else:
    assert result['code']=='operation_incomplete',result
    assert result['result']['status']==('closed' if stop=='after_cancel' else 'awaiting_authorization')
    observed=run(root,{'operation':'inspect','input':{'execution_id':result['result']['execution_id']}})
    assert observed['ok'] and observed['result']==result['result']
  if stop in ['after_intake','after_cancel']:assert http_recovery(root,request)==recovered[0]
  for mode in ['deny','approval_required','audit_fail','audit_completed_fail','unauthenticated']:
   denied=run(root,request,mode);assert not denied['ok'] and 'result' not in denied
  if 'cancel' in stop:
   changed=copy(request);changed['input']['expected_revision']=1
   assert 'result' not in run(root,changed)
   changed=copy(request);changed['input']['execution_id']='different'
   assert 'result' not in run(root,changed)
   assert 'result' not in run(root,request,'foreign')
  elif stop!='before_intake':
   for field,value in [('purpose','changed'),('purchase_ref','other'),('payee_ref','other'),('payment_profile','other'),('expires_in_ms',120000.0),('expires_in_ms',True),('shipping_profile','other'),('provider_preference','other')]:
    changed=copy(request);changed['input'][field]=value;assert 'result' not in run(root,changed)
   for amount in [{'mode':'maximum','minor':5500.0,'currency':'USD'},{'mode':'maximum','minor':5501,'currency':'USD'},{'mode':'maximum','minor':5500,'currency':'EUR'}]:
    changed=copy(request);changed['input']['amount']=amount;assert 'result' not in run(root,changed)
   assert 'result' not in run(root,request,'old_store')
  with sqlite3.connect(root/'state.db') as db:
   assert db.execute('SELECT count(*) FROM executions WHERE claimed!=0').fetchone()[0]==0
   assert db.execute('SELECT count(*) FROM ability_calls WHERE receipt_json IS NULL').fetchone()[0]>=1
print('Interrupted gateway: five real SIGKILL boundaries, four concurrent observation retries, unchanged journals, authenticated HTTP restart, exact terms, policy/audit/auth denial and no recreated action passed')
