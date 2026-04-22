from linux_update_checker.managers.apt import Apt
from linux_update_checker.managers.base import PackageManager
from linux_update_checker.managers.dnf import Dnf
from linux_update_checker.models import UpdateResult

MANAGERS: dict[str, type[PackageManager]] = {
    "apt": Apt,
    "dnf": Dnf,
}


def detect_and_check() -> list[UpdateResult]:
    """Probe PATH for known managers and run all that are found."""
    results = [cls().check() for cls in MANAGERS.values() if cls.available()]
    if not results:
        results.append(
            UpdateResult(
                manager="unknown",
                error="No supported package manager found (apt / dnf).",
            )
        )
    return results
