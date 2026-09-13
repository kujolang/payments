"""Authenticated cancellation, explicit inspect v2, mixed v1 compatibility and real claim races."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import hashlib,hmac,json,os,socket,sqlite3,subprocess,tempfile,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];KUJO=os.environ['KUJO_BIN']
PAYER={'type':'user','id':'user_1','tenant_id':'tenant_1'}
TOKENS=['A'*64,'B'*64,'C'*64]
def call(port,operation,input,key=None,token=0):
 body={'operation':operation,'input':input}
 if key is not None:body['idempotency_key']=key
 request=urllib.request.Request(f'http://127.0.0.1:{port}/v1/payments',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+TOKENS[token]})
 try:response=urllib.request.urlopen(request,timeout=15)
 except urllib.error.HTTPError as e:response=e
 with response:return response.status,json.loads(response.read())
@contextmanager
def service(root,database):
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 credentials=[{'verifier':hmac.new(t.encode(),b'kujo.payments.transport/v1',hashlib.sha256).hexdigest(),'principal':PAYER if i!=2 else {**PAYER,'tenant_id':'other'},'operations':['request','inspect'] if i==1 else ['request','inspect','inspect_revision','cancel'],'disabled':False,'expires_at_ms':4102444800000} for i,t in enumerate(TOKENS)]
 config=root/f'config-{port}.json';config.write_text(json.dumps({'schema':'kujo.payment-service/v1','bind':'127.0.0.1','port':port,'database':str(database),'namespace':'cancel-fixture','currency_table':{'version':'fixture-v1','exponents':{'USD':2}},'credentials':credentials}));config.chmod(0o600)
 p=subprocess.Popen([KUJO,'run','src/executor/gateway.kujo','--interpreter'],cwd=ROOT,env={**os.environ,'PAYMENTS_SERVICE_CONFIG':str(config)},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  deadline=time.monotonic()+15
  while True:
   try:call(port,'inspect',{'execution_id':'startup'});break
   except OSError:
    assert p.poll() is None and time.monotonic()<deadline,'service startup failed';time.sleep(.03)
  yield port
 finally:
  p.terminate()
  try:out,err=p.communicate(timeout=10)
  except subprocess.TimeoutExpired:p.kill();out,err=p.communicate(timeout=10)
  assert all(t not in out+err for t in TOKENS),'credential in service output'
  assert p.returncode in [0,-15],(out,err)
def fixture(db,id,mode):
 p=subprocess.run([KUJO,'run','tests/cancellation_fixture.kujo','--interpreter'],cwd=ROOT,env={**os.environ,'PAYMENTS_TEST_DB':str(db),'PAYMENTS_CANCEL_ID':id,'PAYMENTS_CANCEL_MODE':mode},capture_output=True,text=True,timeout=20)
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
def request(port,name):
 _,r=call(port,'request',{'purchase_ref':name,'payee_ref':'merchant_1','amount':{'mode':'maximum','minor':5500,'currency':'USD'},'purpose':'Synthetic cancellation','payment_profile':'default','expires_in_ms':120000},name)
 assert r['ok'];return r['result']['execution_id']
def status(port,id):
 _,r=call(port,'inspect_revision',{'execution_id':id});assert r['ok'];return r['result']
def cancel(port,id,revision,key):return call(port,'cancel',{'execution_id':id,'expected_revision':revision},key)[1]
with tempfile.TemporaryDirectory(prefix='payments-cancel-') as directory:
 root=Path(directory);db=root/'payments.db'
 with service(root,db) as port:
  # Validate the expanded operation list, including nonadjacent duplicates.
  installed=json.loads((root/f'config-{port}.json').read_text())
  for operations in [['request','inspect','request'],['request','inspect_revision','cancel','cancel'],['execute'],[]]:
   invalid=json.loads(json.dumps(installed));invalid['credentials'][0]['operations']=operations
   path=root/'invalid-config.json';path.write_text(json.dumps(invalid));path.chmod(0o600)
   rejected=subprocess.run([KUJO,'run','src/executor/gateway.kujo','--interpreter'],cwd=ROOT,env={**os.environ,'PAYMENTS_SERVICE_CONFIG':str(path)},capture_output=True,text=True,timeout=10)
   assert rejected.returncode!=0
   assert all(t not in rejected.stdout+rejected.stderr for t in TOKENS)
  id=request(port,'first');assert status(port,id)['revision']==0
  old=call(port,'inspect',{'execution_id':id})[1]['result'];assert set(old)=={'execution_id','status','next_action','receipt_ref'}
  for op,input in [('cancel',{'execution_id':id,'expected_revision':0}),('inspect_revision',{'execution_id':id})]:assert call(port,op,input,'denied' if op=='cancel' else None,1)[0]==403
  assert call(port,'inspect_revision',{'execution_id':id},token=2)[1]['ok'] is False
  assert call(port,'cancel',{'execution_id':id,'expected_revision':0},'foreign',2)[1]['ok'] is False
  for revision in [False,0.0,-1,9007199254740992]:assert cancel(port,id,revision,'invalid')['ok'] is False
  assert call(port,'inspect_revision',{'execution_id':id},'bad-key')[1]['ok'] is False
  assert cancel(port,id,0,'')['ok'] is False
  first=cancel(port,id,0,'cancel-first');assert first['ok'] and first['result']['status']=='closed'
  assert cancel(port,id,0,'cancel-first')==first
  assert cancel(port,id,1,'cancel-first')['ok'] is False
  other=request(port,'other');assert cancel(port,other,0,'cancel-first')['ok'] is False;assert status(port,other)['status']=='awaiting_authorization'
  assert status(port,id)['revision']==1
  id=request(port,'stale');assert fixture(db,id,'ready')['ok'];assert status(port,id)['revision']==2
  assert cancel(port,id,0,'stale-key')['ok'] is False
  assert cancel(port,id,2,'stale-key')['ok'] is False # changed retry cannot reopen a keyed call
  assert cancel(port,id,2,'fresh-key')['ok']
  assert fixture(db,id,'pause')['ok'];paused=request(port,'paused');assert cancel(port,paused,0,'cancel-paused')['ok'];assert fixture(db,id,'resume')['ok']
  for index in range(8):
   id=request(port,'race-'+str(index));assert fixture(db,id,'ready')['ok'];revision=status(port,id)['revision']
   with ThreadPoolExecutor(max_workers=8) as pool:
    futures=[pool.submit(fixture,db,id,'claim') for _ in range(4)]+[pool.submit(cancel,port,id,revision,'race-key-'+str(index)) for _ in range(4)]
    results=[f.result() for f in futures]
   wins=sum(r['won'] for r in results[:4]);assert wins<=1
   current=status(port,id);assert (current['status']=='closed')==(wins==0),(wins,current)
   with sqlite3.connect(db) as connection:
    claimed=connection.execute('SELECT claimed FROM executions WHERE execution_id=?',(id,)).fetchone()[0];assert claimed==wins
   if wins:assert not any(r['ok'] for r in results[4:])
   else:assert any(r['ok'] for r in results[4:])
  # Force a known winning claim, then prove every cancellation is refused.
  id=request(port,'claimed');assert fixture(db,id,'ready')['ok'];assert fixture(db,id,'claim')['won'];assert cancel(port,id,2,'post-claim')['ok'] is False
  with sqlite3.connect(str(db)+'.processor') as ledger:assert ledger.execute('SELECT max(n) FROM (SELECT count(*) AS n FROM calls GROUP BY execution_id)').fetchone()[0]==1
  archived=request(port,'archive')
  clone=root/'recovery'
  p=subprocess.run(['python3','scripts/maintenance/recovery_snapshot.py','--source',str(db),'--output-dir',str(clone)],cwd=ROOT,capture_output=True,text=True,timeout=40);assert p.returncode==0,(p.stdout,p.stderr)
  with service(root,clone/'payments.db') as archived_port:assert cancel(archived_port,archived,0,'archive-cancel')['ok'] is False
  assert status(port,archived)['status']=='awaiting_authorization'
 print('Cancellation: authenticated HTTP, explicit inspect v2, v1 output unchanged, strict revisions, scoped bound replay, pause support, eight real cancel/claim races, post-claim and quarantined-copy denial passed')
