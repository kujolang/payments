"""Independent flat identity conformance plus startup admission of Ability principals."""
import hashlib,hmac,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];KUJO=os.environ['KUJO_BIN']
TOKEN='flat-profile-test-token-'+'x'*48
with tempfile.TemporaryDirectory(prefix='payments-identity-profile-') as directory:
 root=Path(directory);vectors=root/'vectors.json'
 subprocess.run(['python3','scripts/flat_identity_vectors.py','--output',str(vectors)],cwd=ROOT,check=True,timeout=10)
 for mode in ['vm','interpreter']:
  command=[KUJO,'run','tests/flat_identity_scope.kujo']+(['--interpreter'] if mode=='interpreter' else [])
  result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PAYMENTS_FLAT_IDENTITY_VECTORS':str(vectors),'PAYMENTS_TEST_DB':str(root/(mode+'.db'))},capture_output=True,text=True,timeout=90)
  assert result.returncode==0,(mode,result.stdout,result.stderr)
  assert '36 independent approval/scope/request/cancel-key vectors' in result.stdout
 # Domain/service schema accepts these lengths, but installed Ability does not.
 for length in [65,128]:
  database=root/f'invalid-{length}.db'
  settings={'schema':'kujo.payment-service/v1','bind':'127.0.0.1','port':19876,'database':str(database),'namespace':'identity-profile','currency_table':{'version':'fixture-v1','exponents':{'USD':2}},'credentials':[{'verifier':hmac.new(TOKEN.encode(),b'kujo.payments.transport/v1',hashlib.sha256).hexdigest(),'principal':{'type':'T'*length,'id':'payer','tenant_id':'tenant'},'operations':['request','inspect'],'disabled':False,'expires_at_ms':4102444800000}]}
  path=root/f'config-{length}.json';path.write_text(json.dumps(settings));path.chmod(0o600)
  result=subprocess.run([KUJO,'run','src/executor/gateway.kujo','--interpreter'],cwd=ROOT,env={**os.environ,'PAYMENTS_SERVICE_CONFIG':str(path)},capture_output=True,text=True,timeout=10)
  assert result.returncode!=0 and 'credential_ability_identity' in result.stderr
  assert TOKEN not in result.stdout+result.stderr and not database.exists(),'reject before storage initialization'
print('Identity profile: independent Python/VM/interpreter vectors, flat scope enforcement, legacy receipts retained, incompatible service identities rejected before storage initialization passed')
