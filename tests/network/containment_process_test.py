"""Actual timeout, invalid encoding and launch errors must not echo private argv/output."""
import pathlib, sys, traceback, uuid
from containment_process import captured_process
ROOT = pathlib.Path(__file__).resolve().parents[2]
sentinel = "PRIVATE_CONTROLLER_" + uuid.uuid4().hex
cases = [([sys.executable, "-c", "import sys,time;print(sys.argv[1],flush=True);time.sleep(2)", sentinel], 0.1),
         (["/nonexistent/" + sentinel], 1),
         ([sys.executable, "-c", "import os,sys;os.write(1,sys.argv[1].encode()+bytes([255]))", sentinel], 1)]
for arguments, timeout in cases:
    try:
        captured_process(arguments, cwd=ROOT, timeout=timeout)
    except RuntimeError:
        rendered = traceback.format_exc()
        assert sentinel not in rendered and "output withheld" in rendered
    else:
        raise AssertionError("failure fixture did not fail")
print("Containment controller: actual timeout, launch and decoding failures withheld private arguments/output")
