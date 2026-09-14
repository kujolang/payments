"""Native multi-process merchant claims against a non-deduplicating fake Stripe."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']


def run(env):
    result = subprocess.run(
        [KUJO, 'run', 'tests/sandbox_merchant_race.kujo', '--interpreter'],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert 'SENTINEL' not in result.stdout + result.stderr
    return json.loads(result.stdout) if result.stdout else None


for lost in ('0', '1'):
    with tempfile.TemporaryDirectory(prefix='payments-sandbox-merchant-') as directory:
        root = Path(directory)
        ledger = root / 'effects.db'
        with sqlite3.connect(ledger) as db:
            db.execute('CREATE TABLE effects(request_key TEXT)')
        env = {**os.environ, 'PAYMENTS_MERCHANT_DB': str(root / 'merchant.db'),
               'PAYMENTS_MERCHANT_LEDGER': str(ledger), 'PAYMENTS_MERCHANT_LOST': lost}
        run({**env, 'PAYMENTS_MERCHANT_INIT': '1'})
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: run(env), range(4)))
        again = run(env)
        assert again['code'] == 'sandbox_submission_already_claimed'
        with sqlite3.connect(ledger) as db:
            assert db.execute('SELECT count(*) FROM effects').fetchone()[0] == 1
        if lost == '1':
            assert all(result['ok'] is False for result in results)
        else:
            assert sum(result['ok'] is True for result in results) == 1
print('Sandbox merchant: four workers and restart produce one call with successful or lost responses')
