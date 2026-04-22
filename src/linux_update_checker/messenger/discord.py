import json
import logging
import platform
import sys
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from linux_update_checker.constants import (
    DISCORD_EMBED_COLOR_ERROR,
    DISCORD_EMBED_COLOR_OK,
    DISCORD_EMBED_COLOR_SECURITY,
    DISCORD_EMBED_COLOR_UPDATES,
)
from linux_update_checker.models import UpdateResult

log = logging.getLogger("linux_update_checker")


def _package_list_preview(packages: list[str], max_lines: int = 15) -> str:
    if not packages:
        return "_None_"
    text = "\n".join(f"• `{p}`" for p in packages[:max_lines])
    if len(packages) > max_lines:
        text += f"\n_…and {len(packages) - max_lines} more_"
    return text


def build_discord_payload(results: list[UpdateResult]) -> dict:
    hostname = platform.node() or "unknown-host"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_updates = sum(r.count for r in results if not r.error)
    total_security = sum(r.security_count for r in results if not r.error)
    has_error = any(r.error for r in results)

    if has_error and total_updates == 0:
        color, title = DISCORD_EMBED_COLOR_ERROR, "⚠️ Update check encountered errors"
    elif total_security > 0:
        color = DISCORD_EMBED_COLOR_SECURITY
        title = f"🔴 {total_updates} update(s) available — {total_security} security!"
    elif total_updates > 0:
        color, title = (
            DISCORD_EMBED_COLOR_UPDATES,
            f"🟠 {total_updates} update(s) available",
        )
    else:
        color, title = DISCORD_EMBED_COLOR_OK, "✅ System is up to date"

    fields = []
    for r in results:
        if r.error:
            fields.append(
                {
                    "name": f"❌ {r.manager}",
                    "value": f"```{r.error[:500]}```",
                    "inline": False,
                }
            )
        elif r.available:
            fields.append(
                {
                    "name": f"📦 {r.manager} — {r.count} package(s)",
                    "value": _package_list_preview(r.packages),
                    "inline": False,
                }
            )
        else:
            fields.append(
                {
                    "name": f"✅ {r.manager}",
                    "value": "No updates available.",
                    "inline": True,
                }
            )

    return {
        "embeds": [
            {
                "title": title,
                "color": color,
                "fields": fields,
                "footer": {"text": f"🖥  {hostname}  •  {now}"},
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
            "User-Agent": "MyApp/1.0 (+https://example.com)",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 204):
                raise RuntimeError(f"Discord returned HTTP {resp.status}")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        log.error(f"Discord HTTP {exc.code}: {body}")
        sys.exit(1)
    except URLError as exc:
        log.error(f"Network error: {exc}")
        sys.exit(1)
    except Exception as exc:
        log.error(f"Failed to send Discord notification: {exc}")
        sys.exit(1)
