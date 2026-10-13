"""Offline recovery must bound the first query and SQLite lock acquisition too."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/maintenance'))
from recovery_snapshot import snapshot, validate_schema


class RecoveryBoundsTest(unittest.TestCase):
    def test_invalid_metadata_cardinality_stops_after_two_rows(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.execute('CREATE TABLE payments_meta(version INTEGER)')
            db.executemany('INSERT INTO payments_meta VALUES(?)', [(2,)] * 5000)
            # A full scan exhausts this SQLite instruction budget. Detecting a
            # second metadata row is enough to reject the unsupported schema.
            db.set_progress_handler(lambda: 1, 1000)
            with self.assertRaisesRegex(ValueError, 'unsupported schema'):
                validate_schema(db)

    def rejected_within_bound(self, source, destination):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/maintenance/recovery_snapshot.py'),
             '--source', str(source), '--output-dir', str(destination),
             '--timeout-seconds', '1'],
            capture_output=True, text=True, timeout=3,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout),
                         {'ok': False, 'code': 'recovery_snapshot_failed'})
        self.assertEqual(result.stderr, '')
        self.assertFalse((destination / 'payments.db').exists())
        self.assertFalse((destination / 'manifest.json').exists())

    def test_initial_schema_query_obeys_deadline(self):
        with tempfile.TemporaryDirectory(prefix='payments-recovery-query-') as tmp:
            root = Path(tmp)
            with closing(sqlite3.connect(root / 'source.db')) as db:
                db.execute('CREATE VIEW payments_meta AS WITH RECURSIVE n(x) AS '
                           '(VALUES(0) UNION ALL SELECT x+1 FROM n WHERE x<1000000000) '
                           'SELECT max(x) AS version FROM n')
            self.rejected_within_bound(root / 'source.db', root / 'copy')

    def test_source_lock_obeys_deadline(self):
        with tempfile.TemporaryDirectory(prefix='payments-recovery-lock-') as tmp:
            root = Path(tmp)
            with closing(sqlite3.connect(root / 'source.db')) as db:
                for entry in json.loads((ROOT / 'contracts/storage/v2-baseline.json').read_text()):
                    db.execute(entry['sql'])
                db.execute('INSERT INTO payments_meta VALUES(2)')
                db.commit()
                db.execute('BEGIN EXCLUSIVE')
                self.rejected_within_bound(root / 'source.db', root / 'copy')

    def test_invalid_api_bounds_do_not_create_output(self):
        with tempfile.TemporaryDirectory(prefix='payments-recovery-bounds-') as tmp:
            root = Path(tmp)
            source = root / 'source.db'
            with closing(sqlite3.connect(source)):
                pass
            for index, (timeout, maximum) in enumerate([
                (True, 4096), (1.5, 4096), (0, 4096), (301, 4096),
                (1, 4096.0), (1, True), (1, 4095), (1, 16*1024**3+1),
            ]):
                target = root / str(index)
                with self.subTest(timeout=timeout, maximum=maximum):
                    with self.assertRaises(ValueError):
                        snapshot(source, target, timeout, maximum)
                    self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
