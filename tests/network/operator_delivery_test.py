"""Actual core journal + Link private outbox + reviewed operator sink, no provider calls."""
import json,os,sqlite3,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];KUJO=os.environ['KUJO_BIN']
for mode in ['success','ready','tenant','payer','digest','definition','paused','expired','cancel_during_fetch','pause_during_fetch','cancel_during_render','pause_during_render','render_throw','render_object','core_snapshot','wrong_execution','claimed','malformed_operator','definition_collision']:
 with tempfile.TemporaryDirectory(prefix='payments-reviewed-delivery-') as directory:
  root=Path(directory)
  p=subprocess.run([KUJO,'run','tests/operator_delivery.kujo','--interpreter'],cwd=ROOT,env={**os.environ,'PAYMENTS_OPERATOR_DELIVERY_ROOT':directory,'PAYMENTS_OPERATOR_DELIVERY_MODE':mode},capture_output=True,text=True,timeout=20,umask=0o077)
  assert 'SENTINEL' not in p.stdout+p.stderr,'private payload escaped caller output'
  assert p.returncode==0,(p.stdout,p.stderr)
  result=json.loads(p.stdout);assert result['ok']==(mode in ['success','ready']),(mode,result)
  rendered=mode in ['success','ready','cancel_during_render','pause_during_render','render_throw','render_object']
  sink=root/'private-operator.json';assert sink.exists()==rendered,mode
  if rendered:
   assert json.loads(sink.read_text())['approval_url']=='https://approve.example/SENTINEL_PRIVATE_URL'
   assert sink.stat().st_mode&0o777==0o600
  with sqlite3.connect(root/'payments.db') as db:
   assert db.execute('SELECT claimed FROM executions').fetchone()[0]==int(mode=='claimed')
   assert db.execute('SELECT count(*) FROM approvals').fetchone()[0]==int(mode in ['ready','claimed'])
   if mode in ['ready','claimed']:assert db.execute('SELECT consumed FROM approvals').fetchone()[0]==int(mode=='claimed')
  for f in root.iterdir():
   data=f.read_bytes();assert b'SENTINEL_OAUTH' not in data and b'SENTINEL_RENDER' not in data
   if not f.name.startswith('outbox.db') and f!=sink:assert b'SENTINEL_PRIVATE_URL' not in data,(mode,f.name)
print('Reviewed operator delivery: 19 actual core/Link cases, pending and ready grants, scope/binding denial, fetch/render cancellation and pause, bounded private sink, no new/consumed grant or financial claim')
