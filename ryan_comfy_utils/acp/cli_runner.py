import os
import subprocess
from pathlib import Path


def run_cli_command(
    command: list[str],
    cwd: Path,
    timeout_seconds: int,
    env_overrides: dict,
) -> dict:
    env = os.environ.copy()
    env.update(env_overrides)
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
        shell=(os.name == "nt"),
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
