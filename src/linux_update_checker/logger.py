import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_TRUTHY = {"1", "true", "yes", "on"}


def _is_debug_env() -> bool:
    """Return True if the ``DEBUG`` environment variable is set to a truthy value."""
    return os.environ.get("DEBUG", "").strip().lower() in _TRUTHY


def get_log_dir(app_name: str) -> Path:
    """
    Return a user-writable log directory that works on Linux and macOS
    without requiring sudo.

    Linux : ~/.local/share/<app_name>/logs   (XDG_DATA_HOME)
    macOS : ~/Library/Logs/<app_name>
    """
    if sys.platform == "darwin":
        log_dir = Path.home() / "Library" / "Logs" / app_name
    else:
        xdg_base = os.environ.get("XDG_DATA_HOME")
        if xdg_base:
            log_dir = Path(xdg_base).expanduser() / app_name / "logs"
        else:
            log_dir = Path.home() / ".local" / "share" / app_name / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


class ColourFormatter(logging.Formatter):
    """
    Adds ANSI colour codes to the level name when outputting to a TTY.
    Falls back to plain text in non-TTY environments (e.g. cron output redirect).
    """

    COLOURS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        if sys.stdout.isatty():
            colour = self.COLOURS.get(record.levelno, "")
            record.levelname = f"{colour}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    app_name: str = "myapp",
    log_level: int | None = None,
    file_level: int = logging.DEBUG,
    stream_level: int | None = None,
    when: str = "midnight",
    backup_count: int = 30,
    utc: bool = True,
) -> logging.Logger:
    """
    Configure and return a logger with:
      - TimedRotatingFileHandler  → writes all levels to a rotating log file
      - StreamHandler             → writes INFO+ to stdout (coloured on TTY)

    Args:
        app_name     : Name used for the logger and the log directory.
        log_level    : Master level for the logger itself.
        file_level   : Minimum level written to the log file.
        stream_level : Minimum level written to the console.
        when         : Rotation schedule ('midnight', 'H', 'D', 'W0'-'W6').
        backup_count : Number of rotated files to keep.
        utc          : If True, rotate at UTC midnight (avoids DST issues).

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(app_name)

    # Prevent duplicate handlers if setup_logger is called more than once
    if logger.handlers:
        return logger

    debug_mode = _is_debug_env()
    resolved_log_level = (
        log_level
        if log_level is not None
        else (logging.DEBUG if debug_mode else logging.INFO)
    )
    resolved_stream_level = (
        stream_level
        if stream_level is not None
        else (logging.DEBUG if debug_mode else logging.INFO)
    )

    logger.setLevel(resolved_log_level)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%SZ"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    log_dir = get_log_dir(app_name)
    log_file = log_dir / f"{app_name}.log"

    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when=when,
        interval=1,
        backupCount=backup_count,
        encoding="utf-8",
        utc=utc,
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(resolved_stream_level)
    stream_handler.setFormatter(ColourFormatter(fmt=fmt, datefmt=datefmt))

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.info("Logging initialised → %s", log_file)
    return logger
