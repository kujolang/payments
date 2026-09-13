"""Run the trusted Dispatch composition with only public Payments client modules."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='payments-dispatch-harness-') as directory:
    stage=Path(directory)
    for name in ['main.kujo','workflow.kujo','kennel.toml','kennel.lock']:
        shutil.copyfile(EXAMPLE/name,stage/name)
    shutil.copytree(EXAMPLE/'kennel_packages',stage/'kennel_packages')
    (stage/'contracts/abilities').mkdir(parents=True)
    shutil.copyfile(ROOT/'contracts/abilities/request.json',stage/'contracts/abilities/request.json')
    for source,target in [('http','payments_http'),('client','payments_client')]:
        shutil.copyfile(ROOT/f'src/client/{source}.kujo',stage/f'{target}.kujo')
    allowed=['PATH','PAYMENTS_CLIENT_ENDPOINT','PAYMENTS_CLIENT_TOKEN','PAYMENTS_PURCHASE_JSON',
             'PAYMENTS_LOCAL_FIXTURE','PAYMENTS_DISPATCH_OUTPUT','PAYMENTS_DISPATCH_RUN_ID']
    environment={key:os.environ[key] for key in allowed if key in os.environ}
    environment['DISPATCH_OFFLINE_FIXTURE']='true'
    environment['DISPATCH_ALLOW_ANY_OUTPUT_ROOT']='true'
    if environment.get('PAYMENTS_LOCAL_FIXTURE')=='true':
        environment['KUJO_ALLOW_PRIVATE_NETWORK_DESTINATIONS']='true'
    # No model bridge or provider credential environment is inherited.
    result=subprocess.run([os.environ['KUJO_BIN'],'run','main.kujo'],cwd=stage,env=environment,timeout=30)
    raise SystemExit(result.returncode)
