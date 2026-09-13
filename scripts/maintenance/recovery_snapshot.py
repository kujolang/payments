"""Create an observation-only SQLite recovery snapshot. Never enable restored spending.

Administrative maintenance only: no provider credentials, financial calls or execution.
"""
from contextlib import closing
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def digest_file(path, maximum, deadline):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while True:
            data = stream.read(1024*1024)
            if not data:
                break
            size += len(data)
            if size > maximum or time.monotonic() > deadline:
                raise ValueError('snapshot limit')
            digest.update(data)
    return digest.hexdigest()


def validate_schema(connection):
    versions = connection.execute('SELECT version FROM payments_meta').fetchall()
    if len(versions) != 1 or type(versions[0][0]) is not int or versions[0][0] not in (1, 2):
        raise ValueError('unsupported schema')
    version = versions[0][0]
    for expected in json.loads((ROOT/f'contracts/storage/v{version}-baseline.json').read_text()):
        actual = connection.execute('SELECT type,sql FROM sqlite_master WHERE name=?',
                                    (expected['name'],)).fetchall()
        if actual != [(expected['type'], expected['sql'])]:
            raise ValueError('schema drift')


def snapshot(source, destination, timeout=30, max_bytes=256*1024*1024):
    if not 0 < timeout <= 300 or not 4096 <= max_bytes <= 16*1024**3:
        raise ValueError('invalid maintenance bounds')
    source = Path(source)
    destination = Path(destination)
    if source.is_symlink() or not source.is_file():
        raise ValueError('source must be an existing regular database')
    if destination.exists() or destination.is_symlink():
        raise ValueError('destination already exists')
    # A private output directory is reserved exclusively. A failed run can leave
    # this empty directory for inspection, but never a published unlatched DB.
    destination.mkdir(mode=0o700)
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryDirectory(prefix='.stage-', dir=destination) as temporary:
        staged = Path(temporary)/'payments.db'
        def progress(status, remaining, total):
            if time.monotonic() > deadline or total * page_size > max_bytes:
                raise TimeoutError('snapshot deadline')
        uri = source.resolve().as_uri() + '?mode=ro'
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as original:
            validate_schema(original)
            page_size = original.execute('PRAGMA page_size').fetchone()[0]
            if original.execute('PRAGMA page_count').fetchone()[0] * page_size > max_bytes:
                raise ValueError('snapshot size')
            with closing(sqlite3.connect(staged, timeout=5)) as copy:
                original.backup(copy, pages=128, progress=progress, sleep=0.05)
        # No live WAL is copied with filesystem tools. The SQLite backup above is
        # a consistent database snapshot, including committed WAL pages.
        source_digest = digest_file(staged, max_bytes, deadline)
        with closing(sqlite3.connect(staged, timeout=5)) as copy:
            copy.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            validate_schema(copy)
            if copy.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('integrity failure')
            if copy.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('foreign key failure')
            copy.execute('PRAGMA journal_mode=DELETE')
            copy.execute('PRAGMA synchronous=FULL')
            copy.execute('BEGIN IMMEDIATE')
            for statement in json.loads((ROOT/'contracts/storage/quarantine.sql.json').read_text()):
                copy.execute(statement)
            # Retain the earliest quarantine marker when snapshotting a recovery
            # copy again. It is deliberately impossible to resume through the API.
            copy.execute('INSERT OR IGNORE INTO restore_quarantine VALUES(1,?,?)',
                         (source_digest, int(time.time()*1000)))
            copy.execute("UPDATE execution_control SET mode='paused',revision=revision+1 WHERE id=1")
            if copy.execute('SELECT mode FROM execution_control WHERE id=1').fetchall() != [('paused',)]:
                raise ValueError('control unavailable')
            revision = copy.execute('SELECT revision FROM execution_control WHERE id=1').fetchone()[0]
            copy.execute('INSERT INTO execution_control_events VALUES(?,?,?,?)',
                         (revision, 'paused', 'recovery-snapshot', int(time.time()*1000)))
            copy.execute("UPDATE executions SET state='reconciliation_required',revision=revision+1 WHERE claimed=1 AND state='executing'")
            copy.commit()
        staged.chmod(0o600)
        digest = digest_file(staged, max_bytes, deadline)
        with staged.open('rb') as stream:
            os.fsync(stream.fileno())
        # Atomic, no-overwrite publication only after the latch has committed.
        os.link(staged, destination/'payments.db')
        manifest = {'schema':'kujo.payment-recovery-snapshot/v1',
                    'database_sha256':digest,'source_snapshot_sha256':source_digest,
                    'mode':'observation_only','live_reenable_supported':False}
        with (destination/'manifest.json').open('x') as stream:
            os.chmod(stream.name, 0o600)
            json.dump(manifest,stream,indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        fd = os.open(destination, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=30)
    parser.add_argument('--max-bytes', type=int, default=256*1024*1024)
    args = parser.parse_args()
    try:
        result = snapshot(args.source, args.output_dir, args.timeout_seconds, args.max_bytes)
    except Exception:
        # Never interpolate database/config contents or private filesystem errors.
        print(json.dumps({'ok':False,'code':'recovery_snapshot_failed'}))
        raise SystemExit(1)
    print(json.dumps({'ok':True, **result}))
