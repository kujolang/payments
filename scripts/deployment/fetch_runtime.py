"""Fetch only the explicitly pinned build runtime; never run at payment execution time."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import urllib.request

MAX_ARCHIVE = 128 * 1024 * 1024
MAX_BINARY = 256 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def cached_digest(path):
    # A corrupt or replaced cache must not cause an unbounded allocation.
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BINARY:
                return None
            digest.update(chunk)
    return digest.hexdigest()


root = Path(__file__).resolve().parents[2]
lock = json.loads((root / 'deployment/runtime.lock.json').read_text())
target = root / 'deployment/.runtime/kujo'
require(not target.is_symlink() and not target.parent.is_symlink(),
        'runtime path must not be a symlink')
if target.is_file() and cached_digest(target) == lock['binary_sha256']:
    target.chmod(0o755)
    print('Verified cached pinned Kujo runtime')
    raise SystemExit(0)
with urllib.request.urlopen(lock['url'], timeout=60) as response:
    data = response.read(MAX_ARCHIVE + 1)
require(len(data) <= MAX_ARCHIVE, 'runtime archive too large')
require(hashlib.sha256(data).hexdigest() == lock['archive_sha256'], 'archive checksum mismatch')
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    members = [m for m in archive.getmembers() if m.isfile() and Path(m.name).name == 'kujo']
    require(len(members) == 1 and members[0].size <= MAX_BINARY, 'invalid runtime archive members')
    binary = archive.extractfile(members[0]).read(MAX_BINARY + 1)
require(len(binary) <= MAX_BINARY and hashlib.sha256(binary).hexdigest() == lock['binary_sha256'],
        'binary checksum mismatch')
target.parent.mkdir(parents=True, exist_ok=True)
# Preserve the prior cache on write failure; readers see only complete binaries.
# This is an operator-owned build directory, not an isolation boundary against
# another process running as the same user or replacing ancestor directories.
staged = None
try:
    with tempfile.NamedTemporaryFile(prefix='.kujo-', dir=target.parent, delete=False) as stream:
        staged = Path(stream.name)
        stream.write(binary)
        stream.flush()
        os.fchmod(stream.fileno(), 0o755)
        os.fsync(stream.fileno())
    os.replace(staged, target)
finally:
    if staged is not None:
        staged.unlink(missing_ok=True)
print('Verified pinned Kujo runtime prepared for image build')
