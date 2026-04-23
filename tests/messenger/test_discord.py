from datetime import datetime
from urllib.error import HTTPError, URLError

import pytest

from linux_update_checker.messenger.discord import (
    DISCORD_EMBED_COLOR_ERROR,
    DISCORD_EMBED_COLOR_OK,
    DISCORD_EMBED_COLOR_SECURITY,
    DISCORD_EMBED_COLOR_UPDATES,
    _package_list_preview,
    build_discord_payload,
    send_discord,
)
from linux_update_checker.models import UpdateResult


def test_package_list_preview_returns_none_for_empty_list():
    assert _package_list_preview([]) == "_None_"


def test_package_list_preview_truncates_and_reports_remaining_count():
    packages = [f"pkg{i}" for i in range(17)]

    preview = _package_list_preview(packages, max_lines=15)

    assert "• `pkg0`" in preview
    assert "• `pkg14`" in preview
    assert "pkg15" not in preview
    assert preview.endswith("_…and 2 more_")


def test_build_discord_payload_uses_error_status_when_all_results_fail(monkeypatch):
    monkeypatch.setattr(
        "linux_update_checker.messenger.discord.platform.node", lambda: "host1"
    )

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 4, 21, 10, 11, 12)

    monkeypatch.setattr(
        "linux_update_checker.messenger.discord.datetime", FrozenDatetime
    )

    results = [UpdateResult(manager="apt", error="boom")]

    payload = build_discord_payload(results)
    embed = payload["embeds"][0]

    assert embed["title"] == "⚠️ Update check encountered errors"
    assert embed["color"] == DISCORD_EMBED_COLOR_ERROR
    assert embed["footer"]["text"] == "🖥  host1  •  2026-04-21 10:11:12"
    assert embed["fields"] == [
        {"name": "❌ apt", "value": "```boom```", "inline": False}
    ]


def test_build_discord_payload_uses_security_status_and_mixed_fields(monkeypatch):
    monkeypatch.setattr(
        "linux_update_checker.messenger.discord.platform.node", lambda: ""
    )

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 1, 2, 3, 4, 5)

    monkeypatch.setattr(
        "linux_update_checker.messenger.discord.datetime", FrozenDatetime
    )

    results = [
        UpdateResult(
            manager="apt",
            count=2,
            security_count=1,
            available=True,
            packages=["openssl", "curl"],
        ),
        UpdateResult(manager="flatpak", available=False),
        UpdateResult(manager="dnf", error="repo down"),
    ]

    payload = build_discord_payload(results)
    embed = payload["embeds"][0]

    assert embed["title"] == "🔴 2 update(s) available — 1 security!"
    assert embed["color"] == DISCORD_EMBED_COLOR_SECURITY
    assert embed["footer"]["text"] == "🖥  unknown-host  •  2026-01-02 03:04:05"
    assert embed["fields"] == [
        {
            "name": "📦 apt — 2 package(s)",
            "value": "• `openssl`\n• `curl`",
            "inline": False,
        },
        {"name": "✅ flatpak", "value": "No updates available.", "inline": True},
        {"name": "❌ dnf", "value": "```repo down```", "inline": False},
    ]


def test_build_discord_payload_uses_updates_status_without_security():
    results = [
        UpdateResult(manager="apt", count=3, available=True, packages=["a", "b", "c"])
    ]

    payload = build_discord_payload(results)
    embed = payload["embeds"][0]

    assert embed["title"] == "🟠 3 update(s) available"
    assert embed["color"] == DISCORD_EMBED_COLOR_UPDATES


def test_build_discord_payload_uses_ok_status_when_no_updates():
    results = [UpdateResult(manager="apt", available=False)]

    payload = build_discord_payload(results)
    embed = payload["embeds"][0]

    assert embed["title"] == "✅ System is up to date"
    assert embed["color"] == DISCORD_EMBED_COLOR_OK


def test_build_discord_payload_truncates_error_text_to_500_chars():
    error_text = "x" * 600

    payload = build_discord_payload([UpdateResult(manager="apt", error=error_text)])
    field = payload["embeds"][0]["fields"][0]

    assert field["value"] == f"```{'x' * 500}```"


def test_send_discord_posts_json_payload(monkeypatch):
    captured = {}

    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout):
        captured["full_url"] = req.full_url
        captured["method"] = req.get_method()
        captured["headers"] = dict(req.header_items())
        captured["data"] = req.data
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr("linux_update_checker.messenger.discord.urlopen", fake_urlopen)

    payload = {"embeds": [{"title": "hello"}]}
    send_discord("https://discord.example/webhook", payload)

    assert captured["full_url"] == "https://discord.example/webhook"
    assert captured["method"] == "POST"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["headers"]["User-agent"] == "MyApp/1.0 (+https://example.com)"
    assert captured["data"] == b'{"embeds": [{"title": "hello"}]}'
    assert captured["timeout"] == 30


@pytest.mark.parametrize(
    ("side_effect", "expected_message"),
    [
        (URLError("offline"), "Network error: <urlopen error offline>"),
        (RuntimeError("bad status"), "Failed to send Discord notification: bad status"),
    ],
)
def test_send_discord_logs_and_exits_on_network_and_generic_errors(
    monkeypatch, caplog, side_effect, expected_message
):
    def fake_urlopen(req, timeout):
        raise side_effect

    monkeypatch.setattr("linux_update_checker.messenger.discord.urlopen", fake_urlopen)

    with caplog.at_level("ERROR", logger="linux_update_checker"):
        with pytest.raises(SystemExit) as exc_info:
            send_discord("https://discord.example/webhook", {"ok": True})

    assert exc_info.value.code == 1
    assert expected_message in caplog.text


def test_send_discord_logs_and_exits_on_http_error(monkeypatch, caplog):
    class FakeHTTPError(HTTPError):
        def __init__(self):
            super().__init__(
                url="https://discord.example/webhook",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=None,
            )

        def read(self):
            return b'{"message": "invalid webhook"}'

    def fake_urlopen(req, timeout):
        raise FakeHTTPError()

    monkeypatch.setattr("linux_update_checker.messenger.discord.urlopen", fake_urlopen)

    with caplog.at_level("ERROR", logger="linux_update_checker"):
        with pytest.raises(SystemExit) as exc_info:
            send_discord("https://discord.example/webhook", {"ok": True})

    assert exc_info.value.code == 1
    assert 'Discord HTTP 400: {"message": "invalid webhook"}' in caplog.text
