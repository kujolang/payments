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
 return {**os.environ,'PAYMENTS_TEST_DB':str(root/'state.db'),'PAYMENTS_TEST_REQUEST':str(path),'PAYMENTS_TEST_MODE':mode,'PAYMENTS_TEST_STOP':stop,'PAYMENTS_TEST_MARKER':str(root/'marker'),'PAYMENTS_PRIVATE_SENTINEL':SECRET,'PAYMENTS_TEST_RELEASE':''}
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

# Recovery is a new intake operation with the same business identity, never
# reopening the old Ability invocation. The original may still resume later.
for stop in ('before_intake','after_intake','before_complete'):
 for terminate_original in (False,True):
  with tempfile.TemporaryDirectory(prefix='payments-intake-recovery-') as directory:
   root=Path(directory);marker=root/'marker';release=root/'release'
   env=environment(root,REQUEST,stop=stop);env['PAYMENTS_TEST_RELEASE']=str(release)
   original=subprocess.Popen([KUJO,'run','tests/interrupted_gateway_fixture.kujo','--interpreter'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   try:
    deadline=time.monotonic()+15
    while not marker.exists():
     assert original.poll() is None and time.monotonic()<deadline,'original checkpoint unavailable'
     time.sleep(.02)
    if terminate_original:
     original.kill();out,err=original.communicate(timeout=5)
     assert original.returncode==-9 and SECRET not in out+err
    prior=run(root)
    assert not prior['ok']
    if stop=='before_intake':assert 'result' not in prior
    def recover(index):
     request=copy(REQUEST);request['idempotency_key']='recovery-'+str(index)
     return run(root,request)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(recover,range(4)))
    assert all(x['ok'] for x in results),results
    ids={x['result']['execution_id'] for x in results};assert len(ids)==1
    with sqlite3.connect(root/'state.db') as db:
     before=list(db.execute('SELECT execution_id,intent_json,expires_at_ms,claimed FROM executions'))
     assert len(before)==1 and before[0][3]==0
     assert db.execute('SELECT count(*) FROM approvals').fetchone()[0]==0
     assert db.execute('SELECT count(*) FROM ability_calls WHERE receipt_json IS NULL').fetchone()[0]==1
    for field,value in [('purpose','changed'),('payee_ref','other'),('amount',{'mode':'maximum','minor':5501,'currency':'USD'}),('expires_in_ms',10000)]:
     changed=copy(REQUEST);changed['idempotency_key']='changed-'+field;changed['input'][field]=value
     assert not run(root,changed)['ok'],field
    if not terminate_original:
     if stop!='before_complete':time.sleep(2.1)  # exceed the declared handler timeout deliberately
     release.write_text('resume')
     out,err=original.communicate(timeout=15)
     assert original.returncode==0 and SECRET not in out+err,(out,err)
     resumed=json.loads(out);assert resumed['result']['execution_id'] in ids,resumed
     if stop=='before_complete':assert resumed['ok'],resumed
     else:assert not resumed['ok'] and resumed['code']=='operation_receipt_failed',resumed
    else:
     old=run(root);assert not old['ok'],old
     if stop=='before_intake':assert 'result' not in old,old
     else:assert old['result']['execution_id'] in ids,old
    with sqlite3.connect(root/'state.db') as db:
     assert list(db.execute('SELECT execution_id,intent_json,expires_at_ms,claimed FROM executions'))==before,'recovery replaced terms or expiry'
     assert db.execute('SELECT count(*) FROM approvals').fetchone()[0]==0
     assert db.execute('SELECT count(*) FROM ability_calls WHERE receipt_json IS NULL').fetchone()[0]==int(terminate_original)
   finally:
    if original.poll() is None:original.kill();original.communicate(timeout=5)
print('Intake recovery: three interruption boundaries, killed and live originals, four fresh-key contenders, unchanged business terms/expiry, no approval or financial claim and safe late original completion passed')
