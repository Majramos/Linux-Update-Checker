import shutil
from abc import ABC, abstractmethod

from linux_update_checker.constants import SECURITY_KEYWORDS
from linux_update_checker.models import UpdateResult


class PackageManager(ABC):
    """Base class for package-manager integrations.

    Subclasses implement two focused methods:
      - ``_pre_check``  – optional setup step (e.g. ``apt-get update``).
      - ``_fetch_lines`` – run the query command and return raw output lines.
      - ``_parse_line``  – decide whether a raw line is a real package entry.
    The shared ``check()`` method handles the rest: result assembly, counting,
    and security classification.
    """

    #: Name shown in logs and Discord embeds.
    name: str
    #: Binary that must exist on PATH for this manager to be used.
    binary: str

    @classmethod
    def available(cls) -> bool:
        return shutil.which(cls.binary) is not None

    def check(self) -> UpdateResult:
        result = UpdateResult(manager=self.name)

        error = self._pre_check()
        if error:
            result.error = error
            return result

        lines, error = self._fetch_lines()
        if error:
            result.error = error
            return result

        packages = [pkg for line in lines if (pkg := self._parse_line(line))]

        result.packages = packages
        result.count = len(packages)
        result.available = result.count > 0
        result.security_count = sum(
            1 for p in packages if any(kw in p.lower() for kw in SECURITY_KEYWORDS)
        )
        return result

    def _pre_check(self) -> str | None:
        """Optional setup step. Return an error string on failure, else None."""
        return None

    @abstractmethod
    def _fetch_lines(self) -> tuple[list[str], str | None]:
        """Run the list/check command.

        Returns:
            (lines, error) – *lines* is a list of raw output lines;
            *error* is a non-empty string if the command failed.
        """

    @abstractmethod
    def _parse_line(self, line: str) -> str | None:
        """Return the package string if *line* represents a real package, else None."""
