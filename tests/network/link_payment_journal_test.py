"""Frozen legacy issuance/submission profiles must survive reopening without repair."""
import concurrent.futures, json, os, sqlite3, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PROFILE=json.loads((ROOT/'tests/fixtures/link-payment-journal-v0.json').read_text())
def invoke(path,group):
    p=subprocess.run([os.environ['KUJO_BIN'],'run','tests/link_payment_journal.kujo','--interpreter'],cwd=ROOT,env={**os.environ,'PAYMENTS_TEST_DB':str(path),'PAYMENTS_JOURNAL_GROUP':group},capture_output=True,text=True,timeout=15)
    assert p.returncode==0,'journal fixture process failed'
    assert 'SENTINEL' not in p.stdout+p.stderr
    return json.loads(p.stdout)['ok']
def signature(path):
    with sqlite3.connect(path) as db:
        return (db.execute('PRAGMA user_version').fetchone(),db.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall(),{t:db.execute('SELECT * FROM '+t).fetchall() for t in ['link_authorizations','link_mpp_prepared','link_mpp_dispatches','link_provider_prepared'] if db.execute('SELECT 1 FROM sqlite_master WHERE name=?',(t,)).fetchone()})
with tempfile.TemporaryDirectory(prefix='payments-link-journal-') as directory:
    root=Path(directory)
    # The factory initialization order and actual populated legacy records survive.
    for first,second in [('authorization','submission')]:
        path=root/first
        with sqlite3.connect(path) as db:
            for group in PROFILE.values():
                for entry in group:db.execute(entry['sql'])
        with sqlite3.connect(path) as db:
            db.execute("INSERT INTO link_authorizations VALUES('ref','digest','account','network','key','native')")
            db.execute("INSERT INTO link_mpp_prepared VALUES('ref','snapshot','challenge','{}')")
            db.execute("INSERT INTO link_mpp_dispatches VALUES('ref','claim')")
            db.execute("INSERT INTO link_provider_prepared VALUES('ref','scope','execution','installation','intent','{}')")
        before=signature(path)
        assert invoke(path,first) and invoke(path,second) and signature(path)==before
    # Every missing/changed frozen object is rejected, never recreated.
    cases=0
    for definition in PROFILE['authorization']+PROFILE['submission']+PROFILE['provider']:
        for mode in ['missing','changed']:
            path=root/f'fault-{cases}';cases+=1
            with sqlite3.connect(path) as db:
                for group in PROFILE.values():
                    for entry in group:
                        sql=entry['sql']
                        if entry['name']==definition['name']:
                            if mode=='missing':continue
                            if sql.startswith('CREATE TABLE'):sql=sql.replace('TEXT PRIMARY KEY','TEXT',1)
                            elif sql.startswith('CREATE UNIQUE INDEX'):sql=sql.replace('CREATE UNIQUE INDEX','CREATE INDEX')
                            else:sql=sql.replace("RAISE(ABORT,", "RAISE(FAIL,")
                        try:db.execute(sql)
                        except sqlite3.OperationalError:
                            # A missing table also prevents its own indexes/triggers.
                            assert mode=='missing' and definition['sql'].startswith('CREATE TABLE')
                before=db.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()
            assert not invoke(path,'provider')
            with sqlite3.connect(path) as db:assert db.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()==before
    for case in ['future','foreign']:
        path=root/case;assert invoke(path,'authorization')
        with sqlite3.connect(path) as db:
            if case=='future':db.execute('PRAGMA user_version=1')
            else:db.execute('CREATE TABLE unrelated(secret TEXT)');db.execute("INSERT INTO unrelated VALUES('SENTINEL_PRIVATE')")
        before=signature(path);assert not invoke(path,'authorization') and not invoke(path,'submission');assert signature(path)==before
    empty=root/'submission-first';assert not invoke(empty,'submission')
    incomplete=root/'incomplete-provider';assert invoke(incomplete,'authorization');assert not invoke(incomplete,'provider')
    assert invoke(incomplete,'submission');assert not invoke(incomplete,'provider')
    fresh=root/'provider-race'
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        assert all(pool.map(lambda _:invoke(fresh,'provider'),range(4)))
    path=root/'race'
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        assert all(pool.map(lambda _:invoke(path,'authorization'),range(4)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        assert all(pool.map(lambda group:invoke(path,group),['authorization','submission','authorization','submission']))
    assert invoke(path,'authorization') and invoke(path,'submission')
print('Link payment journal: legacy full factory profile, retained rows/claims, 26 missing/changed objects, future/foreign profiles and four-process initialization passed')
