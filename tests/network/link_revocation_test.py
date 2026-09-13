"""Private synthetic revocation: never contact Link or revoke a real session."""
from concurrent.futures import ThreadPoolExecutor
import json,os,sqlite3,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
COMMAND=[os.environ['KUJO_BIN'],'run','tests/link_revocation.kujo','--interpreter']
def invoke(env,mode):
 p=subprocess.run(COMMAND,cwd=ROOT,env={**env,'PAYMENTS_REVOKE_MODE':mode},capture_output=True,text=True,timeout=20)
 assert p.returncode==0,(p.stdout,p.stderr)
 assert 'SENTINEL' not in p.stdout+p.stderr
 return json.loads(p.stdout)
def inspect(path):
 with sqlite3.connect(path) as db:return db.execute('SELECT state,generation,access_token,refresh_token FROM link_credentials_v1').fetchone()
def calls(path):
 with sqlite3.connect(str(path)+'.provider') as db:return db.execute('SELECT kind FROM calls').fetchall()
for mode in ('success','failure','throw','malformed','late','rollback','wrong_scope','wrong_generation','form','race','crash','rotate_inflight'):
 with tempfile.TemporaryDirectory(prefix='payments-revocation-') as directory:
  root=Path(directory);path=root/'vault.db';env={**os.environ,'PAYMENTS_CREDENTIAL_DB':str(path),'PAYMENTS_REVOKE_MARKER':str(root/'marker')}
  assert invoke(env,'install')['ok']
  if mode=='crash':
   p=subprocess.Popen(COMMAND,cwd=ROOT,env={**env,'PAYMENTS_REVOKE_MODE':'crash'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   try:
    deadline=time.monotonic()+10
    while not (root/'marker').exists():
     assert p.poll() is None and time.monotonic()<deadline
     time.sleep(.02)
    p.kill();out,err=p.communicate(timeout=5);assert 'SENTINEL' not in out+err
   finally:
    if p.poll() is None:p.kill();p.communicate(timeout=5)
  elif mode=='race':
   with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:invoke(env,'success'),range(4)))
   assert sum(x['ok'] for x in results)==1,results
  else:
   result=invoke(env,mode)
   if mode=='rotate_inflight':
    assert result['ok'] and inspect(path)==('disabled',2,None,None) and calls(path)==[]
    continue
   if mode in ('wrong_scope','wrong_generation','form'):
    assert result['ok']==(mode=='form') and inspect(path)[0]=='active'
    assert calls(path)==[]
    continue
   assert result=={'ok':True,'state':'disabled','generation':1,'provider_revocation':'acknowledged' if mode=='success' else 'unknown'},result
  assert inspect(path)==('disabled',1,None,None)
  assert calls(path)==[('revoke',)]
  assert not invoke(env,'success')['ok']
  assert calls(path)==[('revoke',)],'no automatic provider re-entry after disable'
  assert not invoke(env,'install')['ok'],'identity cannot be re-enabled'
print('Private Link revocation: 12 failure/identity/deadline/form/race/crash/rotation cases, local disable before provider, one request, no secret output and no re-entry passed')
