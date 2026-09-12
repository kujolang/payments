"""Exercise native Kujo issuance claims across processes with a non-deduping fake API."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
KUJO=os.environ['KUJO_BIN']
def run(env):
    p=subprocess.run([KUJO,'run','tests/link_issuance_race.kujo','--interpreter'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert 'SENTINEL' not in p.stdout+p.stderr
    return json.loads(p.stdout) if p.stdout else None
for lost in ('0','1'):
    with tempfile.TemporaryDirectory(prefix='payments-link-race-') as directory:
        root=Path(directory);ledger=root/'api.db'
        with sqlite3.connect(ledger) as db:
            db.execute('CREATE TABLE calls(request_key TEXT)') # No uniqueness constraint.
        env={**os.environ,'PAYMENTS_LINK_DB':str(root/'link.db'),'PAYMENTS_LINK_LEDGER':str(ledger),'PAYMENTS_LINK_LOST':lost}
        run({**env,'PAYMENTS_LINK_INIT':'1'})
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:run(env),range(4)))
        again=run(env)
        with sqlite3.connect(ledger) as db:
            assert db.execute('SELECT count(*) FROM calls').fetchone()[0]==1
        if lost=='1':
            assert all(x=={'ok':False,'code':'link_authorization_unknown'} for x in results+[again])
        else:
            assert again=={'ok':True,'status':'authorized'}
print('Link issuance: four native workers, non-deduping API ledger, lost create response and restart all retain one issuance')
