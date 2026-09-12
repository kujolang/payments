#!/usr/bin/env python3
"""Static import discipline plus real Fence mutation tests; no runtime isolation claim."""
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
KUJO = os.environ['KUJO_BIN']
FENCE = ROOT / 'tools/kennel_packages/fence/fence.kujo'
PIN = 'fda049ed9aa55ba50c150b84bb9ca1bdf49af0dc'
def read_toml(path):
    result = subprocess.run([KUJO, 'run', str(ROOT / 'scripts/read_toml.kujo')],
                            env={**os.environ, 'PAYMENTS_TEST_TOML': str(path)},
                            capture_output=True, text=True, timeout=15, check=True)
    return json.loads(result.stdout)

lock = read_toml(ROOT / 'tools/kennel.lock')
assert any(p['name'] == 'fence' and p['resolved_commit'] == PIN for p in lock['package'])
assert FENCE.is_file(), 'Install tools/kennel.toml with Kennel first'


def discipline(root):
    """Close Fence's default external allow and unclassified-source gaps."""
    config = read_toml(root / 'fence.toml')
    for path in (root / 'src').rglob('*.kujo'):
        rel = path.relative_to(root).as_posix()
        matches = [name for name, z in config['zones'].items()
                   if any(fnmatch.fnmatchcase(rel, pattern) for pattern in z['paths'])]
        assert len(matches) == 1, f'Unclassified/ambiguous source: {rel}'
        for line in path.read_text().splitlines():
            source = line.split('//', 1)[0].strip()
            if not re.match(r'^(from|import)\b', source):
                continue
            match = re.fullmatch(r'from ([A-Za-z_][A-Za-z0-9_.]*) import [A-Za-z_][A-Za-z0-9_]*(?:, *[A-Za-z_][A-Za-z0-9_]*)*', source)
            assert match, f'Use auditable single-line from imports: {rel}'
            module = match[1]
            if module.startswith('src.'):
                assert (root / (module.replace('.', '/') + '.kujo')).is_file(), f'Unresolved import: {rel}'
            else:
                assert module == 'ability' and matches[0] in ('application', 'gateway'), f'External import forbidden: {rel}'


def fence(root, expected=0):
    result = subprocess.run([KUJO, 'run', str(FENCE), '--', 'check', '--format', 'json'],
                            cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == expected, (result.returncode, result.stdout, result.stderr)
    report = json.loads(result.stdout[result.stdout.index('{'):])
    assert not report['skipped_files'], report
    assert (report['summary']['errors'] > 0) == (expected != 0), report
    return report


discipline(ROOT)
report = fence(ROOT)
cases = [
    ('client/client.kujo', 'src.providers.fixture.provider'),
    ('client/client.kujo', 'src.storage.sqlite'),
    ('domain/binding.kujo', 'src.providers.fixture.provider'),
    ('gateway/operations.kujo', 'src.application.execution'),
    ('application/execution.kujo', 'src.storage.sqlite'),
    ('application/execution.kujo', 'src.providers.fixture.provider'),
    ('providers/contract.kujo', 'src.providers.fixture.provider'),
    ('providers/fixture/provider.kujo', 'src.gateway.operations'),
    ('storage/sqlite.kujo', 'src.providers.fixture.provider'),
]
with tempfile.TemporaryDirectory(prefix='payments-fence-') as directory:
    temp = Path(directory)
    shutil.copytree(ROOT / 'src', temp / 'src')
    shutil.copyfile(ROOT / 'fence.toml', temp / 'fence.toml')
    for source, target in cases:
        path = temp / 'src' / source
        original = path.read_text()
        path.write_text(original + f'\nfrom {target} import forbidden_probe\n')
        fence(temp, 1)
        path.write_text(original)
    for source, addition in [('client/client.kujo', 'from ability import forbidden_probe'),
                             ('client/client.kujo', 'from stripe import forbidden_probe'),
                             ('unclassified.kujo', '// Must be assigned a zone before merge')]:
        path = temp / 'src' / source
        original = path.read_text() if path.exists() else None
        path.write_text((original or '') + '\n' + addition + '\n')
        try:
            discipline(temp)
        except AssertionError:
            pass
        else:
            raise AssertionError('Static import discipline failed to reject mutation')
        if original is None:
            path.unlink()
        else:
            path.write_text(original)
print(f"Architecture: {report['summary']['files_scanned']} files; Fence passed; 9 forbidden edges and 3 coverage/external mutations rejected")
