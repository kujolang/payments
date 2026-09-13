"""Stage only public client code with the pinned SDK for a trusted harness run."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--conformance',action='store_true')
args=parser.parse_args()
with tempfile.TemporaryDirectory(prefix='payments-sdk-harness-') as directory:
    stage=Path(directory)
    for name in ['main.kujo','conformance.kujo','tools.kujo','kennel.toml','kennel.lock']:
        shutil.copyfile(EXAMPLE/name,stage/name)
    shutil.copytree(EXAMPLE/'kennel_packages',stage/'kennel_packages')
    (stage/'contracts/abilities').mkdir(parents=True)
    for name in ['request','inspect']:
        shutil.copyfile(ROOT/f'contracts/abilities/{name}.json',stage/f'contracts/abilities/{name}.json')
    shutil.copyfile(ROOT/'src/client/http.kujo',stage/'payments_http.kujo')
    shutil.copyfile(ROOT/'src/client/client.kujo',stage/'payments_client.kujo')
    result=subprocess.run([os.environ['KUJO_BIN'],'run','conformance.kujo' if args.conformance else 'main.kujo','--interpreter'],cwd=stage,timeout=30)
    raise SystemExit(result.returncode)
