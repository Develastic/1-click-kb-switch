from __future__ import annotations

from dataclasses import asdict, dataclass
from pprint import pformat
from typing import Callable

from one_click_kb_switch.core.config import AppConfig
from one_click_kb_switch.core.hotkeys import InputEvent, SingleClickDetector, default_bindings, has_legacy_default_bindings
from one_click_kb_switch.core.layouts import build_layout, choose_default_pair
from one_click_kb_switch.core.models import LayoutInfo, RuntimeState
from one_click_kb_switch.logging_utils import get_logger
from one_click_kb_switch.platform.base import PlatformBackend
from one_click_kb_switch.platform.factory import create_platform_backend


@dataclass(slots=True)
class RuntimeController:
    backend: PlatformBackend
    config: AppConfig
    layouts: list[LayoutInfo]
    state: RuntimeState
    debug: bool
    _detectors: dict[str, tuple[SingleClickDetector, str]]

    @classmethod
    def bootstrap(cls, debug: bool = False) -> "RuntimeController":
        logger = get_logger()
        config_path = AppConfig.user_config_path()
        first_run = not config_path.exists()
        config = AppConfig.create_from_defaults() if first_run else AppConfig.load()
        backend = create_platform_backend()
        raw_layouts = backend.list_layouts()
        layouts = [build_layout(item.layout_id, item.display_name, config.label_overrides.get(item.layout_id, "")) for item in raw_layouts]
        english, non_english = choose_default_pair(layouts)
        if not config.hotkeys or has_legacy_default_bindings(config.hotkeys, english, non_english):
            config.hotkeys = default_bindings(english, non_english)
            config.save()
        state = RuntimeState(first_run=first_run)
        state.warnings.extend(backend.get_platform_warnings())
        controller = cls(backend=backend, config=config, layouts=layouts, state=state, debug=debug, _detectors={})
        controller.refresh_active_layout()
        controller._rebuild_detectors()
        if debug:
            logger.debug("1-Click-KB-Switch debug mode enabled")
            logger.debug("config path: %s", config_path)
            logger.debug("backend: %s", backend.__class__.__name__)
            logger.debug("first run: %s", first_run)
            logger.debug("loaded hotkeys: %s", pformat([asdict(binding) for binding in config.hotkeys]))
            logger.debug("detected layouts: %s", pformat([asdict(layout) for layout in layouts]))
            logger.debug("active layout: %s", controller.state.active_layout_id)
            logger.debug("platform snapshot:\n%s", pformat(backend.debug_snapshot(), width=120))
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

    def bindings_for_layout(self, layout_id: str) -> list:
        return [item for item in self.config.hotkeys if item.layout_id == layout_id]

    def single_click_binding_for_layout(self, layout_id: str):
        return next((item for item in self.config.hotkeys if item.layout_id == layout_id and item.binding_type == "single_click"), None)

    def combo_binding_for_layout(self, layout_id: str):
        return next((item for item in self.config.hotkeys if item.layout_id == layout_id and item.binding_type == "combo"), None)

    def set_single_click_binding(self, layout_id: str, trigger_key: str | None) -> None:
        from one_click_kb_switch.core.hotkeys import upsert_single_click_binding

        self.config.hotkeys = upsert_single_click_binding(self.config.hotkeys, layout_id, trigger_key)
        self.config.save()
        self._rebuild_detectors()

    def apply_custom_binding(self, layout_id: str, key: str, modifiers: list[str]) -> None:
        from one_click_kb_switch.core.hotkeys import HotkeyBinding, upsert_custom_binding

        binding = HotkeyBinding(layout_id=layout_id, binding_type="combo", trigger_key=key, modifiers=modifiers)
        self.config.hotkeys = upsert_custom_binding(self.config.hotkeys, binding)
        self.config.save()
        self._rebuild_detectors()

    def clear_custom_binding(self, layout_id: str) -> None:
        from one_click_kb_switch.core.hotkeys import clear_custom_binding

        self.config.hotkeys = clear_custom_binding(self.config.hotkeys, layout_id)
        self.config.save()
        self._rebuild_detectors()

    def ignore_layout(self, layout_id: str) -> None:
        from one_click_kb_switch.core.hotkeys import clear_all_bindings

        self.config.hotkeys = clear_all_bindings(self.config.hotkeys, layout_id)
        self.config.save()
        self._rebuild_detectors()

    def switch_layout(self, layout_id: str) -> bool:
        logger = get_logger()
        try:
            if self.debug:
                logger.debug("switch_layout request: %s", layout_id)
            self.backend.switch_layout(layout_id)
            self.state.last_switch_error = None
            self.refresh_active_layout()
            if self.debug:
                logger.debug("switch_layout success, active layout now: %s", self.state.active_layout_id)
            return True
        except Exception as exc:  # noqa: BLE001
            self.state.last_switch_error = str(exc)
            logger.warning("switch_layout failed for %s: %s", layout_id, exc)
            return False

    def start_hooks(self, callback: Callable[[str], None]) -> None:
        logger = get_logger()

        def on_event(event: InputEvent) -> None:
            if self.debug and event.key in self._detectors:
                logger.debug("input event: %s %s", event.key, event.kind)
            for detector, layout_id in self._detectors.values():
                if detector.feed(event):
                    if self.debug:
                        logger.debug("single-click trigger matched layout: %s", layout_id)
                    callback(layout_id)

        self.backend.start_input_hooks(on_event)

    def stop_hooks(self) -> None:
        self.backend.stop_input_hooks()
