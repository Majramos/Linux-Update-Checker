from datetime import datetime
from urllib.error import HTTPError, URLError

import pytest

from linux_update_checker.messenger.discord import (
    COLOR_ERROR,
    COLOR_OK,
    COLOR_SECURITY,
    COLOR_UPDATES,
    DiscordSendError,
    _package_list_preview,
    _truncate,
    build_discord_payload,
    send_discord,
)
from linux_update_checker.models import UpdateResult


class FakeHTTPError(HTTPError):
    def __init__(
        self,
        *,
        code,
        body,
        url="https://discord.example/webhook",
        msg=None,
    ):
        super().__init__(
            url=url,
            code=code,
            msg=msg or f"HTTP {code}",
            hdrs=None,
            fp=None,
        )
        self._body = body

    def read(self):
        return self._body


def freeze_datetime(monkeypatch, year, month, day, hour, minute, second):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls):
            return cls(year, month, day, hour, minute, second)

    monkeypatch.setattr(
        "linux_update_checker.messenger.discord.datetime", FrozenDatetime
    )


def test_package_list_preview_returns_none_for_empty_list():
    assert _package_list_preview([]) == "_None_"


def test_package_list_preview_truncates_and_reports_remaining_count():
    packages = [f"pkg{i}" for i in range(17)]

    preview = _package_list_preview(packages, max_chars=40)

    assert "• `pkg0`" in preview
    assert "• `pkg1`" in preview
    assert "• `pkg2`" in preview
    assert "pkg3" not in preview
    assert preview.endswith("_…and 14 more_")


def test_package_list_preview_drops_last_line_to_fit_more_suffix():
    packages = [f"pkg{i}" for i in range(17)]

    preview = _package_list_preview(packages, max_chars=28)

    assert preview == "• `pkg0`\n• `pkg1`\n_…and 15 more_"
    assert "pkg2" not in preview


def test_truncate_returns_original_when_within_limit():
    assert _truncate("abc", 3) == "abc"


def test_truncate_adds_ellipsis_when_over_limit():
    assert _truncate("abcdef", 5) == "abcd…"


def test_build_discord_payload_uses_error_status_when_all_results_fail(monkeypatch):
    monkeypatch.setattr(
        "linux_update_checker.messenger.discord.platform.node", lambda: "host1"
    )
    freeze_datetime(monkeypatch, 2026, 4, 21, 10, 11, 12)

    results = [UpdateResult(manager="apt", error="boom")]

    payload = build_discord_payload(results)
    embed = payload["embeds"][0]

    assert embed["title"] == "⚠️ Update check encountered errors"
    assert embed["color"] == COLOR_ERROR
    assert embed["footer"]["text"] == "🖥  host1  •  2026-04-21 10:11:12"
    assert embed["fields"] == [
        {"name": "📦 apt — 0 package(s)", "value": "```boom```", "inline": False}
    ]


def test_build_discord_payload_uses_security_status_and_mixed_fields(monkeypatch):
    monkeypatch.setattr(
        "linux_update_checker.messenger.discord.platform.node", lambda: ""
    )
    freeze_datetime(monkeypatch, 2026, 1, 2, 3, 4, 5)

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
    assert embed["color"] == COLOR_SECURITY
    assert embed["footer"]["text"] == "🖥  unknown-host  •  2026-01-02 03:04:05"
    assert embed["fields"] == [
        {
            "name": "📦 apt — 2 package(s)",
            "value": "• `openssl`\n• `curl`",
            "inline": False,
        },
        {
            "name": "📦 flatpak — 0 package(s)",
            "value": "No updates available.",
            "inline": True,
        },
        {
            "name": "📦 dnf — 0 package(s)",
            "value": "```repo down```",
            "inline": False,
        },
    ]


def test_build_discord_payload_uses_updates_status_without_security():
    results = [
        UpdateResult(manager="apt", count=3, available=True, packages=["a", "b", "c"])
    ]

    payload = build_discord_payload(results)
    embed = payload["embeds"][0]

    assert embed["title"] == "🟠 3 update(s) available"
    assert embed["color"] == COLOR_UPDATES


