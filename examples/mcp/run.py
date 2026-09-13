"""Stage public Kujo client code and launch the optional MCP STDIO frontend."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='payments-mcp-harness-') as directory:
    stage=Path(directory)
    for name in ['project.kujo','call.kujo','kennel.toml','kennel.lock']:
        shutil.copyfile(EXAMPLE/name,stage/name)
    shutil.copytree(EXAMPLE/'kennel_packages',stage/'kennel_packages')
    (stage/'contracts/abilities').mkdir(parents=True)
    for name in ['request','inspect']:
        shutil.copyfile(ROOT/f'contracts/abilities/{name}.json',stage/f'contracts/abilities/{name}.json')
    for name,target in [('http','payments_http'),('client','payments_client')]:
        shutil.copyfile(ROOT/f'src/client/{name}.kujo',stage/f'{target}.kujo')
    allowed=['PATH','KUJO_BIN','PAYMENTS_CLIENT_ENDPOINT','PAYMENTS_CLIENT_TOKEN','PAYMENTS_LOCAL_FIXTURE']
    environment={k:os.environ[k] for k in allowed if k in os.environ}
    environment['PAYMENTS_MCP_STAGE']=str(stage)
    if environment.get('PAYMENTS_LOCAL_FIXTURE')=='true': environment['KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS']='true'
    node=shutil.which('node')
    if node is None: raise SystemExit('Node runtime required')
    process=subprocess.Popen([node,'--max-old-space-size=128',str(EXAMPLE/'server.mjs')],cwd=stage,env=environment,start_new_session=True)
    def interrupted(signum,frame): raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    try:
        raise SystemExit(process.wait())
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait()

