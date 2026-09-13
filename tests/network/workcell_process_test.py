"""Exercise operator cancellation escalation without Docker or real payments."""
import importlib.util,subprocess,tempfile,unittest
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

if __name__=='__main__': unittest.main()
