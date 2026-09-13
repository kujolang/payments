"""Install exact Workcell source and build its separately pinned host runtime."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/.workcell'
PIN=json.loads((ROOT/'examples/workcell/source.lock.json').read_text())
def run(args,cwd=None,timeout=180):
    result=subprocess.run(args,cwd=cwd,timeout=timeout,text=True,capture_output=True)
    if result.returncode!=0:
        print(result.stderr[-8192:])
        raise RuntimeError('Pinned Workcell setup failed')
    return result
BASE.mkdir(parents=True,exist_ok=True)
for name,repository,commit in [('workcell','workcell',PIN['workcell_commit']),('runtime','kujo',PIN['runtime_commit'])]:
    path=BASE/name
    if not path.exists():
        run(['git','init',str(path)])
        run(['git','remote','add','origin',f'https://github.com/kujolang/{repository}.git'],path)
        run(['git','fetch','--depth','1','origin',commit],path)
        run(['git','checkout','--detach',commit],path)
    assert run(['git','rev-parse','HEAD'],path).stdout.strip()==commit
    assert run(['git','status','--porcelain'],path).stdout==''
assert (BASE/'workcell/RUNTIME_VERSION').read_text().strip()==PIN['runtime_commit']
run(['cargo','build','--release','--locked','--manifest-path',str(BASE/'runtime/Cargo.toml'),'--bin','kujo'],timeout=1200)
runtime=BASE/'runtime/target/release/kujo'
assert run([str(runtime),'--version']).stdout.strip()==PIN['runtime_version']
(BASE/'build.json').write_text(json.dumps({**PIN,'binary_sha256':hashlib.sha256(runtime.read_bytes()).hexdigest()},indent=2)+'\n')
print('Pinned Workcell source and host Kujo runtime built and verified')
