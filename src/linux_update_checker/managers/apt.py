import os

from linux_update_checker.managers.base import PackageManager
from linux_update_checker.managers.shell import run_subprocess


class Apt(PackageManager):
    name = "apt"
    binary = "apt"

    def _pre_check(self) -> str | None:
        if os.geteuid() != 0:
            return None  # skip refresh when not root
        rc, _, err = run_subprocess(["apt-get", "update", "-qq"])
        if rc != 0:
            return f"apt-get update failed: {err.strip()}"
        return None

    def _fetch_lines(self) -> tuple[list[str], str | None]:
        rc, stdout, stderr = run_subprocess(
            ["apt", "list", "--upgradable", "--quiet=2"]
        )
        if rc != 0:
            return [], f"apt list failed: {stderr.strip() or stdout.strip()}"
        return stdout.splitlines(), None

    def _parse_line(self, line: str) -> str | None:
        line = line.strip()
        if not line or line.startswith("Listing..."):
            return None
        return line
