import json
import logging
import platform
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from linux_update_checker.constants import (
    COLOR_ERROR,
    COLOR_OK,
    COLOR_SECURITY,
    COLOR_UPDATES,
)
from linux_update_checker.models import UpdateResult

log = logging.getLogger("linux_update_checker")


# Discord API limits — see:
# https://discord.com/developers/docs/resources/channel#embed-limits
DISCORD_FIELD_VALUE_MAX = 1024
DISCORD_FIELD_NAME_MAX = 256
DISCORD_EMBED_TOTAL_MAX = 6000
DISCORD_FOOTER_MAX = 2048
DISCORD_EMBED_FIELDS_MAX = 25
DISCORD_PREVIEW_MAX_CHARS = 1000
DISCORD_ERROR_TRUNCATE = 500
DISCORD_HTTP_TIMEOUT = 30
DISCORD_USER_AGENT = "linux-update-checker/1.0"


class DiscordSendError(RuntimeError):
    """Raised when sending a Discord notification fails."""


def _truncate(text: str, limit: int) -> str:
    """Truncate *text* to *limit* characters, appending an ellipsis if cut."""
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _package_list_preview(
    packages: list[str],
    max_chars: int = DISCORD_PREVIEW_MAX_CHARS,
) -> str:

    if not packages:
        return "_None_"

    lines: list[str] = []
    current_len = 0
    shown = 0

    for pkg in packages:
        line = f"• `{pkg}`"
        line_len = len(line) + 1  # +1 for the newline separator
        if current_len + line_len > max_chars:
            break
        lines.append(line)
        current_len += line_len
        shown += 1

    if len(packages) > shown:
        more_text = f"_…and {len(packages) - shown} more_"
        more_len = len(more_text) + 1  # +1 for newline
        # If the "more" suffix doesn't fit, drop the last package line
        if current_len + more_len > max_chars and lines:
            removed = lines.pop()
            current_len -= len(removed) + 1
            shown -= 1
            more_text = f"_…and {len(packages) - shown} more_"
        lines.append(more_text)

    return "\n".join(lines)


def build_discord_payload(
    results: list[UpdateResult],
    *,
    hostname: str | None = None,
    now: datetime | None = None,
) -> dict:
    hostname = hostname or platform.node() or "unknown-host"
    now_str = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    total_updates = sum(r.count for r in results if not r.error)
    total_security = sum(r.security_count for r in results if not r.error)
    has_error = any(r.error for r in results)

    if has_error and total_updates == 0:
        color, title = COLOR_ERROR, "⚠️ Update check encountered errors"
    elif total_security > 0:
        color = COLOR_SECURITY
        title = f"🔴 {total_updates} update(s) available — {total_security} security!"
    elif total_updates > 0:
        color, title = (
            COLOR_UPDATES,
            f"🟠 {total_updates} update(s) available",
        )
    else:
        color, title = COLOR_OK, "✅ System is up to date"

    fields: list[dict] = []
    for r in results:
        if r.error:
            value = f"```{r.error[:DISCORD_ERROR_TRUNCATE]}```"
            inline = False
        elif r.available:
            value = _package_list_preview(r.packages)
            inline = False
        else:
            value = "No updates available."
            inline = True

        fields.append(
            {
                "name": _truncate(
                    f"📦 {r.manager} — {r.count} package(s)",
                    DISCORD_FIELD_NAME_MAX,
                ),
                "value": _truncate(value, DISCORD_FIELD_VALUE_MAX),
                "inline": inline,
            }
        )

    fields = fields[:DISCORD_EMBED_FIELDS_MAX]

    return {
        "embeds": [
            {
                "title": _truncate(title, DISCORD_FIELD_NAME_MAX),
                "color": color,
                "fields": fields,
                "footer": {
                    "text": _truncate(
                        f"🖥  {hostname}  •  {now_str}",
                        DISCORD_FOOTER_MAX,
                    )
                },
            }
        ]
    }


def send_discord(webhook_url: str, payload: dict) -> None:
    log.debug("sending discord message")
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        webhook_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": DISCORD_USER_AGENT,
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=DISCORD_HTTP_TIMEOUT) as resp:
            if resp.status not in (200, 204):
                raise DiscordSendError(f"Discord returned HTTP {resp.status}")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            try:
                retry_after = json.loads(body).get("retry_after", "unknown")
            except json.JSONDecodeError:
                retry_after = "unknown"
            msg = f"Discord rate-limited, retry after {retry_after}s"
            log.error(msg)
            raise DiscordSendError(msg) from exc
        msg = f"Discord HTTP {exc.code}: {body}"
        log.error(msg)
        raise DiscordSendError(msg) from exc
    except URLError as exc:
        url_msg = f"Network error: {exc}"
        log.error(url_msg)
        raise DiscordSendError(url_msg) from exc
    except Exception as exc:
        bare_msg = f"Failed to send Discord notification: {exc}"
        log.error(bare_msg)
        raise DiscordSendError(bare_msg) from exc
