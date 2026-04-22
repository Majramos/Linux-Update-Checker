from typing import Final, Literal

DISCORD_WEBHOOK_ENV: Final[Literal["LUC_DISCORD_WEBHOOK_URL"]] = (
    "LUC_DISCORD_WEBHOOK_URL"
)
DISCORD_EMBED_COLOR_OK = 0x437A22  # green    – no updates
DISCORD_EMBED_COLOR_UPDATES = 0xDA7101  # orange   – updates available
DISCORD_EMBED_COLOR_ERROR = 0xA12C7B  # purple   – check failed
DISCORD_EMBED_COLOR_SECURITY = 0xA13544  # dark red – security updates

SECURITY_KEYWORDS: tuple[Literal["security"], Literal["cve"], Literal["vuln"]] = (
    "security",
    "cve",
    "vuln",
)
