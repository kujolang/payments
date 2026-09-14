"""Exercise the private merchant launcher with fake keys; never call Stripe."""
import base64
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']
encode = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'))
with tempfile.TemporaryDirectory(prefix='payments-sandbox-operator-') as directory:
    root = Path(directory)
    root.chmod(0o700)
    snapshot = json.loads((ROOT/'tests/fixtures/domain.json').read_text())['snapshot']
    expected = json.loads((ROOT/'tests/fixtures/mpp.json').read_text())['expected']
    body = '{}'
    expected['body_digest'] = 'sha-256=' + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
    wire = {'id': 'challenge_fixture', 'realm': expected['realm'], 'method': 'stripe',
            'intent': 'charge', 'expires': expires.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
            'digest': expected['body_digest'],
            'request': base64.urlsafe_b64encode(encode({'amount':'5500','currency':'usd',
                        'methodDetails':{'networkId':'network_1','paymentMethodTypes':['card']}}).encode()).decode().rstrip('=')}
    challenge = 'Payment ' + ', '.join(f'{key}="{value}"' for key, value in sorted(wire.items()))
    snapshot['expires_at_ms'] = int(expires.timestamp()*1000) - 1000
    snapshot['request_binding']['terms_digest'] = hashlib.sha256(encode(wire).encode()).hexdigest()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    settings = {'schema':'kujo.stripe-sandbox-merchant/v1','account_id':'acct_fixture',
                'api_version':'2026-08-27.dahlia','port':port,'snapshot':snapshot,
                'challenge':challenge,'expected':expected,'body':body}
    # Exercise offline publication, then use its actual merchant configuration.
    domain = json.loads((ROOT/'tests/fixtures/domain.json').read_text())
    intent = domain['intent']
    intent['expires_at_ms'] = snapshot['expires_at_ms']
    caps = domain['capabilities']
    caps.update(provider_id='link', adapter_version='0.1.0',
                observed_at_ms=int(time.time()*1000)-1000,
                valid_until_ms=snapshot['expires_at_ms'])
    snapshot['provider'] = {'id':'link','adapter_version':'0.1.0','account_ref':'account_1'}
    plan = {'installed':{'snapshot':snapshot,'capabilities':caps,'expected':expected,
                        'payment_method':'pm_fixture','test_mode':True},
            'intent':intent,'execution_id':snapshot['execution_id'],
            'currency_table':{'version':'fixture-v1','exponents':{'USD':2}},'region':'US',
            'challenge':challenge,'local_fixture':False,
            'route':{'url':'https://example.com/purchase','method':'POST','body':body,
                     'route_id':'mpp_1','route_version':'v1','resource_ref':'order_1'},
            'merchant':{'account_id':'acct_fixture','api_version':'2026-08-27.dahlia','port':port}}
    plan_file = root/'plan.json'
    plan_file.write_text(encode(plan)); plan_file.chmod(0o600)
    configured = root/'configured'
    configure_env = {**os.environ,'KUJO_BIN':KUJO,'PAYMENTS_SANDBOX_PLAN':str(plan_file),
                     'PAYMENTS_SANDBOX_DIR':str(configured)}
    configured_result = subprocess.run(['bash','scripts/sandbox-configure.sh'],cwd=ROOT,
                                     env=configure_env,capture_output=True,text=True,timeout=15)
    assert configured_result.returncode == 0, (configured_result.stdout,configured_result.stderr)
    assert configured.stat().st_mode & 0o077 == 0
    for name in ('merchant.json','buyer.json'):
        assert (configured/name).stat().st_mode & 0o077 == 0
    assert not (configured/'stripe-test-key').exists()
    again = subprocess.run(['bash','scripts/sandbox-configure.sh'],cwd=ROOT,
                           env=configure_env,capture_output=True,text=True,timeout=15)
    assert again.returncode != 0, 'configuration overwritten'
    settings = json.loads((configured/'merchant.json').read_text())
    config = root/'merchant.json'
    key = root/'stripe-test-key'
    config.write_text(encode(settings)); config.chmod(0o600)
    key.write_text('sk_test_SENTINEL'); key.chmod(0o600)
    env = {**os.environ,'KUJO_BIN':KUJO,'PAYMENTS_SANDBOX_DIR':str(root)}
    def run(action='check', **extra):
        result = subprocess.run(['bash','scripts/sandbox-merchant.sh',action], cwd=ROOT,
                                env={**env,**extra}, capture_output=True,text=True,timeout=15)
        assert 'SENTINEL' not in result.stdout + result.stderr
        return result
    result = run()
    assert result.returncode == 0, (result.stdout,result.stderr)
    assert json.loads(result.stdout)['code'] == 'sandbox_configuration_valid'
    assert not (root/'merchant.db').exists(), 'offline check created journal'
    key.chmod(0o644)
    assert run().returncode != 0
    key.chmod(0o600)
    key.write_text('sk_live_SENTINEL')
    assert run().returncode != 0
    key.write_text('sk_test_SENTINEL')
    key.rename(root/'saved-key')
    key.symlink_to(root/'saved-key')
    assert run().returncode != 0
    key.unlink(); (root/'saved-key').rename(key)
    # Missing claim rejects recovery before provider access, despite a plausible ID.
    assert run('recover', PAYMENTS_SANDBOX_PAYMENT_INTENT='pi_fixture').returncode != 0
    # Private buyer can track an intent, but cannot reserve provider issuance
    # merely because configuration and a Stripe sandbox key exist.
    buyer_file = root/'buyer.json'
    buyer_file.write_text((configured/'buyer.json').read_text()); buyer_file.chmod(0o600)
    principal = intent['principal']
    parts = ['kujo.payment-principal/v1',principal['type'],principal['id'],principal['tenant_id']]
    payer_ref = hashlib.sha256(''.join(f'{len(p.encode())}:{p}' for p in parts).encode()).hexdigest()
    host = {'schema':'kujo.link-sandbox-host/v1',
            'authority':{'payer':principal,'operator':{'type':'human','id':'operator','tenant_id':principal['tenant_id']},
                         'issuer_ref':'fixture','ttl_ms':300000},
            'enrollment_id':'enrollment_fixture',
            'enrollment':{'credential_id':'credential_fixture','binding':{
                'tenant_id':principal['tenant_id'],'payer_ref':payer_ref,'account_ref':'account_1',
                'client_id':'registered_fixture','scope':'offline spend'},
                'label':'Kujo Payments','origins':['https://app.link.com']},
            'reconciliation_key':'fixture-reconciliation-key-00000001'}
    host_file = root/'buyer-host.json'
    host_file.write_text(encode(host)); host_file.chmod(0o600)
    def buyer_run(action):
        result = subprocess.run(['bash','scripts/sandbox-buyer.sh',action],cwd=ROOT,
                                env=env,capture_output=True,text=True,timeout=15)
        assert 'SENTINEL' not in result.stdout+result.stderr
        return result
    result = buyer_run('connection')
    assert result.returncode == 0 and json.loads(result.stdout) == {'ok':True,'ready':False}, (result.stdout,result.stderr)
    assert buyer_run('request').returncode == 0
    result = buyer_run('status')
    assert json.loads(result.stdout)['result']['status'] == 'awaiting_authorization'
    result = buyer_run('step')
    assert result.returncode != 0 and json.loads(result.stdout)['code'] == 'sandbox_link_connection_unavailable'
    import sqlite3
    with sqlite3.connect(root/'link.db') as db:
        assert db.execute('SELECT count(*) FROM link_authorizations').fetchone()[0] == 0
    host_file.chmod(0o644)
    assert buyer_run('request').returncode != 0
    host_file.chmod(0o600)
    host['enrollment']['binding']['payer_ref'] = 'other'
    host_file.write_text(encode(host))
    assert buyer_run('connection').returncode != 0
    process = subprocess.Popen(['bash','scripts/sandbox-merchant.sh','serve'],cwd=ROOT,env=env,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline = time.monotonic()+10
        while True:
            connection = http.client.HTTPConnection('127.0.0.1',port,timeout=2)
            try:
                connection.request('POST','/purchase',body='{}')
                response = connection.getresponse()
                data = response.read()
                assert response.status == 402 and b'SENTINEL' not in data
                break
            except ConnectionRefusedError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise AssertionError('merchant server did not start')
                time.sleep(.02)
            finally:
                connection.close()
    finally:
        process.terminate()
        stdout,stderr=process.communicate(timeout=5)
        assert 'SENTINEL' not in stdout+stderr
print('Sandbox operators: private setup/permissions, merchant HTTP startup, buyer intake/status and connection-before-issuance denial passed')
