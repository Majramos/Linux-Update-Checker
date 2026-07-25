from typing import Final, Literal

DISCORD_WEBHOOK_ENV: Final = "LUC_DISCORD_WEBHOOK_URL"

COLOR_OK: Final = 0x437A22  # green – no updates
COLOR_UPDATES: Final = 0xDA7101  # orange – updates available
COLOR_ERROR: Final = 0xA12C7B  # purple – check failed
COLOR_SECURITY: Final = 0xA13544  # dark red – security updates

SECURITY_KEYWORDS: tuple[Literal["security"], Literal["cve"], Literal["vuln"]] = (
    "security",
    "cve",
    "vuln",
)
