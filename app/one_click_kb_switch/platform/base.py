from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from one_click_kb_switch.core.hotkeys import InputEvent
from one_click_kb_switch.core.models import LayoutInfo, PlatformWarning


class PlatformBackend(ABC):
    @abstractmethod
    def list_layouts(self) -> list[LayoutInfo]:
        raise NotImplementedError

    @abstractmethod
    def get_active_layout(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def switch_layout(self, layout_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def start_input_hooks(self, callback: Callable[[InputEvent], None]) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop_input_hooks(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_platform_warnings(self) -> list[PlatformWarning]:
        raise NotImplementedError

    @abstractmethod
    def debug_snapshot(self) -> dict[str, object]:
        raise NotImplementedError
