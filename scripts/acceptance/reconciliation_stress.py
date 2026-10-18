"""Bounded fresh-process synthetic seed stress; never retries a failed sample."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def sample(index):
    with tempfile.TemporaryDirectory(prefix='payments-seed-stress-') as temporary:
        db = Path(temporary) / 'core.db'
        env = {**os.environ, 'PAYMENTS_TEST_DB': str(db), 'PAYMENTS_TEST_MODE': 'seed',
               'PAYMENTS_TEST_EXECUTION': '', 'PAYMENTS_TEST_PROCESSOR_DB': '',
               'PAYMENTS_TEST_STOP': ''}
        reason = 'unexpected_result'
        try:
            p = subprocess.run([os.environ['KUJO_BIN'], 'run', 'tests/reconciliation.kujo',
                                '--interpreter'], cwd=ROOT, env=env, capture_output=True,
                               text=True, timeout=30)
            reason = 'process_failed' if p.returncode else 'unexpected_result'
            if p.returncode == 0 and json.loads(p.stdout) == {'ok': True}:
                with sqlite3.connect(db) as core, sqlite3.connect(str(db)+'.processor') as processor:
                    assert core.execute('SELECT state,claimed FROM executions').fetchall() == [('reconciliation_required', 1)]
                    assert core.execute('SELECT consumed FROM approvals').fetchall() == [(1,)]
                    assert processor.execute('SELECT count(*) FROM fixture_charges').fetchone() == (1,)
                return {'sample': index, 'ok': True}
        except subprocess.TimeoutExpired:
            reason = 'timeout'
        except (AssertionError, ValueError, sqlite3.Error):
            reason = 'invariant_failed'
        # Never copy arbitrary process errors, journals or provider values into
        # acceptance artifacts. Preserve only the independently queried counts.
        evidence = {'sample': index, 'ok': False, 'code': reason}
        for name, path, sql in (
            ('claimed', db, 'SELECT sum(claimed) FROM executions'),
            ('consumed', db, 'SELECT sum(consumed) FROM approvals'),
            ('charges', Path(str(db)+'.processor'), 'SELECT count(*) FROM fixture_charges')):
            try:
                with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as connection:
                    value = connection.execute(sql).fetchone()[0]
                evidence[name] = value if type(value) is int else None
            except sqlite3.Error:
                evidence[name] = None
        return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=40, choices=range(1, 201), metavar='1..200')
    parser.add_argument('--workers', type=int, default=2, choices=range(1, 5))
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error('assertions must be enabled')
    binary = Path(os.environ['KUJO_BIN'])
    if not binary.is_absolute() or not binary.is_file():
        parser.error('KUJO_BIN must name an absolute executable')
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(sample, range(args.samples)))
    failed = [result for result in results if not result['ok']]
    print(json.dumps({'schema': 'kujo.payments.synthetic-seed-stress/v1',
                      'samples': args.samples, 'workers': args.workers,
                      'passed': len(results)-len(failed), 'failures': failed,
                      'elapsed_seconds': round(time.monotonic()-started, 3),
                      'runtime_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                      'scope': 'synthetic_fresh_processes_not_provider_acceptance',
                      'root_cause_resolved': False}, sort_keys=True))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
