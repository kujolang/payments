"""Verify actual exported snapshots and reject tampering without opening them for writes."""
import hashlib,json,os,shutil,sqlite3,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def command(args,ok=True,env=None):
    p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=40)
    assert 'SENTINEL' not in p.stdout+p.stderr
    assert (p.returncode==0)==ok,'fixture command failed'
    return json.loads(p.stdout)
def verify(path,ok=True,extra=()):
    return command(['python3','scripts/maintenance/verify_recovery.py','--snapshot-dir',str(path),*extra],ok)
def rehash(path):
    m=json.loads((path/'manifest.json').read_text());m['database_sha256']=hashlib.sha256((path/'payments.db').read_bytes()).hexdigest();(path/'manifest.json').write_text(json.dumps(m))
with tempfile.TemporaryDirectory(prefix='payments-verify-recovery-') as tmp:
    root=Path(tmp);source=root/'source.db';base=root/'base'
    command([os.environ['KUJO_BIN'],'run','tests/control.kujo','--interpreter'],env={**os.environ,'PAYMENTS_TEST_DB':str(source),'PAYMENTS_TEST_CONTROL':'setup'})
    command(['python3','scripts/maintenance/recovery_snapshot.py','--source',str(source),'--output-dir',str(base)])
    before={p.name:p.read_bytes() for p in base.iterdir()};result=verify(base)
    assert result['mode']=='observation_only' and result['live_reenable_supported'] is False and result['additional_schema_objects']==0
    assert before=={p.name:p.read_bytes() for p in base.iterdir()}
    second=root/'second';command(['python3','scripts/maintenance/recovery_snapshot.py','--source',str(base/'payments.db'),'--output-dir',str(second)]);assert verify(second)['ok']
    legacy=root/'legacy.db'
    with sqlite3.connect(legacy) as db:
        for entry in json.loads((ROOT/'contracts/storage/v1-baseline.json').read_text()):db.execute(entry['sql'])
        db.execute('INSERT INTO payments_meta VALUES(1)');db.execute("INSERT INTO execution_control VALUES(1,'active',0)");db.execute("INSERT INTO execution_control_events VALUES(0,'active','fixture',1000)")
    legacy_copy=root/'legacy-copy';command(['python3','scripts/maintenance/recovery_snapshot.py','--source',str(legacy),'--output-dir',str(legacy_copy)]);assert verify(legacy_copy)['core_schema_version']==1
    for case in ['bytes','manifest','duplicate','enable','missing','marker','guard','active','event','foreign','history','version','db_symlink','manifest_symlink','hardlink','permissions','directory_permissions','wal','shm','journal']:
        path=root/case;shutil.copytree(base,path)
        if case=='bytes':
            with (path/'payments.db').open('ab') as f:f.write(b'SENTINEL_TRAILER')
        elif case=='manifest':(path/'manifest.json').write_text('SENTINEL_BAD_JSON')
        elif case=='duplicate':
            m=(path/'manifest.json').read_text();(path/'manifest.json').write_text(m[:-2]+',"mode":"observation_only"}')
        elif case=='enable':
            m=json.loads((path/'manifest.json').read_text());m['live_reenable_supported']=0;(path/'manifest.json').write_text(json.dumps(m))
        elif case=='missing':(path/'manifest.json').unlink()
        elif case in ['marker','guard','active','event','foreign','history','version']:
            with sqlite3.connect(path/'payments.db') as db:
                if case=='marker':db.execute('DROP TRIGGER permanent_restore_marker_delete');db.execute('DELETE FROM restore_quarantine')
                if case=='guard':db.execute('DROP TRIGGER quarantine_claim')
                if case=='active':db.execute('DROP TRIGGER quarantine_resume');db.execute("UPDATE execution_control SET mode='active'")
                if case=='event':
                    db.execute('PRAGMA writable_schema=ON');db.execute("UPDATE sqlite_master SET sql=replace(sql,'ABORT','FAIL') WHERE name='quarantine_resume'")
                if case=='foreign':db.execute('PRAGMA foreign_keys=OFF');db.execute("INSERT INTO incidents VALUES('missing_execution','evidence','digest','code')")
                if case=='history':
                    original=db.execute("SELECT sql FROM sqlite_master WHERE name='permanent_schema_history_UPDATE'").fetchone()[0]
                    db.execute('DROP TRIGGER permanent_schema_history_UPDATE');db.execute('UPDATE schema_history SET from_version=99');db.execute(original)
                if case=='version':db.execute('PRAGMA writable_schema=ON');db.execute("UPDATE sqlite_master SET sql='CREATE TABLE payments_meta(version TEXT)' WHERE name='payments_meta'")
            rehash(path) # A self-consistent hash is insufficient without quarantine/schema checks.
        elif case.endswith('_symlink'):
            name='payments.db' if case=='db_symlink' else 'manifest.json';(path/name).unlink();(path/name).symlink_to(base/name)
        elif case=='hardlink':(path/'payments.db').unlink();os.link(base/'payments.db',path/'payments.db')
        elif case=='permissions':(path/'payments.db').chmod(0o644)
        elif case=='directory_permissions':path.chmod(0o755)
        else:(path/('payments.db-'+{'wal':'wal','shm':'shm','journal':'journal'}[case])).write_text('SENTINEL_PRIVATE')
        try:assert verify(path,False)=={'ok':False,'code':'recovery_verification_failed'}
        except AssertionError:raise AssertionError('recovery verification case: '+case) from None
        if case=='hardlink':(path/'payments.db').unlink()
    assert verify(base,False,['--max-bytes','4096'])['ok'] is False
    assert verify(base,False,['--timeout-seconds','0'])['ok'] is False
print('Recovery verification: actual and repeated exports, immutable reads, 20 tamper/quarantine/path cases and bounds passed')
