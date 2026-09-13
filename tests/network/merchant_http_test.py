"""Real native HTTP port against loopback-only synthetic merchant; no money."""
import base64,hashlib,json,os,subprocess,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
KUJO=os.environ['KUJO_BIN']
vector=json.loads((ROOT/'tests/fixtures/mpp.json').read_text())['cases'][0]
requests=[]
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):self.respond()
    def do_POST(self):self.respond()
    def respond(self):
        body=self.rfile.read(int(self.headers.get('Content-Length','0')))
        requests.append((self.path,{k.lower():v for k,v in self.headers.items()},body))
        credential=self.headers.get('Authorization')
        if self.path.startswith('/redirect') or (self.path=='/paid-redirect' and credential):
            self.send_response(302);self.send_header('Location','http://127.0.0.1:1/forbidden');self.end_headers();return
        if credential:
            assert credential==vector['credential']
            self.send_response(200);self.end_headers();self.wfile.write(b'SENTINEL_MERCHANT_RESPONSE');return
        self.send_response(402)
        self.send_header('WWW-Authenticate',vector['header'])
        if self.path=='/duplicate':self.send_header('WWW-Authenticate',vector['header'])
        self.end_headers()
        try:self.wfile.write(b'x'*40000 if self.path=='/large' else b'ignored')
        except (BrokenPipeError,ConnectionResetError):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
def run(path,body='',fixture=True,expired=False):
    env={**os.environ,'KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS':'true','PAYMENTS_MERCHANT_URL':f'http://127.0.0.1:{server.server_port}{path}','PAYMENTS_MERCHANT_FIXTURE':'1' if fixture else '0','PAYMENTS_MERCHANT_BODY':body,'PAYMENTS_MERCHANT_EXPIRED':'1' if expired else '0'}
    p=subprocess.run([KUJO,'run','tests/network/merchant.kujo','--interpreter'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert 'SENTINEL' not in p.stdout+p.stderr
    return json.loads(p.stdout)
try:
    a=run('/purchase');assert a['probe_status']==402 and not a['pay_failed'],a
    assert len(requests)==2 and 'authorization' not in requests[0][1] and requests[1][1]['authorization']==vector['credential']
    count=len(requests);assert not run('/purchase',fixture=False)['ok'];assert len(requests)==count
    assert run('/purchase',expired=True)['probe_status']==0;assert len(requests)==count
    for path in ('/redirect','/duplicate','/large'):
        count=len(requests);assert run(path)['probe_status']==0;assert len(requests)==count+1
    assert run('/paid-redirect')['pay_failed']
    body='{"order":"café"}'
    b=run('/post',body=body)
    assert b['body_digest']=='sha-256='+base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
    assert requests[-1][2]==requests[-2][2]==body.encode()
    c=run('/purchase?order=changed');assert c['binding_digest']!=a['binding_digest']
    assert all('cookie' not in h for _,h,_ in requests)
finally:
    server.shutdown();server.server_close();thread.join(timeout=3)
print('Native merchant HTTP: immutable request/body binding, private credential, duplicate-header/redirect/size/deadline denial and sanitized output passed')
