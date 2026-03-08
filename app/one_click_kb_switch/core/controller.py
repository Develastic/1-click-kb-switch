from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Callable

from one_click_kb_switch.core.config import AppConfig
from one_click_kb_switch.core.hotkeys import InputEvent, SingleClickDetector, default_bindings
from one_click_kb_switch.core.layouts import build_layout, choose_default_pair
from one_click_kb_switch.core.models import HotkeyBinding, LayoutInfo, PlatformWarning, RuntimeState
from one_click_kb_switch.platform.base import PlatformBackend
from one_click_kb_switch.platform.factory import create_platform_backend


@dataclass(slots=True)
class RuntimeController:
    backend: PlatformBackend
    config: AppConfig
    layouts: list[LayoutInfo]
    state: RuntimeState
    _detectors: dict[str, tuple[SingleClickDetector, str]]

    @classmethod
    def bootstrap(cls) -> "RuntimeController":
        config_path = AppConfig.user_config_path()
        first_run = not config_path.exists()
        config = AppConfig.create_from_defaults() if first_run else AppConfig.load()
        backend = create_platform_backend()
        raw_layouts = backend.list_layouts()
        layouts = [build_layout(item.layout_id, item.display_name, config.label_overrides.get(item.layout_id, "")) for item in raw_layouts]
        english, non_english = choose_default_pair(layouts)
        if not config.hotkeys:
            config.hotkeys = default_bindings(english, non_english)
            config.save()
        state = RuntimeState(first_run=first_run)
        state.warnings.extend(backend.get_platform_warnings())
        controller = cls(backend=backend, config=config, layouts=layouts, state=state, _detectors={})
        controller.refresh_active_layout()
        controller._rebuild_detectors()
        return controller

    def _rebuild_detectors(self) -> None:
        self._detectors = {
            binding.trigger_key: (SingleClickDetector(binding.trigger_key), binding.layout_id)
            for binding in self.config.hotkeys
            if binding.binding_type == "single_click"
        }

    def refresh_active_layout(self) -> None:
        active_layout = self.backend.get_active_layout()
        self.state.active_layout_id = active_layout
        self.state.tray_label = self.effective_label(active_layout)

    def effective_label(self, layout_id: str | None) -> str:
        if not layout_id:
            return "KB"
        layout = next((item for item in self.layouts if item.layout_id == layout_id), None)
        return layout.effective_label if layout else "KB"

    def update_label_override(self, layout_id: str, value: str) -> None:
        self.config.label_overrides[layout_id] = value.strip().upper()
        for layout in self.layouts:
            if layout.layout_id == layout_id:
                layout.label_override = value.strip().upper()
        self.config.save()
        self.refresh_active_layout()

    def set_play_switch_sound(self, enabled: bool) -> None:
        self.config.play_switch_sound = enabled
        self.config.save()

    def set_start_minimized(self, enabled: bool) -> None:
        self.config.start_minimized_after_first_run = enabled
        self.config.save()

    def mark_first_run_complete(self) -> None:
        if not self.config.has_completed_first_run:
            self.config.has_completed_first_run = True
            self.config.save()

    def apply_custom_binding(self, layout_id: str, key: str, modifiers: list[str]) -> None:
        from one_click_kb_switch.core.hotkeys import HotkeyBinding, upsert_custom_binding

        binding = HotkeyBinding(layout_id=layout_id, binding_type="combo", trigger_key=key, modifiers=modifiers)
        self.config.hotkeys = upsert_custom_binding(self.config.hotkeys, binding)
        self.config.save()

    def clear_custom_binding(self, layout_id: str) -> None:
        from one_click_kb_switch.core.hotkeys import clear_custom_binding

        self.config.hotkeys = clear_custom_binding(self.config.hotkeys, layout_id)
        self.config.save()

    def switch_layout(self, layout_id: str) -> bool:
        try:
            self.backend.switch_layout(layout_id)
            self.state.last_switch_error = None
            self.refresh_active_layout()
            return True
        except Exception as exc:  # noqa: BLE001
            self.state.last_switch_error = str(exc)
            return False

    def start_hooks(self, callback: Callable[[str], None]) -> None:
        def on_event(event: InputEvent) -> None:
            for detector, layout_id in self._detectors.values():
                if detector.feed(event):
                    callback(layout_id)

        self.backend.start_input_hooks(on_event)

    def stop_hooks(self) -> None:
        self.backend.stop_input_hooks()
