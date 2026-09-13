"""Capture declared SQLite journals under one write barrier; core stays quarantined.

Privileged maintenance: the resulting directory may contain payment credentials.
No provider calls, credential output, automatic restore or spending re-enable.
"""
import argparse
from contextlib import ExitStack, closing, contextmanager
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import time
from recovery_snapshot import digest_file, snapshot
from verify_recovery import private_file, unique_object, verify as verify_core

SCHEMA = 'kujo.payment-recovery-set/v1'


def bounds(timeout, maximum):
    if type(timeout) is not int or not 0 < timeout <= 300 or type(maximum) is not int or not 4096 <= maximum <= 16*1024**3:
        raise ValueError('invalid bounds')


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError('maintenance deadline')
    return value


def read_config(path):
    path = Path(path)
    if private_file(path)[2] > 65536:
        raise ValueError('config limit')
    value = json.loads(path.read_bytes(), object_pairs_hook=unique_object)
    if type(value) is not dict or set(value) != {'schema', 'sources'} or value['schema'] != SCHEMA:
        raise ValueError('invalid config')
    sources = value['sources']
    if type(sources) is not dict or not 2 <= len(sources) <= 8 or 'core' not in sources:
        raise ValueError('invalid members')
    for name, source in sources.items():
        if not re.fullmatch('[a-z][a-z0-9_]{0,31}', name) or type(source) is not str or not Path(source).is_absolute():
            raise ValueError('invalid source')
    return {name: Path(source) for name, source in sources.items()}


@contextmanager
def locked_sources(sources, deadline):
    # SQLite write reservations exclude conforming writers, not host administrators
    # or remote effects already in flight. Acquire every reservation before reading.
    identities = {name: private_file(path)[:2] for name, path in sources.items()}
    if len(set(identities.values())) != len(sources):
        raise ValueError('duplicate source')
    with ExitStack() as stack:
        for name, path in sorted(sources.items(), key=lambda item: str(item[1])):
            connection = stack.enter_context(closing(sqlite3.connect(
                path.resolve().as_uri()+'?mode=rw', uri=True,
                timeout=min(5, remaining(deadline)))))
            connection.execute('BEGIN IMMEDIATE')
            stack.callback(connection.rollback)
            if private_file(path)[:2] != identities[name]:
                raise ValueError('source replaced')
        yield
        for name, path in sources.items():
            if private_file(path)[:2] != identities[name]:
                raise ValueError('source replaced')
        remaining(deadline)


def copy_private(source, target, maximum, deadline):
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro', uri=True, timeout=min(5,remaining(deadline)))) as original:
        page_size = original.execute('PRAGMA page_size').fetchone()[0]
        def progress(status, left, total):
            remaining(deadline)
            if total*page_size > maximum:
                raise ValueError('size limit')
        # Restrict permissions before SQLite creates any content or sidecars.
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(target)) as copy:
            original.backup(copy, pages=128, progress=progress, sleep=0.05)
            copy.set_progress_handler(lambda: int(time.monotonic() > deadline),1000)
            if copy.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or copy.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('private integrity')
            copy.execute('PRAGMA journal_mode=DELETE')
    with target.open('rb') as stream:
        os.fsync(stream.fileno())
    return {'path': target.name, 'bytes': target.stat().st_size,
            'sha256': digest_file(target, maximum, deadline)}


