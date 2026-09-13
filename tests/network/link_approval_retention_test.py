"""Real-process private-store upgrades and bounded irreversible URL retirement."""
from concurrent.futures import ThreadPoolExecutor
import json,os,sqlite3,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];KUJO=os.environ['KUJO_BIN']
BASE=json.loads((ROOT/'tests/fixtures/approval-outbox-v1.json').read_text())
COMMAND=[KUJO,'run','tests/link_approval_retention.kujo','--interpreter']
def env(path,action,now=2000,limit=1):return {**os.environ,'PAYMENTS_RETENTION_DB':str(path),'PAYMENTS_RETENTION_ACTION':action,'PAYMENTS_RETENTION_NOW':str(now),'PAYMENTS_RETENTION_LIMIT':str(limit)}
def run(path,action,now=2000,limit=1):
 p=subprocess.run(COMMAND,cwd=ROOT,env=env(path,action,now,limit),capture_output=True,text=True,timeout=20)
 assert 'SENTINEL' not in p.stdout+p.stderr,'private URL in caller output'
 assert p.returncode==0,(p.stdout,p.stderr)
 return json.loads(p.stdout)
def seed(path,count=3):
 with sqlite3.connect(path) as db:
  for d in BASE['definitions']:db.execute(d['sql'])
  db.execute('PRAGMA user_version=1')
  db.executemany('INSERT INTO link_approval_outbox_v1 VALUES(?,?,?,?,?,?)',((str(i),'execution','scope','digest','https://approve.example/SENTINEL_'+str(i),1000*(i+1)) for i in range(count)))
def state(path):
 with sqlite3.connect(path) as db:return list(db.iterdump()),db.execute('PRAGMA user_version').fetchone()[0]
