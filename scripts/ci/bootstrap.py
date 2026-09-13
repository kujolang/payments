"""Reproduce locked development dependencies through Kennel, never update pins."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
KUJO = os.environ.get('KUJO_BIN', str(ROOT / 'deployment/.runtime/kujo'))
PIN = '546dd4205b90825f3e326336941c3068b1add0f0'

def run(args, cwd=ROOT, capture=False):
    return subprocess.run(args, cwd=cwd, check=True, timeout=180,
                          text=True, capture_output=capture)

def read_toml(path):
    result = subprocess.run([KUJO, 'run', str(ROOT / 'scripts/read_toml.kujo')],
                            env={**os.environ, 'PAYMENTS_TEST_TOML': str(path)},
                            check=True, timeout=30, capture_output=True, text=True)
    return json.loads(result.stdout)

with tempfile.TemporaryDirectory(prefix='payments-ci-kennel-') as directory:
    source = Path(directory) / 'kennel'
    run(['git', 'clone', '--no-checkout', '--filter=blob:none',
         'https://github.com/kujolang/kennel.git', str(source)])
    run(['git', 'checkout', '--detach', PIN], cwd=source)
    assert run(['git', 'rev-parse', 'HEAD'], cwd=source, capture=True).stdout.strip() == PIN
    for project in [ROOT, ROOT / 'tools', ROOT / 'examples/agents-sdk']:
        files = [project / 'kennel.toml', project / 'kennel.lock']
        before = [p.read_bytes() for p in files]
        locked = read_toml(files[1])
        run([KUJO, 'run', str(source / 'kennel.kujo'), '--interpreter', '--',
             'install', '--project-dir', str(project)])
        assert [p.read_bytes() for p in files] == before, 'Kennel changed committed dependency contracts'
        for package in locked['package']:
            assert package['kind'] == 'github' and package['requested_kind'] == 'commit'
            installed = project / package['install_path']
            # Kennel intentionally strips .git. Compare the installed source
            # against an independent exact checkout, not the parent repo HEAD.
            expected = Path(directory) / (package['name']+'-'+package['resolved_commit'])
            run(['git', 'clone', '--no-checkout', '--filter=blob:none', package['repository'], str(expected)])
            run(['git', 'checkout', '--detach', package['resolved_commit']], cwd=expected)
            excluded = {'.git', 'node_modules', 'dist', 'build', 'kennel_packages', '.kennel_tmp'}
            def tree(base):
                result = {}
                for path in base.rglob('*'):
                    rel = path.relative_to(base)
                    if rel.parts[0] in excluded:
                        continue
                    assert not path.is_symlink(), 'Unexpected package symlink'
                    if path.is_file():
                        result[rel.as_posix()] = path.read_bytes()
                return result
            assert tree(installed) == tree(expected), 'Installed dependency differs from exact source'
print('Pinned Kennel installed exact Ability, Fence and Agents SDK locks without contract changes')