def test_build_discord_payload_uses_ok_status_when_no_updates():
    results = [UpdateResult(manager="apt", available=False)]

    payload = build_discord_payload(results)
    embed = payload["embeds"][0]

    assert embed["title"] == "✅ System is up to date"
    assert embed["color"] == COLOR_OK


def test_build_discord_payload_limits_fields_to_25():
    results = [UpdateResult(manager=f"mgr{i}", available=False) for i in range(30)]

    payload = build_discord_payload(results)
    fields = payload["embeds"][0]["fields"]

    assert len(fields) == 25
    assert fields[0] == {
        "name": "📦 mgr0 — 0 package(s)",
        "value": "No updates available.",
        "inline": True,
    }
    assert fields[-1] == {
        "name": "📦 mgr24 — 0 package(s)",
        "value": "No updates available.",
        "inline": True,
    }


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
    assert captured["headers"]["User-agent"] == "linux-update-checker/1.0"
    assert captured["data"] == b'{"embeds": [{"title": "hello"}]}'
    assert captured["timeout"] == 30


def test_send_discord_accepts_http_200(monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout):
        return Response()

    monkeypatch.setattr("linux_update_checker.messenger.discord.urlopen", fake_urlopen)

    send_discord("https://discord.example/webhook", {"ok": True})


@pytest.mark.parametrize(
    ("side_effect", "expected_message"),
    [
        (URLError("offline"), "Network error: "),
        (
            RuntimeError("bad status"),
            "Failed to send Discord notification: bad status",
        ),
    ],
)
def test_send_discord_logs_and_raises_on_network_and_generic_errors(
    monkeypatch, caplog, side_effect, expected_message
):
    def fake_urlopen(req, timeout):
        raise side_effect

    monkeypatch.setattr("linux_update_checker.messenger.discord.urlopen", fake_urlopen)

    with caplog.at_level("ERROR", logger="linux_update_checker"):
        with pytest.raises(DiscordSendError):
            send_discord("https://discord.example/webhook", {"ok": True})

    assert expected_message in caplog.text


def test_send_discord_logs_and_raises_on_http_error(monkeypatch, caplog):
    def fake_urlopen(req, timeout):
        raise FakeHTTPError(
            code=400,
            body=b'{"message": "invalid webhook"}',
            msg="Bad Request",
        )

    monkeypatch.setattr("linux_update_checker.messenger.discord.urlopen", fake_urlopen)

    with caplog.at_level("ERROR", logger="linux_update_checker"):
        with pytest.raises(DiscordSendError):
            send_discord("https://discord.example/webhook", {"ok": True})

    assert 'Discord HTTP 400: {"message": "invalid webhook"}' in caplog.text


def test_send_discord_logs_and_raises_on_http_429_with_retry_after(monkeypatch, caplog):
    def fake_urlopen(req, timeout):
        raise FakeHTTPError(
            code=429,
            body=b'{"retry_after": 3}',
            msg="Too Many Requests",
        )

    monkeypatch.setattr("linux_update_checker.messenger.discord.urlopen", fake_urlopen)

    with caplog.at_level("ERROR", logger="linux_update_checker"):
        with pytest.raises(DiscordSendError) as exc_info:
            send_discord("https://discord.example/webhook", {"ok": True})

    assert str(exc_info.value) == "Discord rate-limited, retry after 3s"
    assert "Discord rate-limited, retry after 3s" in caplog.text


def test_send_discord_logs_and_raises_on_http_429_with_invalid_json(
    monkeypatch, caplog
):
    def fake_urlopen(req, timeout):
        raise FakeHTTPError(
            code=429,
            body=b"not-json",
            msg="Too Many Requests",
        )

    monkeypatch.setattr("linux_update_checker.messenger.discord.urlopen", fake_urlopen)

    with caplog.at_level("ERROR", logger="linux_update_checker"):
        with pytest.raises(DiscordSendError) as exc_info:
            send_discord("https://discord.example/webhook", {"ok": True})

    assert str(exc_info.value) == "Discord rate-limited, retry after unknowns"
    assert "Discord rate-limited, retry after unknowns" in caplog.text
