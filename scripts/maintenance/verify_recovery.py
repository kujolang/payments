"""Verify a quiescent published core snapshot's integrity and execution quarantine."""
import argparse
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
from recovery_snapshot import ROOT, digest_file, validate_schema


def private_file(path, directory=False):
    info = path.lstat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('private ownership required')
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError('regular owned artifact required')
    if not directory and info.st_nlink != 1:
        raise ValueError('aliased artifact')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate manifest field')
        result[key] = value
    return result


def verify(directory, timeout=30, max_bytes=256*1024*1024):
    if type(timeout) is not int or not 0 < timeout <= 300 or type(max_bytes) is not int or not 4096 <= max_bytes <= 16*1024**3:
        raise ValueError('invalid verification bounds')
    deadline = time.monotonic() + timeout
    directory = Path(directory)
    before_dir = private_file(directory, directory=True)
    database = directory/'payments.db'; manifest_path = directory/'manifest.json'
    before_db = private_file(database); before_manifest = private_file(manifest_path)
    if before_manifest[2] > 65536 or before_db[2] > max_bytes:
        raise ValueError('artifact limit')
    def no_sidecars():
        for suffix in ['-wal', '-shm', '-journal']:
            sidecar = directory/('payments.db'+suffix)
            if sidecar.exists() or sidecar.is_symlink():
                raise ValueError('quiescent publication required')
    no_sidecars()
    manifest = json.loads(manifest_path.read_bytes(), object_pairs_hook=unique_object)
    fields = {'schema','database_sha256','source_snapshot_sha256','mode','live_reenable_supported'}
    if type(manifest) is not dict or set(manifest) != fields or manifest['schema'] != 'kujo.payment-recovery-snapshot/v1' or manifest['mode'] != 'observation_only' or manifest['live_reenable_supported'] is not False:
        raise ValueError('invalid manifest')
    for name in ['database_sha256','source_snapshot_sha256']:
        if type(manifest[name]) is not str or not re.fullmatch('[a-f0-9]{64}', manifest[name]):
            raise ValueError('invalid digest')
    digest = digest_file(database, max_bytes, deadline)
    if digest != manifest['database_sha256']:
        raise ValueError('artifact digest mismatch')
    # No journal recovery, writes or sidecar creation while inspecting a published copy.
    with closing(sqlite3.connect(database.resolve().as_uri()+'?mode=ro&immutable=1', uri=True, timeout=1)) as db:
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        validate_schema(db)
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('database integrity')
        version = db.execute('SELECT version FROM payments_meta').fetchone()[0]
        if version == 2:
            history = db.execute('SELECT version,from_version,source_digest FROM schema_history').fetchall()
            previous = hashlib.sha256((ROOT/'contracts/storage/v1-baseline.json').read_bytes()).hexdigest()
            if history not in [[(2,0,None)],[(2,1,previous)]]:
                raise ValueError('migration lineage')
        if version == 1 and db.execute("SELECT 1 FROM sqlite_master WHERE name='schema_history' OR name LIKE 'permanent_schema_history_%' LIMIT 1").fetchone():
            raise ValueError('legacy migration history conflict')
        marker = db.execute('SELECT id,source_digest,restored_at_ms FROM restore_quarantine').fetchall()
        if len(marker) != 1 or marker[0][0] != 1 or type(marker[0][1]) is not str or not re.fullmatch('[a-f0-9]{64}',marker[0][1]) or type(marker[0][2]) is not int or marker[0][2] < 0:
            raise ValueError('quarantine marker absent')
        controls = db.execute('SELECT mode,revision FROM execution_control WHERE id=1').fetchall()
        if len(controls) != 1 or controls[0][0] != 'paused':
            raise ValueError('quarantine control')
        if db.execute('SELECT mode FROM execution_control_events WHERE revision=?',(controls[0][1],)).fetchall() != [('paused',)]:
            raise ValueError('quarantine control evidence')
        if db.execute("SELECT 1 FROM executions WHERE claimed=1 AND state='executing' LIMIT 1").fetchone():
            raise ValueError('unreconciled execution state')
        baseline = json.loads((ROOT/f'contracts/storage/v{version}-baseline.json').read_text())
        additional = db.execute("SELECT count(*) FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone()[0] - len(baseline)
    if digest_file(database,max_bytes,deadline) != digest or private_file(database) != before_db or private_file(manifest_path) != before_manifest or private_file(directory,directory=True) != before_dir:
        raise ValueError('artifact changed during verification')
    no_sidecars()
    if time.monotonic() > deadline:
        raise TimeoutError('verification deadline')
    return {'schema':'kujo.payment-recovery-verification/v1','database_sha256':digest,'mode':'observation_only','live_reenable_supported':False,'verification_scope':'core_integrity_and_quarantine','core_schema_version':version,'additional_schema_objects':additional}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-dir',required=True)
    parser.add_argument('--timeout-seconds',type=int,default=30)
    parser.add_argument('--max-bytes',type=int,default=256*1024*1024)
    args = parser.parse_args()
    try:
        result = verify(args.snapshot_dir,args.timeout_seconds,args.max_bytes)
    except Exception:
        print(json.dumps({'ok':False,'code':'recovery_verification_failed'}))
        raise SystemExit(1)
    print(json.dumps({'ok':True,**result}))
