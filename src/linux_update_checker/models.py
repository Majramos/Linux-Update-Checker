from dataclasses import dataclass, field


@dataclass
class UpdateResult:
    manager: str
    available: bool = False
    count: int = 0
    packages: list[str] = field(default_factory=list)
    security_count: int = 0
    error: str | None = None
