"""Run the no-credential agent example; return verified intent evidence only."""
import argparse,hashlib,json,os,re,stat,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=Path(__file__).resolve().parent
PIN=json.loads((EXAMPLE/'source.lock.json').read_text())
def run_workload(args,source,environment,cancel_file):
    """Give Workcell a bounded opportunity to cancel and record owned cleanup."""
    process=subprocess.Popen(args,cwd=source,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        stdout,_=process.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        cancel_file.write_text('operator deadline\n')
        try:
            process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();process.communicate(timeout=5)
            raise RuntimeError('Workcell cancellation did not finish; cleanup is unconfirmed; inspect retained run ownership evidence') from None
        raise RuntimeError('Workcell deadline exceeded; inspect retained cancellation and cleanup receipt') from None
    if process.returncode!=0:
        raise RuntimeError('Workcell execution failed; inspect retained evidence')
    return stdout
def execute(workcell,runtime,image_digest,output):
    assert re.fullmatch(r'sha256:[a-f0-9]{64}',image_digest)
    environment={k:os.environ[k] for k in ['PATH','HOME','DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'] if k in os.environ}
    environment['KUJO']=str(runtime)
    def run(args,cwd=None,timeout=90):
        value=subprocess.run(args,cwd=cwd,env=environment,capture_output=True,text=True,timeout=timeout)
        if value.returncode!=0: raise RuntimeError(f'Workcell composition command failed ({value.returncode}); inspect retained evidence')
        return value.stdout
    assert run(['git','-C',str(workcell),'rev-parse','HEAD']).strip()==PIN['workcell_commit']
    assert run(['git','-C',str(workcell),'status','--porcelain']).strip()==''
    assert run([str(runtime),'--version']).strip()==PIN['runtime_version']
    with tempfile.TemporaryDirectory(prefix='payments-workcell-source-') as directory:
        source=Path(directory)
        (source/'agent.kujo').write_bytes((EXAMPLE/'agent.kujo').read_bytes())
        (source/'probe.kujo').write_bytes((ROOT/'tests/network/agent_probe.kujo').read_bytes())
        run(['git','init','--template=',str(source)])
        run(['git','add','agent.kujo','probe.kujo'],source)
        run(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgSign=false','-c','user.name=Payments Fixture','-c','user.email=fixture@example.invalid','commit','-m','Immutable public agent fixture'],source)
        definition=json.loads((EXAMPLE/'definition.template.json').read_text());definition['runtime']['image_digest']=image_digest
        output.mkdir(parents=True,exist_ok=True,mode=0o700)
        mode=output.stat();assert mode.st_uid==os.getuid() and stat.S_IMODE(mode.st_mode)&0o077==0,'Private owned evidence directory required'
        definition_path=output/'definition.json';definition_path.write_text(json.dumps(definition))
        cli=str(workcell/'bin/workcell')
        run([cli,'validate','--file',str(definition_path),'--json'],source)
        cancel_file=output/'cancel.request'
        assert not cancel_file.exists(),'Use a fresh output directory after cancellation'
        summary=json.loads(run_workload([cli,'run','--file',str(definition_path),'--repo',str(source),'--output',str(output/'runs'),'--cancel-file',str(cancel_file),'--no-pull','--summary'],source,environment,cancel_file))
        assert summary['schema_version']=='workcell-run-summary/v1' and summary['ok']
        run_dir=Path(summary['output_dir']).resolve();assert output.resolve() in run_dir.parents
        verified=json.loads(run([cli,'verify','--run',str(run_dir),'--json'],source));assert verified['ok']
        artifact=run_dir/'artifacts/intent.json';assert artifact.is_file() and not artifact.is_symlink() and artifact.stat().st_size<=8192
        intent=json.loads(artifact.read_text())
        return {'ok':True,'workcell_run_id':summary['run_id'],'receipt_path':summary['receipt_path'],'output_dir':str(run_dir),'intent':intent,'verified':True,'runtime_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest()}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workcell-root',type=Path,required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--image-digest',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(execute(args.workcell_root.resolve(),args.runtime.resolve(),args.image_digest,args.output.resolve())))
