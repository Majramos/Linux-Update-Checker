import argparse
import json
import os
import sys

from linux_update_checker.constants import DISCORD_WEBHOOK_ENV
from linux_update_checker.logger import setup_logger
from linux_update_checker.managers import MANAGERS, detect_and_check
from linux_update_checker.messenger.discord import build_discord_payload, send_discord

log = setup_logger("linux_update_checker")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check for Linux system updates and notify Discord.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--webhook",
        "-w",
        default=os.environ.get(DISCORD_WEBHOOK_ENV),
        metavar="URL",
        help=f"Discord webhook URL. Can also be set via {DISCORD_WEBHOOK_ENV}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Discord payload to stdout instead of sending it.",
    )
    parser.add_argument(
        "--notify-on-no-updates",
        action="store_true",
        default=False,
        help="Send a notification even when the system is up to date.",
    )
    parser.add_argument(
        "--manager",
        choices=[*MANAGERS, "auto"],
        default="auto",
        help="Force a specific package manager (default: auto-detect).",
    )
    return parser.parse_args()


def main() -> None:
    log.debug("parsing cli arguments")
    args = parse_args()

    if not args.dry_run and not args.webhook:
        print(
            f"[ERROR] No webhook URL provided.\n"
            f"        Use --webhook <URL> or set {DISCORD_WEBHOOK_ENV}.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.manager == "auto":
        results = detect_and_check()
    else:
        results = [MANAGERS[args.manager]().check()]

    for r in results:
        if r.error:
            print(f"[{r.manager}] ERROR: {r.error}")
        elif r.available:
            sec = f", {r.security_count} security" if r.security_count else ""
            print(f"[{r.manager}] {r.count} update(s) available{sec}")
        else:
            print(f"[{r.manager}] Up to date.")

    has_updates = any(r.available or r.error for r in results)
    if not has_updates and not args.notify_on_no_updates:
        print(
            "[INFO] No updates found — skipping Discord notification. "
            "Use --notify-on-no-updates to always send."
        )
        return

    payload = build_discord_payload(results)

    if args.dry_run:
        print("\n── Discord payload (dry run) ──")
        print(json.dumps(payload, indent=2))
        return

    send_discord(args.webhook, payload)
    log.info("Discord notification sent.")


if __name__ == "__main__":
    main()
