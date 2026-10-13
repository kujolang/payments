"""Offline bootstrap integrity checks, including optimized Python interpreters."""
import ast
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ['scripts/deployment/fetch_runtime.py', 'scripts/deployment/setup_workcell.py',
           'scripts/ci/bootstrap.py', 'examples/workcell/run.py']

class Integrity(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='payments-integrity-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.script = self.root / SCRIPTS[0]
        self.script.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / SCRIPTS[0], self.script)
        (self.root / 'deployment').mkdir()
        self.target = self.root / 'deployment/.runtime/kujo'
        self.binary = b'INERT_SYNTHETIC_BINARY'
        self.archive = self.root / 'fixture.tar.gz'
        self.pack()

    def pack(self, duplicate=False):
        with tarfile.open(self.archive, 'w:gz') as archive:
            for name in ['kujo', 'other/kujo'] if duplicate else ['kujo']:
                info = tarfile.TarInfo(name)
                info.size = len(self.binary)
                archive.addfile(info, io.BytesIO(self.binary))
        self.lock = {'url': self.archive.as_uri(),
                     'archive_sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                     'binary_sha256': hashlib.sha256(self.binary).hexdigest()}

    def invoke(self, flags=()):
        (self.root / 'deployment/runtime.lock.json').write_text(json.dumps(self.lock))
        return subprocess.run([sys.executable, *flags, str(self.script)],
                              capture_output=True, text=True, timeout=10)

    def test_valid_and_cached_in_all_modes(self):
        for flags in [(), ('-O',), ('-OO',)]:
            with self.subTest(flags=flags):
                result = self.invoke(flags)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.target.read_bytes(), self.binary)
                self.assertEqual(self.target.stat().st_mode & 0o777, 0o755)
        self.archive.unlink()
        self.assertEqual(self.invoke(('-O',)).returncode, 0, 'cache must avoid network')

    def test_bad_archive_and_binary_hashes_in_all_modes(self):
        for field in ['archive_sha256', 'binary_sha256']:
            for flags in [(), ('-O',), ('-OO',)]:
                with self.subTest(field=field, flags=flags):
                    original = self.lock[field]
                    self.lock[field] = '0' * 64
                    result = self.invoke(flags)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(self.target.exists())
                    self.lock[field] = original

    def test_duplicate_archive_binary_rejected(self):
        self.pack(duplicate=True)
        for flags in [(), ('-O',)]:
            self.assertNotEqual(self.invoke(flags).returncode, 0)
            self.assertFalse(self.target.exists())

    def test_target_symlink_never_overwritten(self):
        self.target.parent.mkdir()
        victim = self.root / 'victim'
        victim.write_bytes(b'UNCHANGED')
        self.target.symlink_to(victim)
        for flags in [(), ('-O',)]:
            self.assertNotEqual(self.invoke(flags).returncode, 0)
            self.assertEqual(victim.read_bytes(), b'UNCHANGED')

    def test_failed_download_preserves_existing_binary(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b'PREVIOUS')
        self.lock['archive_sha256'] = '0' * 64
        self.assertNotEqual(self.invoke(('-O',)).returncode, 0)
        self.assertEqual(self.target.read_bytes(), b'PREVIOUS')

    def test_failed_publication_preserves_cache_and_cleans_stage(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b'PREVIOUS')
        (self.root / 'deployment/runtime.lock.json').write_text(json.dumps(self.lock))
        for failing_call in ['os.fsync', 'os.replace']:
            code = """import runpy,sys
from unittest.mock import patch
with patch(sys.argv[2], side_effect=OSError('synthetic publication failure')):
    try: runpy.run_path(sys.argv[1])
    except OSError: pass
    else: raise RuntimeError('fault was not exercised')
"""
            result = subprocess.run([sys.executable, '-O', '-c', code, str(self.script), failing_call],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.target.read_bytes(), b'PREVIOUS')
            self.assertEqual([p.name for p in self.target.parent.iterdir()], ['kujo'])

    def test_cache_is_hashed_without_whole_file_buffering(self):
        self.target.parent.mkdir()
        self.target.write_bytes(self.binary)
        self.target.chmod(0o600)
        (self.root / 'deployment/runtime.lock.json').write_text(json.dumps(self.lock))
        code = """import runpy,sys
from pathlib import Path
from unittest.mock import patch
with patch.object(Path, 'read_bytes', side_effect=RuntimeError('whole-file read')):
    runpy.run_path(sys.argv[1])
"""
        result = subprocess.run([sys.executable, '-c', code, str(self.script)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o755)

    def test_suite_refuses_optimized_python(self):
        import os
        result = subprocess.run(['bash', str(ROOT / 'scripts/test.sh')], cwd=ROOT,
                                env={**os.environ, 'PYTHONOPTIMIZE': '1', 'KUJO_BIN': '/unused'},
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Run verification without PYTHONOPTIMIZE', result.stderr)

    def test_workcell_receipt_checks_survive_optimization(self):
        for flags in [(), ('-O',), ('-OO',)]:
            result = subprocess.run([sys.executable, *flags, str(ROOT / 'tests/network/workcell_process_test.py')],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_bootstrap_guards_cannot_be_compiled_out(self):
        for name in SCRIPTS:
            with self.subTest(name=name):
                tree = ast.parse((ROOT / name).read_text())
                self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)),
                                 'Installation/verification guards must survive python -O')

    def test_workcell_invalid_image_denied_before_any_command(self):
        code = '''import runpy,sys
from pathlib import Path
from unittest.mock import patch
module=runpy.run_path(sys.argv[1])
with patch('subprocess.run', side_effect=RuntimeError('COMMAND_REACHED')):
    try:
        module['execute'](Path('/unused'),Path('/unused'),'mutable:latest',Path('/unused'))
    except ValueError:
        pass
    else:
        raise RuntimeError('invalid image accepted')
'''
        for flags in [(), ('-O',), ('-OO',)]:
            result = subprocess.run([sys.executable, *flags, '-c', code, str(ROOT / SCRIPTS[3])],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == '__main__':
    unittest.main()
