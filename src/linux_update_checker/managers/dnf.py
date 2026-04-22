from linux_update_checker.managers.base import PackageManager
from linux_update_checker.managers.shell import run_subprocess


class Dnf(PackageManager):
    name = "dnf"
    binary = "dnf"

    # dnf check-update exits 100 when updates are available, 0 when there are none.
    _OK_CODES = frozenset({0, 100})

    _SKIP_PREFIXES = ("Last metadata", "Obsoleting", "Security:")

    def _fetch_lines(self) -> tuple[list[str], str | None]:
        rc, stdout, stderr = run_subprocess(["dnf", "check-update", "--quiet"])
        if rc not in self._OK_CODES:
            return (
                [],
                f"dnf check-update failed (rc={rc}): {stderr.strip() or stdout.strip()}",
            )
        return stdout.splitlines(), None

    def _parse_line(self, line: str) -> str | None:
        line = line.strip()
        if not line or line.startswith(self._SKIP_PREFIXES):
            return None
        return line
