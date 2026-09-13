"""Snapshot a pre-claim DB, claim afterwards, prove the stale copy cannot claim."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']

def run(script, env, ok=True):
    result = subprocess.run([KUJO, 'run', script, '--interpreter'],cwd=ROOT,
                            env=env,capture_output=True,text=True,timeout=25)
    assert (result.returncode==0)==ok,(result.stdout,result.stderr)
    return json.loads(result.stdout)

def backup(source, destination, ok=True, extra=()):
    result=subprocess.run(['python3','scripts/maintenance/recovery_snapshot.py',
                           '--source',str(source),'--output-dir',str(destination),*extra],
                          cwd=ROOT,capture_output=True,text=True,timeout=40)
    assert (result.returncode==0)==ok,(result.stdout,result.stderr)
    value=json.loads(result.stdout)
    assert value['ok']==ok
    return value

with tempfile.TemporaryDirectory(prefix='payments-recovery-') as directory:
    root=Path(directory); source=root/'source.db'
    env={**os.environ,'PAYMENTS_TEST_DB':str(source),'PAYMENTS_TEST_CONTROL':'setup'}
    run('tests/control.kujo',env)
    config=root/'control.json'
    config.write_text(json.dumps({'schema':'kujo.payment-control/v1','database':str(source),'actor_ref':'admin'}))
    command={**env,'PAYMENTS_CONTROL_CONFIG':str(config),'PAYMENTS_CONTROL_ACTION':'resume','PAYMENTS_CONTROL_REVISION':'1'}
    assert run('src/executor/control.kujo',command)['ok']
    # Keep a real WAL reader/writer connection open across the backup. The tool
    # must include the committed page even though it is absent from the base file.
    with sqlite3.connect(source) as live:
        live.execute('CREATE TABLE wal_fixture(value TEXT)')
        live.execute("INSERT INTO wal_fixture VALUES('committed WAL evidence')")
        live.commit()
        recovered=root/'recovered'
        manifest=backup(source,recovered)
        assert manifest['mode']=='observation_only' and not manifest['live_reenable_supported']
        assert hashlib.sha256((recovered/'payments.db').read_bytes()).hexdigest()==manifest['database_sha256']
        with sqlite3.connect(recovered/'payments.db') as copy:
            assert copy.execute('SELECT value FROM wal_fixture').fetchone()[0]=='committed WAL evidence'
        # Winning a later claim on the source makes the copy demonstrably stale.
        assert run('tests/control.kujo',{**env,'PAYMENTS_TEST_CONTROL':'claim'})['won']
        assert live.execute('SELECT mode FROM execution_control').fetchone()[0]=='active'
        assert live.execute('SELECT count(*) FROM restore_quarantine').fetchone()[0]==0
    clone={**env,'PAYMENTS_TEST_DB':str(recovered/'payments.db'),'PAYMENTS_TEST_CONTROL':'claim'}
    assert run('tests/control.kujo',clone)['won'] is False
    config.write_text(json.dumps({'schema':'kujo.payment-control/v1','database':str(recovered/'payments.db'),'actor_ref':'admin'}))
    with sqlite3.connect(recovered/'payments.db') as copy:
        revision=copy.execute('SELECT revision FROM execution_control').fetchone()[0]
        assert copy.execute('SELECT claimed FROM executions').fetchone()[0]==0
        for statement in ["UPDATE execution_control SET mode='active'",'DELETE FROM restore_quarantine',
                          "UPDATE executions SET state='executing',claimed=1",
                          "INSERT INTO provider_authorizations VALUES('exec_control',1)"]:
            try:
                copy.execute(statement)
            except sqlite3.DatabaseError:
                copy.rollback()
            else:
                raise AssertionError('quarantine bypass')
    command['PAYMENTS_CONTROL_REVISION']=str(revision)
    assert run('src/executor/control.kujo',command,False)['code']=='control_conflict'
    assert backup(source,recovered,False)=={'ok':False,'code':'recovery_snapshot_failed'}
    assert (recovered.stat().st_mode & 0o777)==0o700
    assert ((recovered/'payments.db').stat().st_mode & 0o777)==0o600
    assert ((recovered/'manifest.json').stat().st_mode & 0o777)==0o600
    # A post-claim snapshot preserves the tombstone and is immediately reconcilable.
    post=root/'post'
    backup(source,post)
    assert run('tests/control.kujo',{**env,'PAYMENTS_TEST_DB':str(post/'payments.db'),'PAYMENTS_TEST_CONTROL':'recover'})['status']=='reconciliation_required'
    duplicate=root/'duplicate'
    backup(post/'payments.db',duplicate)
    assert run('tests/control.kujo',{**env,'PAYMENTS_TEST_DB':str(duplicate/'payments.db'),'PAYMENTS_TEST_CONTROL':'claim'})['won'] is False
    # Bound violations never publish a database, and source bytes stay untouched.
    small=root/'small'
    backup(source,small,False,['--max-bytes','4096'])
    assert not (small/'payments.db').exists()
    future=root/'future.db'
    with sqlite3.connect(future) as db:
        db.execute('CREATE TABLE payments_meta(version INTEGER)')
        db.execute('INSERT INTO payments_meta VALUES(999)')
    before=hashlib.sha256(future.read_bytes()).hexdigest()
    backup(future,root/'future-copy',False)
    config.write_text(json.dumps({'schema':'kujo.payment-control/v1','database':str(future),'actor_ref':'admin'}))
    command['PAYMENTS_CONTROL_ACTION']='inspect'
    assert run('src/executor/control.kujo',command,False)=={'ok':False,'code':'control_failed'}
    assert hashlib.sha256(future.read_bytes()).hexdigest()==before
print('Recovery snapshot: committed WAL, stale pre-claim denial, permanent quarantine, resume/bypass denial, post-claim reconciliation, bounds, permissions and future-schema refusal passed')
