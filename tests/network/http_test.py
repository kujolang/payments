"""Real-process request/status transport tests; synthetic application tokens only."""
import hashlib,hmac,json,os,socket,sqlite3,subprocess,tempfile,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def digest(token):
    return hmac.new(token.encode(),b'kujo.payments.transport/v1',hashlib.sha256).hexdigest()
def exchange(port,token,value,content_type='application/json',path='/v1/payments'):
    body=value if isinstance(value,bytes) else json.dumps(value).encode()
    request=urllib.request.Request(f'http://127.0.0.1:{port}{path}',body,headers={'Authorization':'Bearer '+token,'Content-Type':content_type})
    try:
        with urllib.request.urlopen(request,timeout=4) as response: return response.status,response.read(),dict(response.headers)
    except urllib.error.HTTPError as e: return e.code,e.read(),dict(e.headers)
with tempfile.TemporaryDirectory(prefix='payments-http-') as tmp:
    root=Path(tmp)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    token='a'*64;other='b'*64;expired='c'*64
    credentials=[]
    for secret,tenant,expiry in [(token,'one',4102444800000),(other,'two',4102444800000),(expired,'one',1)]:
        credentials.append({'verifier':digest(secret),'principal':{'type':'user','id':'user','tenant_id':tenant},'operations':['request','inspect'],'disabled':False,'expires_at_ms':expiry})
    settings={'schema':'kujo.payment-service/v1','bind':'127.0.0.1','port':port,'database':str(root/'payments.db'),'namespace':'test-installation','currency_table':{'version':'test-v1','exponents':{'USD':2}},'credentials':credentials}
    (root/'config.json').write_text(json.dumps(settings))
    env={**os.environ,'PAYMENTS_SERVICE_CONFIG':str(root/'config.json'),'KUJO_HTTP_SERVER_READ_TIMEOUT_MS':'500'}
    process=subprocess.Popen([os.environ['KUJO_BIN'],'run','src/executor/gateway.kujo','--interpreter'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+15
        while True:
            if process.poll() is not None: raise AssertionError(process.communicate())
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1): break
            except OSError:
                assert time.monotonic()<deadline,'gateway startup timeout';time.sleep(.05)
        purchase={'operation':'request','idempotency_key':'key','input':{'purchase_ref':'order','payee_ref':'merchant','amount':{'mode':'maximum','minor':5500,'currency':'USD'},'purpose':'Synthetic purchase','payment_profile':'default','expires_in_ms':60000}}
        status,body,headers=exchange(port,token,purchase)
        assert status==200,(status,body)
        result=json.loads(body)['result'];eid=result['execution_id']
        assert headers['Cache-Control']=='no-store'
        lookup={'operation':'inspect','input':{'execution_id':eid}}
        assert exchange(port,token,lookup)[0]==200
        assert exchange(port,other,lookup)[0]==409
        assert exchange(port,expired,lookup)[0]==401
        assert exchange(port,'d'*64,lookup)[0]==401
        assert exchange(port,token,{'operation':'execute','input':{}})[0]==403
        assert exchange(port,token,{**lookup,'principal':credentials[0]['principal']})[0]==409
        assert exchange(port,token,b'{'*9000)[0]==400
        assert exchange(port,token,lookup,'text/plain')[0]==415
        assert exchange(port,token,lookup,path='/execute')[0]==404
        exponent=json.dumps(purchase).replace('5500','5500e0').replace('"key"','"exponent"').encode()
        assert exchange(port,token,exponent)[0]==409,'lexical floating money rejected'
        assert exchange(port,token,purchase)[1]==body,'request replay'
        with sqlite3.connect(root/'payments.db') as db:
            assert db.execute('SELECT count(*) FROM executions').fetchone()[0]==1
            assert db.execute('SELECT count(*) FROM audit').fetchone()[0]>0
        # Domain binding must reject changed terms even if a lower-layer replay
        # receipt is otherwise valid. Cover every scalar and amount component.
        changes=[('purchase_ref','other-order'),('payee_ref','other-merchant'),
                 ('purpose','Changed direct request'),('payment_profile','other'),
                 ('expires_in_ms',120000),('shipping_profile','home'),('provider_preference','link'),
                 ('amount',{'mode':'maximum','minor':5501,'currency':'USD'}),
                 ('amount',{'mode':'exact','minor':5500,'currency':'USD'}),
                 ('amount',{'mode':'maximum','minor':5500,'currency':'JPY'})]
        for field,value in changes:
            altered={**purchase,'input':{**purchase['input'],field:value}}
            assert exchange(port,token,altered)[0]==409,field
        client_env={**env,'KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS':'true','PAYMENTS_CLIENT_ENDPOINT':f'http://127.0.0.1:{port}/v1/payments','PAYMENTS_CLIENT_TOKEN':token}
        client=subprocess.run([os.environ['KUJO_BIN'],'run','tests/network/client.kujo','--interpreter'],cwd=ROOT,env=client_env,capture_output=True,text=True,timeout=10,check=True)
        assert json.loads(client.stdout)['ok'] is True
        assert token not in client.stdout+client.stderr
        sdk_env={**client_env,'PAYMENTS_LOCAL_FIXTURE':'true','PAYMENTS_PURCHASE_JSON':json.dumps({**purchase['input'],'purchase_ref':'sdk-purchase'})}
        sdk=subprocess.run(['python3','examples/agents-sdk/run.py','--conformance'],cwd=ROOT,env=sdk_env,capture_output=True,text=True,timeout=40)
        assert sdk.returncode==0,(sdk.stdout,sdk.stderr)
        sdk_result=json.loads(sdk.stdout)
        assert sdk_result['ok'] and sdk_result['tools']==['purchase_request','purchase_status']
        assert sdk_result['status']['status']=='awaiting_authorization'
        assert token not in sdk.stdout+sdk.stderr and 'SENTINEL_PRIVATE_CALLBACK_SECRET' not in sdk.stdout+sdk.stderr
        mcp_env={**sdk_env,'PAYMENTS_PURCHASE_JSON':json.dumps({**purchase['input'],'purchase_ref':'mcp-purchase'})}
        mcp=subprocess.run(['node','examples/mcp/conformance.mjs'],cwd=ROOT,env=mcp_env,capture_output=True,text=True,timeout=45)
        assert mcp.returncode==0,(mcp.stdout,mcp.stderr)
        mcp_result=json.loads(mcp.stdout);assert mcp_result['ok'] and mcp_result['tools']==['purchase_request','purchase_status']
        assert token not in mcp.stdout+mcp.stderr
        print('MCP measurements: '+json.dumps(mcp_result['metrics'],sort_keys=True))
        # Guard raw wire numbers before the JS MCP SDK can round them. These
        # connections fail closed and must not reach financial intake.
        wire_purchase={**purchase['input'],'purchase_ref':'mcp-invalid-wire'}
        call={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'purchase_request','arguments':wire_purchase}}
        initialize={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'wire-test','version':'1.0.0'}}}
        for number in ['5500.0','55e2','5500.0000000000000000001','9007199254740993']:
            raw=json.dumps(initialize)+'\n'+json.dumps(call).replace('5500',number)+'\n'
            wire=subprocess.run(['python3','examples/mcp/run.py'],cwd=ROOT,env=mcp_env,input=raw,capture_output=True,text=True,timeout=12)
            assert wire.returncode!=0 and 'Invalid or oversized payment MCP frame' in wire.stderr,number
            assert token not in wire.stdout+wire.stderr
        oversized=subprocess.run(['python3','examples/mcp/run.py'],cwd=ROOT,env=mcp_env,input='x'*8193+'\n',capture_output=True,text=True,timeout=12)
        assert oversized.returncode!=0 and 'Invalid or oversized payment MCP frame' in oversized.stderr
        with sqlite3.connect(root/'payments.db') as db:
            assert db.execute('SELECT count(*) FROM executions').fetchone()[0]==4
            assert db.execute('SELECT sum(claimed) FROM executions').fetchone()[0]==0
        # No request tokens may be persisted in any service artifact.
        for file in root.iterdir():
            if file.is_file():
                for secret in [token,other,expired]: assert secret.encode() not in file.read_bytes(),file
    finally:
        process.terminate()
        out,err=process.communicate(timeout=5)
        for secret in [token,other,expired]: assert secret not in out+err
print('HTTP service, pinned Agents SDK and MCP projections: authenticated tenant isolation, hidden operations, bounded input, replay and token non-persistence passed')
