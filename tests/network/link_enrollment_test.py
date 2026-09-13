"""Bounded private enrollment with synthetic OAuth and a separate credential vault."""
from concurrent.futures import ThreadPoolExecutor
import json,os,sqlite3,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
COMMAND=[os.environ['KUJO_BIN'],'run','tests/link_enrollment.kujo','--interpreter']
def call(env,action,now=1000,mode=''):
 p=subprocess.run(COMMAND,cwd=ROOT,env={**env,'PAYMENTS_ENROLL_ACTION':action,'PAYMENTS_ENROLL_NOW':str(now),'PAYMENTS_ENROLL_MODE':mode},capture_output=True,text=True,timeout=20)
 assert p.returncode==0,(action,p.stdout,p.stderr)
 assert 'SENTINEL' not in p.stdout+p.stderr,'secret in process output'
 return json.loads(p.stdout)
def environment(root):return {**os.environ,'PAYMENTS_ENROLL_DB':str(root/'enrollment.db'),'PAYMENTS_ENROLL_MARKER':str(root/'marker'),'PAYMENTS_ENROLL_STOP':'','PAYMENTS_ENROLL_ID':'enrollment_1'}
def counts(env):
 with sqlite3.connect(env['PAYMENTS_ENROLL_DB']+'.provider') as db:return dict(db.execute('SELECT phase,count(*) FROM calls GROUP BY phase'))
def row(env):
 with sqlite3.connect(env['PAYMENTS_ENROLL_DB']) as db:
  db.row_factory=sqlite3.Row
  return dict(db.execute('SELECT * FROM link_enrollment_v1').fetchone())
with tempfile.TemporaryDirectory(prefix='payments-enrollment-') as directory:
 env=environment(Path(directory));assert call(env,'forms')['ok']
 with ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(lambda _:call(env,'start'),range(4)))
 assert all(x['ok'] for x in values) and counts(env)=={'start':1}
 assert call(env,'inspect')['state']=='pending'
 assert not call({**env,'PAYMENTS_ENROLL_ID':'enrollment_2'},'start')['ok'],'same credential target cannot initiate twice'
 assert call(env,'deliver')['ok']
 assert not call(env,'api')['ok']
 assert not call(env,'inspect',mode='wrong_binding')['ok']
 assert not call(env,'start',mode='wrong_origin')['ok']
 assert call(env,'poll',5999)['state']=='pending' and counts(env).get('poll',0)==0
 assert call(env,'poll',6000,'pending')['next_poll_at_ms']==11000
 assert call(env,'poll',11000,'slow_down')['next_poll_at_ms']==21000
 assert call(env,'poll',20999)['state']=='pending' and counts(env)['poll']==2
 assert call(env,'poll',21000,'slow_down')['next_poll_at_ms']==36000
 with ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(lambda _:call(env,'poll',36000),range(4)))
 assert call(env,'inspect')['state']=='received' and counts(env)['poll']==4
 stored=row(env);assert stored['device_code'] is None and stored['operator_json'] is None and 'SENTINEL_EXTRA' not in stored['tokens_json']
 assert not call(env,'deliver',36000)['ok']
 with ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(lambda _:call(env,'accept',36000),range(4)))
 assert call(env,'inspect')['state']=='accepted' and counts(env)['accept']==1
 assert call(env,'api',36000)['ok'] and counts(env)['api']==1
 assert not call(env,'api',36000,'wrong_binding')['ok'] and counts(env)['api']==1
 assert row(env)['tokens_json'] is None
 with sqlite3.connect(env['PAYMENTS_ENROLL_DB']+'.vault') as db:
  assert db.execute('SELECT state,generation,expires_at_ms FROM link_credentials_v1').fetchone()==('active',0,96000)
 before=counts(env)
 for action in ('start','poll','accept'):assert call(env,action,37000)['state']=='accepted'
 assert counts(env)==before
for action,mode,state in [('start','throw','unknown'),('start','url','unknown'),('start','interval','unknown'),('start','abandon','abandoned'),('poll','throw','unknown'),('poll','scope','unknown'),('poll','details','unknown'),('poll','rejected','rejected'),('poll','expired','expired'),('poll','abandon','abandoned'),('accept','deny','unknown'),('deliver','abandon','abandoned'),('deliver','throw','pending'),('start','write_failure','unknown'),('poll','write_failure','unknown'),('accept','write_failure','accepting'),('start','late','unknown'),('start','rollback','unknown'),('poll','late','unknown'),('poll','rollback','unknown'),('accept','late','unknown'),('accept','rollback','unknown')]:
 with tempfile.TemporaryDirectory(prefix='payments-enrollment-fault-') as directory:
  env=environment(Path(directory))
  if action!='start':assert call(env,'start')['state']=='pending'
  if action=='accept':assert call(env,'poll',6000)['state']=='received'
  result=call(env,action,6000 if action in ('poll','accept') else 1000,mode)
  assert call(env,'inspect')['state']==state,(action,mode,result)
  assert not call(env,'api',7000)['ok']
  if state!='pending':assert all(row(env)[x] is None for x in ('device_code','operator_json','tokens_json'))
  before=counts(env)
  if state!='pending':
   for retry in ('start','poll','accept'):call(env,retry,7000)
   assert counts(env)==before
for stage in ('start','poll','accept','after_install'):
 with tempfile.TemporaryDirectory(prefix='payments-enrollment-kill-') as directory:
  root=Path(directory);env=environment(root)
  if stage!='start':call(env,'start')
  if stage in ('accept','after_install'):call(env,'poll',6000)
  action='accept' if stage=='after_install' else stage
  child=subprocess.Popen(COMMAND,cwd=ROOT,env={**env,'PAYMENTS_ENROLL_ACTION':action,'PAYMENTS_ENROLL_NOW':'6000' if action!='start' else '1000','PAYMENTS_ENROLL_MODE':'','PAYMENTS_ENROLL_STOP':stage},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  try:
   deadline=time.monotonic()+15
   while not (root/'marker').exists():
    assert child.poll() is None and time.monotonic()<deadline
    time.sleep(.02)
   child.kill();out,err=child.communicate(timeout=5);assert 'SENTINEL' not in out+err
  finally:
   if child.poll() is None:child.kill();child.communicate(timeout=5)
  expected='initiating' if stage=='start' else 'polling' if stage=='poll' else 'accepting'
  assert call(env,'inspect')['state']==expected
  assert not call(env,'api',7000)['ok'],'active vault alone must not publish interrupted enrollment'
  before=counts(env)
  for retry in ('start','poll','accept'):call(env,retry,7000)
  assert counts(env)==before,'crash caused native re-entry'
  assert call(env,'abandon')['state']=='abandoned'
  assert all(row(env)[x] is None for x in ('device_code','operator_json','tokens_json'))
for action,now in [('poll',121000),('accept',66000)]:
 with tempfile.TemporaryDirectory(prefix='payments-enrollment-expire-') as directory:
  env=environment(Path(directory));call(env,'start',mode='default_interval')
  if action=='accept':call(env,'poll',6000)
  assert call(env,action,now)['state']=='expired'
  assert all(row(env)[x] is None for x in ('device_code','operator_json','tokens_json'))
print('Private Link enrollment: timed pending/slow_down, private delivery, vault acceptance and guarded API publication, four-way races, 22 fault cases, four SIGKILL boundaries, expiry, no native re-entry or secret output passed')
