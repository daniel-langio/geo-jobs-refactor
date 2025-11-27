import subprocess
import sys


def run_cmd(cmd, cwd=None):
    """
    Execute a shell command and stream output.
    Raises an exception if the command fails.
    """
    try:
        process = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            text=True
        )
        return process
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(e.returncode)
