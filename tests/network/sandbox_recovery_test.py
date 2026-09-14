"""Kill after a fake Stripe charge, then recover solely through verified reads."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']
with tempfile.TemporaryDirectory(prefix='payments-sandbox-recovery-') as directory:
    root = Path(directory)
    processor = root / 'processor.db'
    journal = root / 'merchant.db'
    marker = root / 'charged'
    with sqlite3.connect(processor) as db:
        db.execute('CREATE TABLE payments(body TEXT)')
    env = {**os.environ, 'PAYMENTS_RECOVERY_DB': str(journal),
           'PAYMENTS_RECOVERY_PROCESSOR': str(processor),
           'PAYMENTS_RECOVERY_MARKER': str(marker)}
    argv = [KUJO, 'run', 'tests/sandbox_recovery.kujo', '--interpreter']
    process = subprocess.Popen(argv, cwd=ROOT, env={**env, 'PAYMENTS_RECOVERY_MODE': 'create'},
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 15
        while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        if not marker.exists() or process.poll() is not None:
            stdout, stderr = process.communicate(timeout=5)
            raise AssertionError(('charge checkpoint not reached', stdout, stderr))
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
        assert 'SENTINEL' not in stdout + stderr
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
    with sqlite3.connect(journal) as db:
        assert db.execute('SELECT payment_intent_id FROM sandbox_purchases').fetchall() == [(None,)]
    recovered = False
    for mode in ('wrong_account', 'wrong_amount', 'live', 'wrong_binding', 'pending',
                 'wrong_id', 'exception', 'missing_claim', 'recover', 'recover', 'substitute'):
        result = subprocess.run(argv, cwd=ROOT, env={**env, 'PAYMENTS_RECOVERY_MODE': mode},
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert 'SENTINEL' not in result.stdout + result.stderr
        output = json.loads(result.stdout)
        assert output['ok'] is (mode == 'recover'), (mode, output)
        recovered = recovered or mode == 'recover'
        with sqlite3.connect(journal) as db:
            expected = 'pi_fixture' if recovered else None
            assert db.execute('SELECT payment_intent_id FROM sandbox_purchases').fetchall() == [(expected,)]
        with sqlite3.connect(processor) as db:
            assert db.execute('SELECT count(*) FROM payments').fetchone()[0] == 1
    with sqlite3.connect(journal) as db:
        assert db.execute('SELECT payment_intent_id FROM sandbox_purchases').fetchall() == [('pi_fixture',)]
print('Sandbox recovery: killed after charge; mismatches denied; expired purchase recovered idempotently without another charge')
