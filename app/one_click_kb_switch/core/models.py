from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BindingType = Literal["single_click", "combo"]


@dataclass(slots=True)
class HotkeyBinding:
    layout_id: str
    binding_type: BindingType
    trigger_key: str
    modifiers: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LayoutInfo:
    layout_id: str
    display_name: str
    is_english: bool
    auto_label: str
    label_override: str = ""

    @property
    def effective_label(self) -> str:
        return self.label_override.strip().upper() or self.auto_label


@dataclass(slots=True)
class PlatformWarning:
    code: str
    message: str


@dataclass(slots=True)
class RuntimeState:
    active_layout_id: str | None = None
    tray_label: str = "KB"
    last_switch_error: str | None = None
    warnings: list[PlatformWarning] = field(default_factory=list)
    first_run: bool = False
