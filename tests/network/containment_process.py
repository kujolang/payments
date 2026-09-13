"""Private test-controller subprocess boundary; never format raw command failures."""
import subprocess


def captured_process(arguments, *, cwd, timeout):
    try:
        return subprocess.run(arguments, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.SubprocessError, OSError, UnicodeError):
        # TimeoutExpired includes argv and captured output. Both can contain canaries.
        raise RuntimeError("Containment subprocess failed; arguments and output withheld") from None
