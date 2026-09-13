"""Actual Kujo atomic initialization and explicit v1->v2 migration/fault tests."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2]
KUJO=os.environ['KUJO_BIN']
BASELINE=json.loads((ROOT/'contracts/storage/v1-baseline.json').read_text())
ROWS=json.loads((ROOT/'tests/fixtures/storage-v1.json').read_text())

def legacy(path):
    with sqlite3.connect(path) as db:
        for kind in ('table','trigger'):
            for item in BASELINE:
                if item['type']==kind: db.execute(item['sql'])
        for table,rows in ROWS.items():
            for row in rows:
                db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in row)+')',row)
        db.execute("UPDATE execution_control SET mode='active'")

def run(script, env, ok=True, root=ROOT):
    p=subprocess.run([KUJO,'run',script,'--interpreter'],cwd=root,env=env,
                     capture_output=True,text=True,timeout=25)
    value=json.loads(p.stdout)
    assert (p.returncode==0)==ok and value['ok']==ok,(p.stdout,p.stderr)
    return value

def environment(root,path):
    config=root/(path.stem+'.json')
    config.write_text(json.dumps({'schema':'kujo.payment-control/v1','database':str(path),'actor_ref':'migration-admin'}))
    return {**os.environ,'PAYMENTS_CONTROL_CONFIG':str(config),'PAYMENTS_TEST_DB':str(path)}

def records(path):
    with sqlite3.connect(path) as db:
        return {name:db.execute('SELECT * FROM '+name).fetchall() for name in
                ['executions','approvals','issued_approvals','request_keys','observations','ability_calls','provider_authorizations','restore_quarantine']}

def kill_at_boundary(script, workroot, env, marker):
    worker=subprocess.Popen([KUJO,'run',script,'--interpreter'],cwd=workroot,env=env,
                            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+15
        while not marker.exists():
            assert worker.poll() is None,worker.communicate()
            assert time.monotonic()<deadline,'migration did not reach crash boundary'
            time.sleep(.02)
        worker.kill();worker.communicate(timeout=5)
    finally:
        if worker.poll() is None: worker.kill();worker.wait()

with tempfile.TemporaryDirectory(prefix='payments-migration-') as directory:
    root=Path(directory)
    # Concurrent first-ever initialization must expose either nothing or v2,
    # never an empty metadata table or a partially created claim guard.
    fresh=root/'fresh.db';env=environment(root,fresh)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:run('tests/schema_open.kujo',env),range(8)))
    assert all(r['ok'] for r in results)
    with sqlite3.connect(fresh) as db:
        assert db.execute('SELECT version FROM payments_meta').fetchall()==[(2,)]
        assert db.execute('SELECT version,from_version FROM schema_history').fetchall()==[(2,0)]
    old=root/'old.db';legacy(old);env=environment(root,old)
    with sqlite3.connect(old) as db:
        db.execute('UPDATE approvals SET consumed=1')
        db.execute("UPDATE executions SET claimed=1,state='executing',invocation_id='invocation'")
        fixture=json.loads((ROOT/'tests/fixtures/domain.json').read_text())
        fixture['receipt']['execution_id']='exec_control'
        db.execute("UPDATE executions SET state='succeeded',receipt_json=?",(json.dumps(fixture['receipt']),))
        db.execute("INSERT INTO observations VALUES('exec_control','evidence','digest',?)",(json.dumps(fixture['observation']),))
        db.execute("INSERT INTO ability_calls VALUES('fixture','key','digest','invocation','fixture keyed receipt')")
    before=records(old)
    assert run('tests/schema_open.kujo',env,False)=={'ok':False}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:run('src/executor/migrate.kujo',env),range(4)))
    assert all(r['schema_version']==2 and r['control']['mode']=='paused' for r in results)
    assert records(old)==before
    with sqlite3.connect(old) as db:
        assert db.execute('SELECT version,from_version FROM schema_history').fetchall()==[(2,1)]
        assert db.execute('SELECT count(*) FROM execution_control_events').fetchone()[0]==2
    assert run('tests/schema_open.kujo',env)['ok']
    # A quarantined legacy journal remains quarantined across migration.
    quarantine=root/'quarantine.db';legacy(quarantine)
    with sqlite3.connect(quarantine) as db:
        db.execute("INSERT INTO restore_quarantine VALUES(1,'fixture',1000)")
        db.execute("UPDATE execution_control SET mode='paused'")
    env=environment(root,quarantine)
    result=run('src/executor/migrate.kujo',env)
    command={**env,'PAYMENTS_CONTROL_ACTION':'resume','PAYMENTS_CONTROL_REVISION':str(result['control']['revision'])}
    assert run('src/executor/control.kujo',command,False)['code']=='control_conflict'
    # Unknown/missing financial constraints are rejected, never silently repaired.
    drift=root/'drift.db';legacy(drift)
    with sqlite3.connect(drift) as db: db.execute('DROP TRIGGER permanent_claim')
    assert run('src/executor/migrate.kujo',environment(root,drift),False)['code']=='migration_failed'
    # Force transaction failure at the audit boundary: mode/data/version all roll back.
    failed=root/'failed.db';legacy(failed);before=records(failed)
    with sqlite3.connect(failed) as db:
        db.execute("CREATE TRIGGER fixture_failure BEFORE INSERT ON execution_control_events BEGIN SELECT RAISE(ABORT,'fixture'); END")
    run('src/executor/migrate.kujo',environment(root,failed),False)
    assert records(failed)==before
    with sqlite3.connect(failed) as db:
        assert db.execute('SELECT version FROM payments_meta').fetchall()==[(1,)]
        assert db.execute('SELECT mode FROM execution_control').fetchone()[0]=='active'
    # Instrument a private copy only; no production crash-hook/environment flag.
    scratch=root/'instrumented';scratch.mkdir()
    shutil.copytree(ROOT/'src',scratch/'src');shutil.copytree(ROOT/'contracts',scratch/'contracts')
    module=scratch/'src/storage/sqlite.kujo'
    code=module.read_text();needle='            db_execute(db,"INSERT INTO schema_history VALUES(2,1,?,?,?)"'
    assert code.count(needle)==1
    code=code.replace(needle,'            write_file(env("PAYMENTS_TEST_MARKER"),"ready")\n            sleep(30000)\n'+needle)
    module.write_text(code)
    crashed=root/'crashed.db';legacy(crashed);before=records(crashed);env=environment(root,crashed)
    marker=root/'crash-marker';env['PAYMENTS_TEST_MARKER']=str(marker)
    kill_at_boundary('src/executor/migrate.kujo',scratch,env,marker)
    assert records(crashed)==before
    with sqlite3.connect(crashed) as db:
        assert db.execute('SELECT version FROM payments_meta').fetchall()==[(1,)]
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='schema_history'").fetchone()[0]==0
    assert run('src/executor/migrate.kujo',env)['control']['mode']=='paused'
    # Kill first-time initialization after all DDL but before its first commit.
    init_code=(ROOT/'src/storage/sqlite.kujo').read_text()
    needle='        if version == 0 { db_execute(db,"INSERT INTO schema_history VALUES(2,0'
    assert init_code.count(needle)==1
    init_code=init_code.replace(needle,'        if version == 0 { write_file(env("PAYMENTS_TEST_MARKER"),"ready"); sleep(30000) }\n'+needle)
    module.write_text(init_code)
    shutil.copyfile(ROOT/'tests/schema_open.kujo',scratch/'open.kujo')
    initial=root/'initial-crash.db';marker=root/'initial-marker';env=environment(root,initial)
    env['PAYMENTS_TEST_MARKER']=str(marker)
    kill_at_boundary('open.kujo',scratch,env,marker)
    with sqlite3.connect(initial) as db:
        assert db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0]==0
    assert run('tests/schema_open.kujo',env)['ok']
    # Version 2 is equally strict: never recreate a missing safety trigger silently.
    with sqlite3.connect(initial) as db: db.execute('DROP TRIGGER permanent_claim')
    assert run('tests/schema_open.kujo',env,False)=={'ok':False}
print('Schema migration: eight-process initialization, four-process v1 upgrade, exact financial preservation, quarantine retention, schema drift denial, transaction fault and SIGKILL rollback passed')
