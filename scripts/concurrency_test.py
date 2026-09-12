"""Process/fault supervisor; all admission decisions execute the actual Kujo store."""
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
BIN = os.environ['KUJO_BIN']
COMMAND = [BIN, 'run', 'tests/concurrency_worker.kujo']

def run(env, mode):
    return subprocess.run(COMMAND, env={**env, 'PAYMENTS_TEST_MODE':mode}, cwd=ROOT, capture_output=True, text=True, timeout=20, check=True)

def setup(path):
    env = {**os.environ, 'PAYMENTS_TEST_DB':str(path/'state.db'), 'PAYMENTS_TEST_PROCESSOR':str(path/'processor.db'), 'PAYMENTS_TEST_MARKER':str(path/'marker')}
    with sqlite3.connect(env['PAYMENTS_TEST_PROCESSOR']) as db:
        db.execute('CREATE TABLE charges(execution_id TEXT)')  # no unique key
    run(env, 'setup')
    return env

def charges(env):
    with sqlite3.connect(env['PAYMENTS_TEST_PROCESSOR']) as db:
        return db.execute('SELECT count(*) FROM charges').fetchone()[0]

def race(env):
    workers = [subprocess.Popen(COMMAND, cwd=ROOT, env={**env,'PAYMENTS_TEST_MODE':'submit'}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(8)]
    results = []
    try:
        for worker in workers:
            out, err = worker.communicate(timeout=20)
            assert worker.returncode == 0, (out, err)
            results.append(out.strip())
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
                worker.wait()
    return results

with tempfile.TemporaryDirectory(prefix='payments-concurrency-') as tmp:
    base = Path(tmp)
    ordinary = base/'ordinary'; ordinary.mkdir()
    env = setup(ordinary)
    output = race(env)
    assert output.count('winner') == 1, output
    assert charges(env) == 1
    assert race(env).count('winner') == 0
    assert charges(env) == 1
    for phase, expected in [('crash_before_send',0),('crash_after_send',1)]:
        path = base/phase; path.mkdir()
        env = setup(path)
        worker = subprocess.Popen(COMMAND,cwd=ROOT,env={**env,'PAYMENTS_TEST_MODE':phase},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline = time.monotonic()+15
            while not Path(env['PAYMENTS_TEST_MARKER']).exists():
                if worker.poll() is not None:
                    raise AssertionError(worker.communicate())
                if time.monotonic() > deadline:
                    raise AssertionError('worker did not reach fault boundary')
                time.sleep(.02)
            worker.kill()
            worker.communicate(timeout=5)
        finally:
            if worker.poll() is None:
                worker.kill(); worker.wait()
        run(env,'recover')
        assert race(env).count('winner') == 0
        assert charges(env) == expected
        with sqlite3.connect(env['PAYMENTS_TEST_DB']) as db:
            assert db.execute('SELECT state,claimed FROM executions').fetchone() == ('reconciliation_required',1)
    # Negative control: the fake processor itself permits duplicate charges.
    with sqlite3.connect(env['PAYMENTS_TEST_PROCESSOR']) as db:
        db.executemany('INSERT INTO charges VALUES(?)',[('control',),('control',)])
        assert db.execute("SELECT count(*) FROM charges WHERE execution_id='control'").fetchone()[0] == 2
print('Kujo SQLite: 8-process race and SIGKILL before/after dispatch passed; no resumed dispatch')