with tempfile.TemporaryDirectory(prefix='payments-approval-retention-') as directory:
 root=Path(directory);path=root/'upgrade.db';seed(path);before=state(path)
 assert run(path,'open')['ok'] is False and state(path)==before
 assert run(path,'no_quiescence')['ok'] is False and state(path)==before
 with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:run(path,'migrate'),range(4)))
 assert all(r['ok'] for r in results) and sum(r['migrated'] for r in results)==1
 assert run(path,'legacy_open')['ok'] is False
 assert run(path,'open')['ok']
 with sqlite3.connect(path) as db:
  rows=db.execute('SELECT * FROM link_approval_outbox_v2 ORDER BY id').fetchall()
  assert rows==[(str(i),'execution','scope','digest','https://approve.example/SENTINEL_'+str(i),1000*(i+1),None) for i in range(3)]
 assert run(path,'retire',0)['retired']==0
 assert run(path,'retire',2000,0)['ok'] is False
 with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:run(path,'retire',2000),range(4)))
 assert all(r['ok'] for r in results) and sum(r['retired'] for r in results)==2
 assert run(path,'retire',0)['retired']==0 # clock rollback cannot resurrect URLs
 with sqlite3.connect(path) as db:
  rows=db.execute('SELECT id,approval_url,retired_at_ms FROM link_approval_outbox_v2 ORDER BY id').fetchall()
  assert rows==[('0',None,2000),('1',None,2000),('2','https://approve.example/SENTINEL_2',None)]
  for sql in ["DELETE FROM link_approval_outbox_v2 WHERE id='0'","UPDATE link_approval_outbox_v2 SET approval_url='replacement',retired_at_ms=NULL WHERE id='0'","UPDATE link_approval_outbox_v2 SET scope='other' WHERE id='2'","UPDATE link_approval_outbox_v2 SET approval_url=NULL,retired_at_ms=0 WHERE id='2'"]:
   try:db.execute(sql)
   except sqlite3.IntegrityError:pass
   else:raise AssertionError('identity/retirement guard missing')
 assert run(path,'retire',3000,1000)=={'ok':True,'retired':1}
 assert run(path,'retire',3000,1000)=={'ok':True,'retired':0}
 for mode in ['drift','future','disk_full']:
  fault=root/(mode+'.db');seed(fault,200)
  with sqlite3.connect(fault) as db:
   if mode=='drift':db.execute('DROP TRIGGER link_approval_outbox_permanent')
   if mode=='future':db.execute('PRAGMA user_version=3')
  before=state(fault);assert run(fault,'disk_full' if mode=='disk_full' else 'migrate')['ok'] is False
  assert state(fault)==before,'failed migration changed private state'
 crash=root/'crash.db';seed(crash,100000);before=state(crash)
 child=subprocess.Popen(COMMAND,cwd=ROOT,env=env(crash,'migrate'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  deadline=time.monotonic()+10
  while not Path(str(crash)+'-journal').exists():
   assert child.poll() is None and time.monotonic()<deadline,'missed transactional crash window'
   time.sleep(.001)
  child.kill();out,err=child.communicate(timeout=10);assert 'SENTINEL' not in out+err
 finally:
  if child.poll() is None:child.kill();child.communicate(timeout=10)
 assert state(crash)==before,'interrupted migration did not roll back'
 assert run(crash,'migrate')['migrated'] is True
 before=state(crash)
 child=subprocess.Popen(COMMAND,cwd=ROOT,env=env(crash,'retire',100000000,1000),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  deadline=time.monotonic()+10
  while not Path(str(crash)+'-journal').exists():
   assert child.poll() is None and time.monotonic()<deadline,'missed retention crash window'
   time.sleep(.001)
  child.kill();out,err=child.communicate(timeout=10);assert 'SENTINEL' not in out+err
 finally:
  if child.poll() is None:child.kill();child.communicate(timeout=10)
 assert state(crash)==before,'interrupted retirement did not roll back'
 assert run(crash,'retire',100000000,1000)=={'ok':True,'retired':1000}

print('Approval retention: frozen v1 preservation, explicit four-process upgrade, bounded concurrent retirement, irreversible tombstones, disk-full rollback and SIGKILL recovery passed')

with tempfile.TemporaryDirectory(prefix='payments-approval-admin-') as directory:
    root=Path(directory);path=root/'outbox.db';seed(path);config=root/'admin.json'
    def admin(settings):
        config.write_text(json.dumps(settings));config.chmod(0o600)
        result=subprocess.run(['bash','scripts/link-approval-maintenance.sh'],cwd=ROOT,env={**os.environ,'KUJO_BIN':KUJO,'PAYMENTS_APPROVAL_MAINTENANCE_CONFIG':str(config)},capture_output=True,text=True,timeout=20)
        assert 'SENTINEL' not in result.stdout+result.stderr
        assert result.stdout.strip(),result.stderr
        return result.returncode,json.loads(result.stdout)
    base={'schema':'kujo.link-approval-maintenance/v1','database':str(path)}
    assert admin({**base,'action':'migrate'})[0]==1
    assert state(path)[1]==1
    assert admin({**base,'action':'migrate','quiesced':True})==(0,{'ok':True,'schema_version':2,'migrated':True})
    assert admin({**base,'action':'retire','batch_limit':1001})[0]==1
    assert admin({**base,'action':'retire','batch_limit':2})==(0,{'ok':True,'retired':2})
    assert admin({**base,'action':'retire','batch_limit':2})==(0,{'ok':True,'retired':1})
    with sqlite3.connect(path) as db:
        plan=db.execute('EXPLAIN QUERY PLAN SELECT id FROM link_approval_outbox_v2 WHERE approval_url IS NOT NULL AND expires_at_ms<=? ORDER BY expires_at_ms,id LIMIT ?',(2000,1)).fetchall()
        assert any('link_approval_outbox_expiry' in row[3] for row in plan),plan
print('Private administrator command validates configuration, requires migration quiescence and retires indexed bounded batches without URL output')