def create(config, directory, timeout=30, max_bytes=256*1024*1024):
    bounds(timeout,max_bytes)
    deadline=time.monotonic()+timeout
    sources=read_config(config)
    directory=Path(directory)
    directory.mkdir(mode=0o700)  # exclusive; partial failure never publishes a manifest
    private_file(directory,directory=True)
    entries={}
    with locked_sources(sources,deadline):
        core=snapshot(sources['core'],directory/'core',min(300,math.ceil(remaining(deadline))),max_bytes)
        used=(directory/'core'/'payments.db').stat().st_size
        entries['core']={'path':'core/payments.db','bytes':used,'sha256':core['database_sha256']}
        for index,name in enumerate(sorted(set(sources)-{'core'})):
            available=max_bytes-used
            if available < 4096:
                raise ValueError('set size')
            value=copy_private(sources[name],directory/f'private-{index:02d}.db',available,deadline)
            entries[name]=value
            used+=value['bytes']
        if used>max_bytes:
            raise ValueError('set size')
    # Only completed barrier capture gets a manifest. Not an authenticity signature.
    manifest={'schema':SCHEMA,'mode':'observation_only','live_reenable_supported':False,
              'consistency':'declared_sqlite_write_barrier','members':entries}
    remaining(deadline)
    with (directory/'manifest.json').open('x') as stream:
        os.chmod(stream.name,0o600)
        json.dump(manifest,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    fd=os.open(directory,os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return {'schema':SCHEMA,'mode':'observation_only','live_reenable_supported':False,'member_count':len(entries)}


def verify(directory,timeout=30,max_bytes=256*1024*1024):
    bounds(timeout,max_bytes)
    deadline=time.monotonic()+timeout
    directory=Path(directory);before=private_file(directory,directory=True)
    manifest_path=directory/'manifest.json';manifest_before=private_file(manifest_path)
    if manifest_before[2]>65536: raise ValueError('manifest limit')
    manifest=json.loads(manifest_path.read_bytes(),object_pairs_hook=unique_object)
    if type(manifest) is not dict or set(manifest)!={'schema','mode','live_reenable_supported','consistency','members'} or manifest['schema']!=SCHEMA or manifest['mode']!='observation_only' or manifest['live_reenable_supported'] is not False or manifest['consistency']!='declared_sqlite_write_barrier':
        raise ValueError('invalid manifest')
    entries=manifest['members']
    if type(entries) is not dict or not 2<=len(entries)<=8 or 'core' not in entries:
        raise ValueError('invalid members')
    names=sorted(set(entries)-{'core'})
    private_file(directory/'core',directory=True)
    if set(p.name for p in (directory/'core').iterdir())!={'payments.db','manifest.json'}:
        raise ValueError('unexpected core files')
    expected={'core':'core/payments.db',**{name:f'private-{i:02d}.db' for i,name in enumerate(names)}}
    if set(p.name for p in directory.iterdir())!={'core','manifest.json',*(expected[n] for n in names)}:
        raise ValueError('unexpected files')
    used=0;observed={}
    for name,value in entries.items():
        if not re.fullmatch('[a-z][a-z0-9_]{0,31}',name) or type(value) is not dict or set(value)!={'path','bytes','sha256'} or value['path']!=expected[name] or type(value['bytes']) is not int or value['bytes']<4096 or type(value['sha256']) is not str or not re.fullmatch('[a-f0-9]{64}',value['sha256']):
            raise ValueError('invalid member')
        path=directory/value['path'];identity=private_file(path);used+=identity[2]
        if used>max_bytes or identity[2]!=value['bytes'] or digest_file(path,max_bytes,deadline)!=value['sha256']:
            raise ValueError('member mismatch')
        observed[name]=identity
        if name!='core':
            with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
                db.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
                if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('private integrity')
    core=verify_core(directory/'core',min(300,math.ceil(remaining(deadline))),max_bytes)
    if core['database_sha256']!=entries['core']['sha256']: raise ValueError('core mismatch')
    for name,value in entries.items():
        path=directory/value['path']
        if private_file(path)!=observed[name] or digest_file(path,max_bytes,deadline)!=value['sha256']: raise ValueError('member changed')
    if private_file(directory,directory=True)!=before or private_file(manifest_path)!=manifest_before: raise ValueError('publication changed')
    remaining(deadline)
    return {'schema':SCHEMA,'mode':'observation_only','live_reenable_supported':False,'member_count':len(entries),'verification_scope':'declared_member_integrity_and_core_quarantine'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['create','verify'])
    parser.add_argument('--directory',required=True)
    parser.add_argument('--config')
    parser.add_argument('--timeout-seconds',type=int,default=30)
    parser.add_argument('--max-bytes',type=int,default=256*1024*1024)
    args=parser.parse_args()
    try:
        if (args.action=='create') != (args.config is not None): raise ValueError('config mode')
        value=create(args.config,args.directory,args.timeout_seconds,args.max_bytes) if args.action=='create' else verify(args.directory,args.timeout_seconds,args.max_bytes)
    except Exception:
        print(json.dumps({'ok':False,'code':'recovery_set_failed'}));raise SystemExit(1)
    print(json.dumps({'ok':True,**value}))
