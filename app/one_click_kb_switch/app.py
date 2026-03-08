from __future__ import annotations

from one_click_kb_switch.core.controller import RuntimeController
from one_click_kb_switch.ui.main_window import run_app


def main() -> int:
    controller = RuntimeController.bootstrap()
    return run_app(controller)
