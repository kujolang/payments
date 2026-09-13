"""Pinned native Kennel packaging and real installation; synthetic release only."""
import hashlib,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
KUJO=os.environ['KUJO_BIN'];PIN='546dd4205b90825f3e326336941c3068b1add0f0'
def run(args,cwd=ROOT,env=None,timeout=180):
    p=subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise AssertionError('package fixture command failed: '+p.stdout[-1500:]+p.stderr[-1500:])
    return p.stdout
with tempfile.TemporaryDirectory(prefix='payments-package-') as temporary:
    root=Path(temporary);kennel=root/'kennel';repo=root/'source';repo.mkdir();output=root/'output';output.mkdir()
    run(['git','clone','--no-checkout','--filter=blob:none',os.environ.get('PAYMENTS_KENNEL_ROOT','https://github.com/kujolang/kennel.git'),str(kennel)])
    run(['git','checkout','--detach',PIN],cwd=kennel)
    assert run(['git','rev-parse','HEAD'],cwd=kennel).strip()==PIN
    paths=run(['git','ls-files','-z']).split('\0')
    for name in paths:
        if not name:continue
        source=ROOT/name
        assert source.is_file() and not source.is_symlink(),'nonregular source input'
        target=repo/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    # Deliberately tracked sentinels: the positive allowlist must exclude them,
    # including paths not covered by the publisher's own generic denylist.
    sentinels=['.local/backup.json','tests/package-canary.txt','docs/evidence/package-canary.txt','unrelated.txt','src/.env','src/credential.key']
    for name in sentinels:
        path=repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('PACKAGE_PRIVATE_SENTINEL')
    run(['git','init','-q'],cwd=repo);run(['git','add','-f','.'],cwd=repo)
    run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','synthetic package input'],cwd=repo)
    commit=run(['git','rev-parse','HEAD'],cwd=repo).strip();run(['git','tag','v0.1.0'],cwd=repo)
    data={'repo':str(repo),'commit':commit,'output':str(output),
          'release':{'repository':'kujolang/payments','repository_id':1,'id':1,'draft':False,'prerelease':False,'tag_name':'v0.1.0','published_at':'2026-09-13T00:00:00Z'},
          'policy':{'schema_version':1,'packages':{'payments':{'repository':'kujolang/payments','repository_id':1,'official':True,'enabled':True}}},
          'workflow':{'run':'https://example.invalid/synthetic-package-fixture','ref':'fixture','sha':commit,'published_at':'2026-09-13T00:00:00Z'}}
    settings=root/'settings.json';settings.write_text(json.dumps(data));script=root/'package.kujo'
    script.write_text('''from src.registry_package import package_build
from src.registry_archive import extract_registry_archive
value := parse_json(read_file(env("PAYMENTS_PACKAGE_SETTINGS")))
built := package_build(value["repo"],value["commit"],value["release"],value["policy"],value["workflow"],"https://example.invalid")
again := package_build(value["repo"],value["commit"],value["release"],value["policy"],value["workflow"],"https://example.invalid")
assert(built == again,"non_deterministic_package")
for name in keys(built["artifacts"]) { io_write_bytes(value["output"]+"/"+name,built["artifacts"][name]) }
extract_registry_archive(built["artifacts"]["package.tar.gz"],value["output"]+"/extracted",built["metadata"]["file_count"])
print("native package and extraction passed")
''')
    env={**os.environ,'KUJO_MODULE_PATH':str(kennel),'PAYMENTS_PACKAGE_SETTINGS':str(settings)}
    run([KUJO,'run',str(script),'--interpreter','--isolated-imports'],env=env)
    archive=output/'package.tar.gz';metadata=json.loads((output/'manifest.json').read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==metadata['archive_sha256']
    with tarfile.open(archive) as tar:
        names=tar.getnames()
        assert len(names)==metadata['file_count'] and not any(n in names for n in sentinels)
        for member in tar:
            assert member.isfile() and 'PACKAGE_PRIVATE_SENTINEL' not in tar.extractfile(member).read().decode(errors='ignore')
        for required in ['kennel.toml','kennel.lock','LICENSE','payments.kujo','payments_http.kujo','src/client/client.kujo','src/client/http.kujo','contracts/abilities/inspect.json']:
            assert required in names,'required package file missing: '+required
    consumer=root/'consumer';consumer.mkdir()
    run([KUJO,'run',str(kennel/'kennel.kujo'),'--interpreter','--','init','--name','payment-consumer','--project-dir',str(consumer)])
    run([KUJO,'run',str(kennel/'kennel.kujo'),'--interpreter','--','add','file:'+str(output/'extracted'),'--alias','payments','--project-dir',str(consumer)])
    run([KUJO,'run',str(kennel/'kennel.kujo'),'--interpreter','--','validate','--project-dir',str(consumer)])
    installed=consumer/'kennel_packages/payments'
    assert (installed/'payments.kujo').read_bytes()==(ROOT/'payments.kujo').read_bytes()
    clean_env={k:v for k,v in os.environ.items() if k not in ['KUJO_MODULE_PATH','KUJO_IMPORT_PATH']}
    for module in ['payments']:
        sample=consumer/'main.kujo'
        sample.write_text('from '+module+''' import purchase_request, purchase_status, purchase_inspect_revision, purchase_cancel
transport := func(request) { return request }
assert(purchase_request(transport,{"purchase_ref":"demo"},"key")["operation"]=="request","request")
assert(purchase_status(transport,"execution")["operation"]=="inspect","status")
assert(purchase_inspect_revision(transport,"execution")["operation"]=="inspect_revision","revision")
assert(purchase_cancel(transport,"execution",3,"key")["input"]["expected_revision"]==3,"cancel")
print("installed client passed")
''')
        for suffix in [[],['--interpreter']]:run([KUJO,'run',str(sample),*suffix],cwd=consumer,env=clean_env,timeout=30)
    sample.write_text('''from payments_http import http_transport
transport := http_transport("http://127.0.0.1:19876/v1/payments",repeat("x",64),{},true)
assert(type(transport)=="function","installed_http_factory")
print("installed HTTP transport factory passed; no network call")
''')
    for suffix in [[],['--interpreter']]:run([KUJO,'run',str(sample),*suffix],cwd=consumer,env=clean_env,timeout=30)
    print('Package installation: deterministic native archive, private-path exclusion, real Kennel install/validate and two client imports in VM/interpreter passed; '+str(len(names))+' files, '+str(archive.stat().st_size)+' archive bytes')
