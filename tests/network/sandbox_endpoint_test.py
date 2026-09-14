"""Real loopback Kujo HTTP server; synthetic merchant callback only."""
import base64
import http.client
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ['KUJO_BIN']
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
process = subprocess.Popen([KUJO, 'run', 'tests/sandbox_endpoint.kujo', '--interpreter'],
                           cwd=ROOT, env={**os.environ, 'PAYMENTS_ENDPOINT_PORT': str(port)},
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def request(body='{}', credential=None, duplicate=False):
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
    try:
        connection.putrequest('POST', '/purchase')
        connection.putheader('Content-Length', str(len(body.encode())))
        connection.putheader('Content-Type', 'application/json')
        if credential:
            connection.putheader('Authorization', credential)
            if duplicate:
                connection.putheader('Authorization', credential)
        connection.endheaders(body.encode())
        response = connection.getresponse()
        data = response.read()
        assert b'SENTINEL' not in data
        return response.status, dict(response.getheaders()), data
    finally:
        connection.close()

try:
    deadline = time.monotonic() + 10
    while True:
        try:
            status, headers, data = request()
            break
        except (ConnectionRefusedError, ConnectionResetError):
            if process.poll() is not None or time.monotonic() >= deadline:
                raise AssertionError('HTTP fixture did not start')
            time.sleep(.02)
    assert status == 402, (status, data)
    normalized = {k.lower(): v for k, v in headers.items()}
    assert normalized['cache-control'] == 'no-store'
    challenge = dict(re.findall(r'(\w+)="([^"]*)"', normalized['www-authenticate']))
    payload = json.dumps({'challenge': challenge, 'payload': {'spt': 'spt_SENTINEL'}},
                         sort_keys=True, separators=(',', ':')).encode()
    credential = 'Payment ' + base64.urlsafe_b64encode(payload).decode().rstrip('=')
    assert request(body='changed', credential=credential)[0] == 400
    supported = os.environ.get('PAYMENTS_HEADER_VALUES_RUNTIME') == '1'
    assert request(credential='Payment invalid')[0] == (400 if supported else 503)
    status, _, data = request(credential=credential)
    if supported:
        assert status == 202 and json.loads(data)['code'] == 'payment_recorded', (status, data)
    else:
        assert status == 503 and json.loads(data)['code'] == 'runtime_header_values_required', (status, data)
    status, _, data = request(credential=credential, duplicate=True)
    assert status == (400 if supported else 503), ('duplicate Authorization admitted', status, data)
finally:
    process.terminate()
    stdout, stderr = process.communicate(timeout=5)
    assert 'SENTINEL' not in stdout + stderr
print('Sandbox HTTP endpoint: supported-runtime recording and duplicate denial passed' if supported else 'Sandbox HTTP endpoint: v1.4.0 credential execution refused; challenge and response/log suppression passed')
