from __future__ import annotations

from one_click_kb_switch.app_paths import AppPaths
from one_click_kb_switch.core.controller import RuntimeController
from one_click_kb_switch.logging_utils import configure_logging, get_logger
from one_click_kb_switch.single_instance import SingleInstanceGuard
from one_click_kb_switch.ui.main_window import run_app


def main(debug: bool = False) -> int:
    paths = AppPaths.detect()
    paths.ensure()
    guard = SingleInstanceGuard(paths.instance_lock_file)
    try:
        guard.acquire()
    except RuntimeError as exc:
        print(str(exc))
        return 1

    logger = configure_logging(debug=debug, html_log_path=paths.html_log_file)
    logger.info("Using OS directories: config=%s data=%s logs=%s runtime=%s", paths.config_dir, paths.data_dir, paths.log_dir, paths.runtime_dir)
    logger.info("Single-instance guard acquired: %s", paths.instance_lock_file)
    try:
        controller = RuntimeController.bootstrap(debug=debug)
        return run_app(controller)
    finally:
        guard.release()
        get_logger().info("Single-instance guard released")
