"""OCI acceptance probe: untrusted agent has no network or private mounts."""
import hashlib,hmac,json,os,shutil,socket,subprocess,tempfile,time,urllib.request,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DOCKER=os.environ.get('DOCKER_BIN','docker')
name='payments-boundary-'+uuid.uuid4().hex[:10]
canary='PAYMENTS_VAULT_CANARY_'+uuid.uuid4().hex
token='T'+uuid.uuid4().hex+uuid.uuid4().hex

def docker(*args,timeout=30,check=True):
    result=subprocess.run([DOCKER,*args],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
    if check and result.returncode != 0:
        raise AssertionError(f'Docker {args[0]} failed with status {result.returncode}; raw arguments and output withheld')
    return result
with tempfile.TemporaryDirectory(prefix='payments-boundary-') as tmp:
    private=Path(tmp)/'private';private.mkdir(mode=0o777);private.chmod(0o777)
    # The writable bind is exclusive to the trusted service container.
    # These test fixture permissions do not prescribe production vault permissions.
    (private/'provider-secret').write_text(canary);(private/'provider-secret').chmod(0o444)
    settings={'schema':'kujo.payment-service/v1','bind':'0.0.0.0','port':8000,'database':'/private/state.db','namespace':'containment-test','currency_table':{'version':'test-v1','exponents':{'USD':2}},'credentials':[{'verifier':hmac.new(token.encode(),b'kujo.payments.transport/v1',hashlib.sha256).hexdigest(),'principal':{'type':'user','id':'agent','tenant_id':'test'},'operations':['request','inspect'],'disabled':False,'expires_at_ms':4102444800000}]}
    (private/'config.json').write_text(json.dumps(settings));(private/'config.json').chmod(0o444)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    created=False
    try:
        docker('network','create','--internal',name);created=True
        seed=docker('run','--rm','--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','65532:65532','--pids-limit','64','--memory','256m','--mount',f'type=bind,src={private},dst=/private','--mount',f'type=bind,src={ROOT / "tests/network/credential_vault_seed.kujo"},dst=/app/seed.kujo,readonly','--mount',f'type=bind,src={ROOT / "tests/fixtures/domain.json"},dst=/app/domain.json,readonly','--env','PAYMENTS_PROVIDER_SECRET='+canary,'--entrypoint','/usr/local/bin/kujo','kujo-payments-gateway:local','run','/app/seed.kujo','--interpreter')
        assert json.loads(seed.stdout)=={'ok':True}
        assert canary not in seed.stdout+seed.stderr
        docker('run','-d','--name',name,'--network',name,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','65532:65532','--pids-limit','64','--memory','512m','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=16m','--mount',f'type=bind,src={private},dst=/private','--env','PAYMENTS_SERVICE_CONFIG=/private/config.json','--env','PAYMENTS_PROVIDER_SECRET='+canary,'--env','KUJO_HTTP_SERVER_READ_TIMEOUT_MS=500','kujo-payments-gateway:local')
        deadline=time.monotonic()+20
        while 'Server listening on' not in docker('logs',name).stdout:
            assert time.monotonic()<deadline,'service startup timeout'
            state=docker('inspect',name,'--format','{{.State.Status}}').stdout.strip()
            assert state=='running',docker('logs',name).stdout+docker('logs',name).stderr
            time.sleep(.1)
        docker('exec',name,'/bin/sh','-c','test -r /private/provider-secret && test -r /private/link-vault.db && test -r /private/link-approval-outbox.db && test -r /private/operator-approval.json && test -n "$PAYMENTS_PROVIDER_SECRET"')
        # Separate trusted harness reaches the service on the private Docker network.
        # Its scoped request token never enters the hostile workload.
        harness=docker('run','--rm','--network',name,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','65532:65532','--memory','256m','--pids-limit','64','--env','KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS=true','--env','PAYMENTS_SERVICE_URL=http://'+name+':8000','--env','PAYMENTS_HARNESS_TOKEN='+token,'kujo-payments-harness-probe:local',timeout=15)
        summary=json.loads(harness.stdout.strip())
        assert summary['result']['status']=='awaiting_authorization'
        probe=docker('run','--rm','--network','none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','65532:65532','--pids-limit','64','--memory','256m','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=16m','--env','KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS=true','kujo-payments-agent-probe:local',timeout=20)
        assert json.loads(probe.stdout.strip())['ok'] is True,(probe.stdout,probe.stderr)
        for output in [probe.stdout,probe.stderr,harness.stdout,harness.stderr,docker('logs',name).stdout,json.dumps(summary)]:
            assert canary not in output and token not in output
        workcell_evidence=None
        if os.environ.get('PAYMENTS_WORKCELL_ROOT'):
            image_digest=docker('image','inspect','kujo-payments-workcell-agent:local','--format','{{.Id}}').stdout.strip()
            workcell_output=Path(tmp)/'workcell'
            command=['python3','examples/workcell/run.py','--workcell-root',os.environ['PAYMENTS_WORKCELL_ROOT'],'--runtime',os.environ['PAYMENTS_WORKCELL_KUJO'],'--image-digest',image_digest,'--output',str(workcell_output)]
            workcell=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=150)
            assert workcell.returncode==0,(workcell.stdout,workcell.stderr)
            emitted=json.loads(workcell.stdout);assert emitted['ok'] and emitted['verified']
            # Receipt verification establishes artifact integrity, not payment
            # authorization. The server independently validates this untrusted intent.
            host=docker('run','--rm','--network',name,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user','65532:65532','--memory','256m','--pids-limit','64','--env','KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS=true','--env','PAYMENTS_SERVICE_URL=http://'+name+':8000','--env','PAYMENTS_HARNESS_TOKEN='+token,'--env','PAYMENTS_INTENT_JSON='+json.dumps(emitted['intent']),'kujo-payments-harness-probe:local',timeout=15)
            observed=json.loads(host.stdout);assert observed['result']['status']=='awaiting_authorization'
            assert observed['result']['execution_id']!=summary['result']['execution_id']
            for file in workcell_output.rglob('*'):
                if file.is_file():
                    for secret in [canary,token]: assert secret.encode() not in file.read_bytes(),file.name
            for text in [workcell.stdout,workcell.stderr,host.stdout,host.stderr]:
                assert canary not in text and token not in text
            workcell_receipt=Path(emitted['receipt_path'])
            workcell_evidence={'source':json.loads((ROOT/'examples/workcell/source.lock.json').read_text()),'image':image_digest,'run_id':emitted['workcell_run_id'],'receipt_sha256':hashlib.sha256(workcell_receipt.read_bytes()).hexdigest(),'verified':True,'runtime_sha256':emitted['runtime_sha256'],'payment_execution_id':observed['result']['execution_id']}
            preserved=os.environ.get('PAYMENTS_WORKCELL_EVIDENCE')
            if preserved: shutil.copytree(workcell_output,Path(preserved))
            print('Workcell composition passed: isolated hostile probes, verified intent artifact, separate trusted intake and zero credential evidence leakage')
        # Neither service nor agent runs privileged, shares the host PID namespace, or mounts the engine socket.
        info=json.loads(docker('inspect',name).stdout)[0]
        assert info['HostConfig']['Privileged'] is False
        assert info['HostConfig']['PidMode']!='host'
        assert info['HostConfig']['ReadonlyRootfs'] is True
        assert info['Config']['User']=='65532:65532'
        assert all(m['Destination']!='/var/run/docker.sock' for m in info['Mounts'])
        receipt={'ok':True,'runtime':json.loads((ROOT/'deployment/runtime.lock.json').read_text()),'gateway_image':docker('image','inspect','kujo-payments-gateway:local','--format','{{.Id}}').stdout.strip(),'agent_image':docker('image','inspect','kujo-payments-agent-probe:local','--format','{{.Id}}').stdout.strip(),'docker_server':docker('version','--format','{{.Server.Version}}').stdout.strip(),'profile':'linux-amd64 OCI; agent network none; no shared credentials/mounts/PID/engine sockets','private_canary_positive_control':True,'private_credential_vault_positive_control':True,'private_approval_outbox_positive_control':True,'private_reviewed_operator_sink_positive_control':True,'probes':json.loads(probe.stdout.strip()),'scope':'Synthetic credential canary and HTTP intake. No live provider or kernel-escape proof.'}
        if workcell_evidence:
            receipt['workcell']=workcell_evidence
            preserved=os.environ.get('PAYMENTS_WORKCELL_EVIDENCE')
            if preserved: (Path(preserved)/'boundary.json').write_text(json.dumps(receipt,indent=2)+'\n')
        evidence=os.environ.get('PAYMENTS_CONTAINMENT_RECEIPT')
        if evidence:Path(evidence).write_text(json.dumps(receipt,indent=2)+'\n')
        print('OCI containment passed: credential files/env/processes, sockets, command access, symlinks and network denied; trusted intake works')
    finally:
        docker('rm','-f',name,check=False)
        if created:docker('network','rm',name,check=False)
