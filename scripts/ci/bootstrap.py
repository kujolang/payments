"""Reproduce locked development dependencies through Kennel, never update pins."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

def require(condition, message):
    if not condition:
        raise ValueError(message)

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

def checkout(repository, commit, target):
    require(re.fullmatch(r'https://github\.com/kujolang/[a-zA-Z0-9_.-]+\.git', repository),
            'Unexpected dependency repository')
    require(re.fullmatch(r'[0-9a-f]{40}', commit), 'Expected a full dependency commit ID')
    run(['git', 'init', '--quiet', '--template=', str(target)])
    run(['git', 'fetch', '--no-tags', '--depth=1', repository, commit], cwd=target)
    run(['git', 'checkout', '--detach', 'FETCH_HEAD'], cwd=target)
    head = run(['git', 'rev-parse', 'HEAD'], cwd=target, capture=True).stdout.strip()
    require(head == commit, 'Dependency source commit mismatch')

def fingerprint(base):
    require(base.is_dir() and not base.is_symlink(), 'Invalid package root')
    excluded = {'.git', 'node_modules', 'dist', 'build', 'kennel_packages', '.kennel_tmp'}
    result = {}
    for current, directories, files in os.walk(base):
        parent = Path(current)
        if parent == base:
            directories[:] = [name for name in directories if name not in excluded]
            files = [name for name in files if name not in excluded]
        for name in directories:
            require(not (parent / name).is_symlink(), 'Unexpected package directory symlink')
        for name in files:
            path = parent / name
            require(stat.S_ISREG(path.lstat().st_mode), 'Expected regular package file')
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
            result[path.relative_to(base).as_posix()] = digest.digest()
    return result

with tempfile.TemporaryDirectory(prefix='payments-ci-kennel-') as directory:
    source = Path(directory) / 'kennel'
    checkout('https://github.com/kujolang/kennel.git', PIN, source)
    expected_sources = {}
    for project in [ROOT, ROOT / 'tools', ROOT / 'examples/agents-sdk', ROOT / 'examples/dispatch', ROOT / 'examples/mcp']:
        files = [project / 'kennel.toml', project / 'kennel.lock']
        before = [p.read_bytes() for p in files]
        locked = read_toml(files[1])
        run([KUJO, 'run', str(source / 'kennel.kujo'), '--interpreter', '--',
             'install', '--project-dir', str(project)])
        require([p.read_bytes() for p in files] == before, 'Kennel changed committed dependency contracts')
        for package in locked['package']:
            require(package['kind'] == 'github' and package['requested_kind'] == 'commit', 'Dependency must be pinned to a GitHub commit')
            name = package['name']
            require(re.fullmatch(r'[a-zA-Z0-9_-]+', name), 'Invalid dependency name')
            require(package['install_path'] == f'kennel_packages/{name}', 'Invalid dependency location')
            packages_root = project / 'kennel_packages'
            require(not packages_root.is_symlink(), 'Unexpected package directory symlink')
            installed = packages_root / name
            # Kennel intentionally strips .git. Compare the installed source
            # against an independent exact checkout, not the parent repo HEAD.
            identity = (package['repository'], package['resolved_commit'])
            require(package['requested'] == identity[1], 'Dependency resolution changed its requested commit')
            if identity not in expected_sources:
                expected = Path(directory) / f'verification-{len(expected_sources)}'
                checkout(*identity, expected)
                expected_sources[identity] = fingerprint(expected)
            require(fingerprint(installed) == expected_sources[identity], 'Installed dependency differs from exact source')
print('Pinned Kennel installed exact Ability, Fence, Agents SDK, Dispatch and MCP locks without contract changes')
