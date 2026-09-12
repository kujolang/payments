import subprocess,tempfile,os,json,stat
from pathlib import Path
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as tmp:
    private=Path(tmp)/'new'
    env={**os.environ,'PAYMENTS_PROVISION_DIR':str(private),'PAYMENTS_PRINCIPAL_JSON':json.dumps({'type':'user','id':'operator','tenant_id':'test'})}
    result=subprocess.run(['bash','scripts/provision.sh'],cwd=root,env=env,capture_output=True,text=True,check=True)
    token=(private/'client-token').read_text()
    assert token not in result.stdout+result.stderr
    assert stat.S_IMODE(private.stat().st_mode)==0o700
    for name in ['client-token','service.json']:
        assert stat.S_IMODE((private/name).stat().st_mode)&0o077==0
    assert subprocess.run(['bash','scripts/provision.sh'],cwd=root,env=env,capture_output=True).returncode!=0
print('Provisioning: private permissions, token suppression and overwrite refusal passed')
