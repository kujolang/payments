"""Exercise operator cancellation escalation without Docker or real payments."""
import importlib.util,json,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('workcell_example',ROOT/'examples/workcell/run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Cancellation(unittest.TestCase):
    def invoke(self,process,cancel):
        with patch.object(module.subprocess,'Popen',return_value=process):
            return module.run_workload(['fixture'],cancel.parent,{},cancel)
    def test_success(self):
        with tempfile.TemporaryDirectory() as directory:
            cancel=Path(directory)/'cancel'
            process=Mock(returncode=0);process.communicate.return_value=('{}','')
            self.assertEqual(self.invoke(process,cancel),'{}')
            self.assertFalse(cancel.exists());process.terminate.assert_not_called()
    def test_cancel_before_termination(self):
        with tempfile.TemporaryDirectory() as directory:
            cancel=Path(directory)/'cancel';process=Mock(returncode=1)
            def communicate(timeout):
                if timeout==60: raise subprocess.TimeoutExpired('fixture',60)
                self.assertTrue(cancel.exists());return ('','')
            process.communicate.side_effect=communicate
            with self.assertRaisesRegex(RuntimeError,'deadline exceeded'): self.invoke(process,cancel)
            process.terminate.assert_not_called();process.kill.assert_not_called()
    def test_stuck_cleanup_never_reports_success(self):
        with tempfile.TemporaryDirectory() as directory:
            cancel=Path(directory)/'cancel';process=Mock()
            process.communicate.side_effect=[subprocess.TimeoutExpired('fixture',n) for n in [60,30,5]]+[('','')]
            process.terminate.side_effect=lambda:self.assertTrue(cancel.exists())
            with self.assertRaisesRegex(RuntimeError,'cleanup is unconfirmed'): self.invoke(process,cancel)
            process.terminate.assert_called_once();process.kill.assert_called_once()
    def test_failure_output_is_not_exposed(self):
        with tempfile.TemporaryDirectory() as directory:
            process=Mock(returncode=1);process.communicate.return_value=('SECRET','SECRET')
            with self.assertRaises(RuntimeError) as error: self.invoke(process,Path(directory)/'cancel')
            self.assertNotIn('SECRET',str(error.exception))

class Verification(unittest.TestCase):
    def exercise(self, scenario):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);output=root/'evidence';output.mkdir(mode=0o700)
            runtime=root/'runtime';runtime.write_bytes(b'INERT_RUNTIME')
            run_dir=(root/'escaped') if scenario=='escape' else output/'runs'/'one'
            artifact=run_dir/'artifacts'/'intent.json';artifact.parent.mkdir(parents=True)
            artifact.write_text('{}')
            if scenario=='symlink':
                artifact.unlink();artifact.symlink_to(runtime)
            if scenario=='oversized': artifact.write_text('x'*8193)
            summary={'schema_version':'workcell-run-summary/v1','ok':scenario!='failed_run',
                     'output_dir':str(run_dir),'run_id':'one','receipt_path':'fixture'}
            def command(args, **kwargs):
                value=''
                if args[0]=='git' and 'rev-parse' in args:
                    value='wrong' if scenario=='commit' else module.PIN['workcell_commit']
                elif args[0]=='git' and 'status' in args:
                    value=' M changed' if scenario=='dirty' else ''
                elif args==[str(runtime),'--version']:
                    value='wrong' if scenario=='version' else module.PIN['runtime_version']
                elif len(args)>1 and args[1]=='verify': value=json.dumps({'ok':scenario!='unverified'})
                return subprocess.CompletedProcess(args,0,value,'')
            with patch.object(module.subprocess,'run',side_effect=command), patch.object(module,'run_workload',return_value=json.dumps(summary)):
                return module.execute(root/'workcell',runtime,'sha256:'+'a'*64,output)

    def test_verified_result_requires_every_boundary(self):
        for scenario in ['commit','dirty','version','failed_run','escape','unverified','symlink','oversized']:
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                self.exercise(scenario)

    def test_valid_evidence_is_returned(self):
        result=self.exercise('valid')
        self.assertTrue(result['verified'])
        self.assertEqual(result['intent'],{})

if __name__=='__main__': unittest.main()
