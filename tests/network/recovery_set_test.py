"""Real private journals, shared SQLite write barrier and quarantined recovery set."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/maintenance'))
import recovery_set as subject


def cli(action,directory,config=None,ok=True,extra=()):
    command=[sys.executable,str(ROOT/'scripts/maintenance/recovery_set.py'),action,'--directory',str(directory)]
    if config: command+=['--config',str(config)]
    result=subprocess.run(command+list(extra),capture_output=True,text=True,timeout=45)
    assert sentinel not in result.stdout+result.stderr and 'Traceback' not in result.stderr,'private diagnostic leakage'
    assert (result.returncode==0)==ok,'unexpected maintenance result'
    value=json.loads(result.stdout)
    assert value['ok']==ok
    if not ok: assert value=={'ok':False,'code':'recovery_set_failed'}
    return value


with tempfile.TemporaryDirectory(prefix='payments-recovery-set-') as temporary:
    root=Path(temporary);source=root/'source';source.mkdir(mode=0o700)
    sentinel='PAYMENTS_SET_'+uuid.uuid4().hex
    env={**os.environ,'PAYMENTS_CANARY_ROOT':str(source),'PAYMENTS_CANARY_DOMAIN':str(ROOT/'tests/fixtures/domain.json'),'PAYMENTS_PROVIDER_SECRET':sentinel}
    p=subprocess.run([os.environ['KUJO_BIN'],'run','tests/network/credential_vault_seed.kujo','--interpreter'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert p.returncode==0 and sentinel not in p.stdout+p.stderr,'private fixture failed'
    members={'core':'operator-payments.db','provider':'link-approval-auth.db','outbox':'link-approval-outbox.db','credentials':'link-vault.db','enrollment':'link-enrollment.db'}
    sources={name:source/file for name,file in members.items()}
    for path in sources.values():path.chmod(0o600)
    config=root/'config.json'
    def configure(values):
        config.write_text(json.dumps({'schema':subject.SCHEMA,'sources':{n:str(p) for n,p in values.items()}}));config.chmod(0o600)
    configure(sources)
    # A committed WAL page must be included while its live connection stays open.
    with closing(sqlite3.connect(sources['provider'])) as live:
        live.execute('PRAGMA journal_mode=WAL');live.execute('CREATE TABLE recovery_fixture(value TEXT)');live.execute('INSERT INTO recovery_fixture VALUES(?)',(sentinel,));live.commit()
        with subject.locked_sources(sources,time.monotonic()+10):
            for path in sources.values():
                with closing(sqlite3.connect(path,timeout=.02)) as writer:
                    try: writer.execute('BEGIN IMMEDIATE')
                    except sqlite3.OperationalError: pass
                    else: raise AssertionError('source writer admitted under barrier')
        output=root/'set'
        assert cli('create',output,config)['member_count']==5
        assert cli('verify',output)['verification_scope']=='declared_member_integrity_and_core_quarantine'
    manifest=json.loads((output/'manifest.json').read_text())
    provider=output/manifest['members']['provider']['path']
    with closing(sqlite3.connect(provider)) as db:assert db.execute('SELECT value FROM recovery_fixture').fetchone()==(sentinel,)
    # Real credential/enrollment values survive only in explicitly private members.
    credentials=output/manifest['members']['credentials']['path']
    with closing(sqlite3.connect(credentials)) as db:
        assert sentinel in str(db.execute('SELECT access_token,refresh_token FROM link_credentials_v1').fetchall())
    for path in output.rglob('*'):
        assert path.stat().st_mode & 0o077 == 0,'private backup permission'
        if path.is_file() and path.suffix!='.db':assert sentinel.encode() not in path.read_bytes(),'secret in manifest'
    before={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()}
    cli('verify',output)
    assert before=={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*') if p.is_file()},'verification wrote publication'
    with closing(sqlite3.connect(output/'core/payments.db')) as db:
        assert db.execute('SELECT mode FROM execution_control').fetchone()==('paused',)
        try:db.execute("UPDATE execution_control SET mode='active'")
        except sqlite3.DatabaseError:pass
        else:raise AssertionError('restored core resumed')
    cli('create',output,config,ok=False)
    cases=['bytes','manifest','missing','extra','sidecar','symlink','core_symlink','permissions','hardlink','false_integer','path','duplicate','core_manifest']
    for case in cases:
        altered=root/case;shutil.copytree(output,altered)
        mpath=altered/'manifest.json';m=json.loads(mpath.read_text());private=altered/m['members']['credentials']['path']
        if case=='bytes':
            with private.open('r+b') as stream:stream.seek(100);stream.write(b'BROKEN')
        elif case=='manifest':m['unknown']=True
        elif case=='missing':private.unlink()
        elif case=='extra':(altered/'unexpected').write_text('x')
        elif case=='sidecar':Path(str(private)+'-wal').touch(mode=0o600)
        elif case=='symlink':private.unlink();private.symlink_to(credentials)
        elif case=='core_symlink':shutil.rmtree(altered/'core');(altered/'core').symlink_to(output/'core')
        elif case=='permissions':private.chmod(0o644)
        elif case=='hardlink':private.unlink();os.link(credentials,private)
        elif case=='false_integer':m['live_reenable_supported']=0
        elif case=='path':m['members']['credentials']['path']='../source/link-vault.db'
        elif case=='duplicate':mpath.write_text('{"schema":"x",'+mpath.read_text()[1:])
        elif case=='core_manifest':(altered/'core/manifest.json').write_text('{}')
        if case in ['manifest','false_integer','path']:mpath.write_text(json.dumps(m))
        cli('verify',altered,ok=False)
        shutil.rmtree(altered)
    cli('create',root/'small',config,ok=False,extra=['--max-bytes','4096'])
    cli('verify',output,ok=False,extra=['--max-bytes','4096'])
    bad={**sources,'provider':sources['core']};configure(bad);cli('create',root/'alias',config,ok=False)
    configure(sources)
    # Holding the final source lock forces timeout and releases earlier reservations.
    held_path=sorted(sources.values(),key=str)[-1]
    with closing(sqlite3.connect(held_path)) as held:
        held.execute('BEGIN IMMEDIATE')
        cli('create',root/'busy',config,ok=False,extra=['--timeout-seconds','1'])
    assert not (root/'busy/manifest.json').exists()
    original=subject.copy_private
    def fail(*args,**kwargs):raise OSError(sentinel)
    subject.copy_private=fail
    try:
        try:subject.create(config,root/'fault')
        except OSError:pass
        else:raise AssertionError('publication accepted failed private copy')
    finally:subject.copy_private=original
    assert not (root/'fault/manifest.json').exists()
    # Kill an actual maintenance process after a private database was copied.
    # OS lock release must not turn the incomplete directory into a publication.
    crash_code='''import os,signal,sys
sys.path.insert(0,sys.argv[1])
import recovery_set as subject
original=subject.copy_private
def crash(*args,**kwargs):
 original(*args,**kwargs)
 os.kill(os.getpid(),signal.SIGKILL)
subject.copy_private=crash
subject.create(sys.argv[2],sys.argv[3])
'''
    killed=subprocess.run([sys.executable,'-c',crash_code,str(ROOT/'scripts/maintenance'),str(config),str(root/'killed')],capture_output=True,text=True,timeout=30)
    assert killed.returncode==-9 and sentinel not in killed.stdout+killed.stderr
    assert not (root/'killed/manifest.json').exists()
    cli('verify',root/'killed',ok=False)
    for path in sources.values():
        with closing(sqlite3.connect(path,timeout=.05)) as writer:writer.execute('BEGIN IMMEDIATE');writer.rollback()
    cli('create',root/'after-fault',config)
print('Recovery set: five actual journals, shared writer exclusion, committed WAL, private credential retention, quarantine, 13 tamper cases, bounded lock failure, SIGKILL and partial-publication refusal passed')
