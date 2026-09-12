"""Fetch only the explicitly pinned build runtime; never run at payment execution time."""
import hashlib,io,json,tarfile,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[2]
lock=json.loads((root/'deployment/runtime.lock.json').read_text())
target=root/'deployment/.runtime/kujo'
assert not target.is_symlink() and not target.parent.is_symlink(), 'runtime path must not be a symlink'
if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==lock['binary_sha256']:
    print('Verified cached pinned Kujo runtime')
    raise SystemExit(0)
with urllib.request.urlopen(lock['url'],timeout=60) as response:
    data=response.read(128*1024*1024+1)
assert len(data)<=128*1024*1024,'runtime archive too large'
assert hashlib.sha256(data).hexdigest()==lock['archive_sha256'],'archive checksum mismatch'
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
    members=[m for m in archive.getmembers() if m.isfile() and Path(m.name).name=='kujo']
    assert len(members)==1 and members[0].size<=256*1024*1024
    binary=archive.extractfile(members[0]).read()
assert hashlib.sha256(binary).hexdigest()==lock['binary_sha256'],'binary checksum mismatch'
target=root/'deployment/.runtime/kujo';target.parent.mkdir(parents=True,exist_ok=True)
target.write_bytes(binary);target.chmod(0o755)
print('Verified pinned Kujo runtime prepared for image build')
