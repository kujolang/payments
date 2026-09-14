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
print('Sandbox operator: offline check, private-file/live-key denial, missing-claim recovery and real uncredentialed HTTP startup passed')
