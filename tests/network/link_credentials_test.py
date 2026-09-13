"""Private OAuth vault rotation: real native processes, fake non-deduping issuer."""
from concurrent.futures import ThreadPoolExecutor
import json,os,sqlite3,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
KUJO=os.environ['KUJO_BIN']
COMMAND=[KUJO,'run','tests/link_credentials.kujo','--interpreter']
def run(env,action):
    result=subprocess.run(COMMAND,cwd=ROOT,env={**env,'PAYMENTS_CREDENTIAL_ACTION':action},capture_output=True,text=True,timeout=20)
    assert 'SENTINEL' not in result.stdout+result.stderr,'credential leaked outside private executor'
    assert result.returncode==0,(result.stdout,result.stderr)
    return json.loads(result.stdout)
for mode in ['success','lost','scope','late','rollback','malformed','commit_failure','disable_race','crash','after_commit']:
    with tempfile.TemporaryDirectory(prefix='payments-private-oauth-') as directory:
        root=Path(directory);vault=root/'vault.db';ledger=root/'issuer.db';marker=root/'marker'
        env={**os.environ,'PAYMENTS_CREDENTIAL_DB':str(vault),'PAYMENTS_CREDENTIAL_LEDGER':str(ledger),'PAYMENTS_CREDENTIAL_MARKER':str(marker)}
        with sqlite3.connect(ledger) as db:db.execute('CREATE TABLE calls(n INTEGER)')
        assert run(env,'install')=={'ok':True,'generation':0}
        vault.chmod(0o600)
        assert run(env,'deny')=={'ok':True}
        if mode in ['crash','after_commit']:
            child=subprocess.Popen(COMMAND,cwd=ROOT,env={**env,'PAYMENTS_CREDENTIAL_ACTION':mode},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                deadline=time.monotonic()+10
                while not marker.exists():
                    assert child.poll() is None and time.monotonic()<deadline
                    time.sleep(.02)
                child.kill();out,err=child.communicate(timeout=10)
                assert 'SENTINEL' not in out+err
            finally:
                if child.poll() is None:child.kill();child.communicate(timeout=10)
        elif mode=='commit_failure':
            # Install a fault after schema validation in one process; other
            # cases cover concurrency without introducing a schema-open race.
            assert run(env,mode)['ok'] is False
        else:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results=list(pool.map(lambda _:run(env,mode),range(4)))
            assert sum(r['ok'] for r in results)==(1 if mode=='success' else 0)
        if mode=='commit_failure':
            with sqlite3.connect(vault) as db:db.execute('DROP TRIGGER fault')
        assert run(env,mode if mode not in ['crash','after_commit'] else 'success')['ok'] is False
        state=run(env,'inspect')
        assert state['state']==('active' if mode in ['success','after_commit'] else 'disabled' if mode=='disable_race' else 'rotating' if mode in ['crash','malformed','commit_failure'] else 'reauthentication_required'),state
        with sqlite3.connect(ledger) as db:assert db.execute('SELECT count(*) FROM calls').fetchone()[0]==1
        with sqlite3.connect(vault) as db:
            access,refresh=db.execute('SELECT access_token,refresh_token FROM link_credentials_v1').fetchone()
            assert (access,refresh)==(('SENTINEL_ACCESS_NEW','SENTINEL_REFRESH_NEW') if mode in ['success','after_commit'] else (None,None))
        assert not any('SENTINEL' in f.read_text(errors='ignore') for f in root.iterdir() if f.name not in ['vault.db','vault.db-journal','vault.db-wal','vault.db-shm']), 'private value leaked into another artifact'
print('Link credentials: four-process rotation, changed scope, malformed/lost response, commit failure, disable race and SIGKILL never repeat a generation; no output leakage')

for mode in ['vault_into_core','core_into_vault','drift']:
    with tempfile.TemporaryDirectory(prefix='payments-vault-separation-') as directory:
        result=subprocess.run([KUJO,'run','tests/credential_separation.kujo','--interpreter'],cwd=ROOT,env={**os.environ,'PAYMENTS_CREDENTIAL_DB':str(Path(directory)/'state.db'),'PAYMENTS_SEPARATION_MODE':mode},capture_output=True,text=True,timeout=20)
        assert result.returncode==0,(result.stdout,result.stderr)
print('Credential vault rejects core-journal co-location and schema drift; core rejects vault as a payment journal')

with tempfile.TemporaryDirectory(prefix='payments-empty-oauth-scope-') as directory:
    vault=Path(directory)/'vault.db'
    assert run({**os.environ,'PAYMENTS_CREDENTIAL_DB':str(vault)},'empty_scope')['ok'] is False
    with sqlite3.connect(vault) as db:assert db.execute('SELECT count(*) FROM link_credentials_v1').fetchone()[0]==0
print('Whitespace-only OAuth scope rejected before credential installation')
