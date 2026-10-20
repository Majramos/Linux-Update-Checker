import subprocess


def run_subprocess(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Run *cmd* and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"
    except PermissionError:
        return 126, "", f"Permission denied: {cmd[0]}"
    except OSError as exc:
        return 1, "", f"Failed to execute {cmd[0]}: {exc}"
