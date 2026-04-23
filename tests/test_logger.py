import logging
from logging.handlers import TimedRotatingFileHandler

import pytest

import linux_update_checker.logger as mod


@pytest.fixture
def clean_logger():
    created = []

    def _make(name="test-logger"):
        logger = logging.getLogger(name)
        logger.handlers[:] = []
        logger.setLevel(logging.NOTSET)
        logger.propagate = False
        created.append(logger)
        return logger

    yield _make

    for logger in created:
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


class TestIsDebugEnv:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("1", True),
            ("true", True),
            ("TRUE", True),
            (" yes ", True),
            ("on", True),
            ("0", False),
            ("false", False),
            ("off", False),
            ("", False),
        ],
    )
    def test_truthy_and_falsy_values(self, monkeypatch, value, expected):
        monkeypatch.setenv("DEBUG", value)
        assert mod._is_debug_env() is expected

    def test_missing_env_var_returns_false(self, monkeypatch):
        monkeypatch.delenv("DEBUG", raising=False)
        assert mod._is_debug_env() is False


def assert_log_dir(result, expected):
    assert result == expected
    assert result.exists()
    assert result.is_dir()


class TestGetLogDir:
    @pytest.mark.parametrize(
        ("xdg_data_home", "patch_home", "expected_parts"),
        [
            ("xdg-data", False, ("xdg-data", "myapp", "logs")),
            (None, True, (".local", "share", "myapp", "logs")),
            ("", True, (".local", "share", "myapp", "logs")),
        ],
        ids=[
            "linux-uses-xdg-data-home",
            "linux-defaults-to-local-share",
            "linux-empty-xdg-data-home-falls-back",
        ],
    )
    def test_linux_log_dir(
        self, monkeypatch, tmp_path, xdg_data_home, patch_home, expected_parts
    ):
        monkeypatch.setattr(mod.sys, "platform", "linux")

        if xdg_data_home is None:
            monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        elif xdg_data_home == "":
            monkeypatch.setenv("XDG_DATA_HOME", "")
        else:
            monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / xdg_data_home))

        if patch_home:
            monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)

        result = mod.get_log_dir("myapp")
        expected = tmp_path.joinpath(*expected_parts)

        assert_log_dir(result, expected)

    def test_macos_uses_library_logs(self, monkeypatch, tmp_path):
        monkeypatch.setattr(mod.sys, "platform", "darwin")
        monkeypatch.setattr(mod.Path, "home", lambda: tmp_path)

        result = mod.get_log_dir("myapp")
        expected = tmp_path / "Library" / "Logs" / "myapp"

        assert_log_dir(result, expected)


class TestColourFormatter:
    def test_format_adds_colour_when_stdout_is_tty(self, monkeypatch):
        monkeypatch.setattr(mod.sys.stdout, "isatty", lambda: True)

        formatter = mod.ColourFormatter("%(levelname)s | %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="boom",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert "\033[31mERROR\033[0m" in output
        assert "boom" in output

    def test_format_does_not_add_colour_when_not_tty(self, monkeypatch):
        monkeypatch.setattr(mod.sys.stdout, "isatty", lambda: False)

        formatter = mod.ColourFormatter("%(levelname)s | %(message)s")
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="careful",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        assert output == "WARNING | careful"

    def test_format_unknown_level_has_no_colour_prefix(self, monkeypatch):
        monkeypatch.setattr(mod.sys.stdout, "isatty", lambda: True)

        formatter = mod.ColourFormatter("%(levelname)s | %(message)s")
        record = logging.LogRecord(
            name="test",
            level=5,
            pathname=__file__,
            lineno=1,
            msg="custom",
            args=(),
            exc_info=None,
        )
        record.levelname = "TRACE"

        output = formatter.format(record)

        assert output == "TRACE\033[0m | custom"


class TestSetupLogger:
    @pytest.fixture
    def configured_logger(self, monkeypatch, tmp_path, clean_logger):
        created = {}

        def factory(app_name: str):
            logger = clean_logger(app_name)
            real_get_logger = logging.getLogger

            def fake_get_logger(name=None):
                if name == app_name:
                    return logger
                return real_get_logger(name)

            monkeypatch.setattr(mod.logging, "getLogger", fake_get_logger)
            monkeypatch.setattr(mod, "get_log_dir", lambda name: tmp_path)
            monkeypatch.setattr(mod.sys.stdout, "isatty", lambda: False)
            created["logger"] = logger
            created["tmp_path"] = tmp_path
            created["app_name"] = app_name
            return logger

        return factory

    def test_setup_logger_creates_file_and_stream_handlers(
        self, monkeypatch, configured_logger
    ):
        app_name = "app-basic"
        logger = configured_logger(app_name)
        monkeypatch.delenv("DEBUG", raising=False)

        result = mod.setup_logger(app_name=app_name)

        assert result is logger
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 2

        file_handler = next(
            h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)
        )
        stream_handler = next(
            h for h in logger.handlers if type(h) is logging.StreamHandler
        )

        assert file_handler.level == logging.DEBUG
        assert stream_handler.level == logging.INFO
        assert file_handler.backupCount == 30
        assert file_handler.utc is True
        assert file_handler.when == "MIDNIGHT"
        assert file_handler.baseFilename.endswith(f"{app_name}.log")

    def test_setup_logger_uses_debug_env_defaults(self, monkeypatch, configured_logger):
        app_name = "app-debug-env"
        logger = configured_logger(app_name)
        monkeypatch.setenv("DEBUG", "true")

        mod.setup_logger(app_name=app_name)

        stream_handler = next(
            h for h in logger.handlers if type(h) is logging.StreamHandler
        )

        assert logger.level == logging.DEBUG
        assert stream_handler.level == logging.DEBUG

    def test_explicit_levels_override_debug_env(self, monkeypatch, configured_logger):
        app_name = "app-explicit-levels"
        logger = configured_logger(app_name)
        monkeypatch.setenv("DEBUG", "true")

        mod.setup_logger(
            app_name=app_name,
            log_level=logging.WARNING,
            stream_level=logging.ERROR,
            file_level=logging.CRITICAL,
            when="H",
            backup_count=7,
            utc=False,
        )

        file_handler = next(
            h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)
        )
        stream_handler = next(
            h for h in logger.handlers if type(h) is logging.StreamHandler
        )

        assert logger.level == logging.WARNING
        assert stream_handler.level == logging.ERROR
        assert file_handler.level == logging.CRITICAL
        assert file_handler.backupCount == 7
        assert file_handler.utc is False
        assert file_handler.when == "H"

    def test_second_call_returns_same_logger_without_adding_handlers(
        self, monkeypatch, configured_logger
    ):
        app_name = "app-no-duplicates"
        logger = configured_logger(app_name)
        monkeypatch.delenv("DEBUG", raising=False)

        first = mod.setup_logger(app_name=app_name)
        handler_ids = [id(h) for h in logger.handlers]

        second = mod.setup_logger(app_name=app_name)

        assert first is second is logger
        assert len(logger.handlers) == 2
        assert [id(h) for h in logger.handlers] == handler_ids

    def test_initialisation_message_is_written_to_log_file(
        self, monkeypatch, configured_logger, tmp_path
    ):
        app_name = "app-log-message"
        configured_logger(app_name)
        monkeypatch.delenv("DEBUG", raising=False)

        mod.setup_logger(app_name=app_name)

        log_file = tmp_path / f"{app_name}.log"
        assert log_file.exists()

        content = log_file.read_text(encoding="utf-8")
        assert "Logging initialised" in content
        assert str(log_file) in content
