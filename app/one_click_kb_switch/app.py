from __future__ import annotations

from one_click_kb_switch.core.controller import RuntimeController
from one_click_kb_switch.logging_utils import configure_logging
from one_click_kb_switch.ui.main_window import run_app


def main(debug: bool = False) -> int:
    configure_logging(debug)
    controller = RuntimeController.bootstrap(debug=debug)
    return run_app(controller)
