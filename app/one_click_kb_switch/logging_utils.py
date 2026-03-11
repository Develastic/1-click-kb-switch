from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pylogrouter import (
    LEVEL_DEBUG,
    LEVEL_INFO,
    NATURE_ERROR,
    NATURE_INFO,
    NATURE_WARNING,
    THEME_LIGHT,
    configure_logger,
    get_logger as get_router,
)


@dataclass(slots=True)
class AppLogger:
    debug_enabled: bool

    def debug(self, message: str, *args: object) -> None:
        if self.debug_enabled:
            get_router().log(message % args if args else message, level=LEVEL_DEBUG, nature=NATURE_INFO)

    def info(self, message: str, *args: object) -> None:
        get_router().log(message % args if args else message, level=LEVEL_INFO, nature=NATURE_INFO)

    def warning(self, message: str, *args: object) -> None:
        get_router().log(message % args if args else message, level=LEVEL_INFO, nature=NATURE_WARNING)

    def error(self, message: str, *args: object) -> None:
        get_router().log(message % args if args else message, level=LEVEL_INFO, nature=NATURE_ERROR)


_logger: AppLogger | None = None


def configure_logging(debug: bool, html_log_path: Path) -> AppLogger:
    global _logger
    if html_log_path.exists():
        html_log_path.unlink()
    router = configure_logger(level=LEVEL_DEBUG if debug else LEVEL_INFO, color=False, suppress_logger_greeting=True)
    router.add_html_log_file(
        log_handle="html",
        log_file_path=str(html_log_path),
        title="1-Click-KB-Switch session log",
        html_theme=THEME_LIGHT,
        html_auto_refresh_enabled=False,
        rotate_on_start=False,
        rotations_to_keep=0,
    )
    _logger = AppLogger(debug_enabled=debug)
    _logger.info("HTML log initialized: %s", str(html_log_path))
    return _logger


def get_logger() -> AppLogger:
    if _logger is None:
        raise RuntimeError("Logger is not configured")
    return _logger
