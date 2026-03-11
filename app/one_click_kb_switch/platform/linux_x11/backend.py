from __future__ import annotations

import os
import re
import shutil
import subprocess
from threading import Event, Thread
import time
from typing import Callable

from Xlib import X, display
from Xlib.ext import record
from Xlib.ext import xtest
from Xlib.keysymdef import latin1
from Xlib.XK import string_to_keysym
from Xlib.protocol import rq

from one_click_kb_switch.core.hotkeys import InputEvent
from one_click_kb_switch.core.layouts import build_layout
from one_click_kb_switch.core.models import LayoutInfo, PlatformWarning
from one_click_kb_switch.logging_utils import get_logger
from one_click_kb_switch.platform.base import PlatformBackend

KEYCODE_MAP = {
    37: "LeftCtrl",
    105: "RightCtrl",
    50: "LeftShift",
    62: "RightShift",
}

TOGGLE_OPTION_KEY_MAP: dict[str, list[str]] = {
    "grp:ctrl_space_toggle": ["LeftCtrl", "Space"],
    "grp:alt_shift_toggle": ["LeftAlt", "LeftShift"],
    "grp:ctrl_shift_toggle": ["LeftCtrl", "LeftShift"],
    "grp:lalt_toggle": ["LeftAlt"],
    "grp:ralt_toggle": ["RightAlt"],
    "grp:shift_caps_toggle": ["LeftShift", "CapsLock"],
}

KEYSYM_NAME_MAP = {
    "LeftCtrl": "Control_L",
    "RightCtrl": "Control_R",
    "LeftShift": "Shift_L",
    "RightShift": "Shift_R",
    "LeftAlt": "Alt_L",
    "RightAlt": "Alt_R",
    "Space": "space",
    "CapsLock": "Caps_Lock",
}


class LinuxX11Backend(PlatformBackend):
    def __init__(self) -> None:
        self._record_display = None
        self._local_display = None
        self._record_context = None
        self._thread: Thread | None = None
        self._stop = Event()
        self._logger = get_logger()

    def list_layouts(self) -> list[LayoutInfo]:
        query = self._query_xkb_state()
        return [
            build_layout(layout_id=item["layout_id"], display_name=item["display_name"])
            for item in query["layouts"]
        ]

    def get_active_layout(self) -> str | None:
        query = self._query_xkb_state()
        layouts = query["layouts"]
        if not layouts:
            return None
        active_index = self._active_group_index()
        if 0 <= active_index < len(layouts):
            return str(layouts[active_index]["layout_id"])
        return str(layouts[0]["layout_id"])

    def switch_layout(self, layout_id: str) -> None:
        self._logger.debug("linux_x11 switch requested: %s", layout_id)
        query = self._query_xkb_state()
        available_ids = [str(item["layout_id"]) for item in query["layouts"]]
        if layout_id not in available_ids:
            raise RuntimeError(f"Requested layout is not part of the current XKB configuration: {layout_id}")
        target_index = available_ids.index(layout_id)
        current_index = self._active_group_index()
        if current_index == target_index:
            self._logger.debug("linux_x11 switch skipped: target layout already active")
            return

        toggle_sequence = self._resolve_toggle_sequence(query)
        if not toggle_sequence:
            raise RuntimeError(
                "Unable to switch layouts safely on Linux X11 because the current user switching method is not recognized. Run with --debug and inspect the reported XKB options."
            )

        max_attempts = max(len(available_ids), 1)
        for _ in range(max_attempts):
            self._emit_key_combo(toggle_sequence)
            time.sleep(0.05)
            current_index = self._active_group_index()
            if current_index == target_index:
                self._logger.debug("linux_x11 switch succeeded using existing toggle sequence: %s", "+".join(toggle_sequence))
                return

        raise RuntimeError(
            f"Failed to reach requested layout '{layout_id}' through the user's existing XKB toggle path ({'+'.join(toggle_sequence)})."
        )

    def start_input_hooks(self, callback: Callable[[InputEvent], None]) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._listen, args=(callback,), daemon=True)
        self._thread.start()
        self._logger.debug("linux_x11 input hooks started")

    def stop_input_hooks(self) -> None:
        self._stop.set()
        if self._record_display and self._record_context:
            self._record_display.record_disable_context(self._record_context)
        self._logger.debug("linux_x11 input hooks stopped")

    def get_platform_warnings(self) -> list[PlatformWarning]:
        query = self._query_xkb_state()
        if self._resolve_toggle_sequence(query):
            return []
        return [
            PlatformWarning(
                code="linux-x11-switch-unsupported",
                message="Linux X11 switching is limited because the current XKB toggle option is not recognized by this build.",
            )
        ]

    def debug_snapshot(self) -> dict[str, object]:
        query = self._query_xkb_state()
        return {
            "backend": "linux-x11-setxkbmap-observer",
            "session_type": os.environ.get("XDG_SESSION_TYPE", ""),
            "desktop": os.environ.get("XDG_CURRENT_DESKTOP", ""),
            "display": os.environ.get("DISPLAY", ""),
            "switching_system_detected": self._detect_switching_system(query),
            "toggle_sequence": self._resolve_toggle_sequence(query),
            "commands": {
                "setxkbmap": shutil.which("setxkbmap"),
                "localectl": shutil.which("localectl"),
                "xset": shutil.which("xset"),
                "xkb-switch": shutil.which("xkb-switch"),
            },
            "setxkbmap_query": query["raw_query"],
            "localectl_status": self._run_optional_command(["localectl", "status"]),
            "xset_q": self._run_optional_command(["xset", "-q"]),
            "layouts": query["layouts"],
            "active_group_index": self._active_group_index(),
            "active_layout": self.get_active_layout(),
        }

    def _listen(self, callback: Callable[[InputEvent], None]) -> None:
        self._local_display = display.Display()
        self._record_display = display.Display()
        if not self._record_display.has_extension("RECORD"):
            self._logger.warning("X11 RECORD extension is unavailable")
            return
        self._record_context = self._record_display.record_create_context(
            0,
            [record.AllClients],
            [{
                'core_requests': (0, 0),
                'core_replies': (0, 0),
                'ext_requests': (0, 0, 0, 0),
                'ext_replies': (0, 0, 0, 0),
                'delivered_events': (0, 0),
                'device_events': (X.KeyPress, X.ButtonRelease),
                'errors': (0, 0),
                'client_started': False,
                'client_died': False,
            }],
        )

        def handler(reply):
            if self._stop.is_set() or reply.category != record.FromServer or not reply.data:
                return
            data = reply.data
            while data:
                event, data = rq.EventField(None).parse_binary_value(data, self._local_display.display, None, None)
                if event.type == X.KeyPress:
                    callback(InputEvent(key=KEYCODE_MAP.get(event.detail, str(event.detail)), kind="down"))
                elif event.type == X.KeyRelease:
                    callback(InputEvent(key=KEYCODE_MAP.get(event.detail, str(event.detail)), kind="up"))
                elif event.type in {X.ButtonPress, X.ButtonRelease}:
                    callback(InputEvent(key="Mouse", kind="mouse"))

        self._record_display.record_enable_context(self._record_context, handler)

    def _query_xkb_state(self) -> dict[str, object]:
        raw_query = subprocess.check_output(["setxkbmap", "-query"], text=True)
        parsed = self._parse_setxkbmap_query(raw_query)
        parsed["raw_query"] = raw_query.strip()
        return parsed

    def _active_group_index(self) -> int:
        if shutil.which("xkb-switch"):
            try:
                active = subprocess.check_output(["xkb-switch", "-p"], text=True).strip()
                query = self._query_xkb_state()
                available_ids = [str(item["layout_id"]) for item in query["layouts"]]
                if active in available_ids:
                    return available_ids.index(active)
            except subprocess.CalledProcessError:
                pass
        output = self._run_optional_command(["xset", "-q"])
        if not output:
            return 0
        active_group = 0
        for match in re.finditer(r"Group\s+(\d+):\s+on", output, re.IGNORECASE):
            active_group = max(active_group, int(match.group(1)) - 1)
        if active_group:
            return active_group
        for line in output.splitlines():
            if "Group 2:" in line and "on" in line.lower():
                return 1
        return 0

    def _detect_switching_system(self, query: dict[str, object]) -> str:
        options = query.get("options") or []
        grp_options = [item for item in options if str(item).startswith("grp:")]
        if grp_options:
            return f"XKB group toggle via {', '.join(grp_options)}"
        return "No explicit XKB group toggle option detected"

    def _run_optional_command(self, command: list[str]) -> str:
        if shutil.which(command[0]) is None:
            return ""
        try:
            return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT).strip()
        except subprocess.CalledProcessError as exc:
            return exc.output.strip()

    @staticmethod
    def _parse_setxkbmap_query(raw_query: str) -> dict[str, object]:
        values: dict[str, str] = {}
        for line in raw_query.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()

        layouts = [item.strip() for item in values.get("layout", "us").split(",")]
        variants = [item.strip() for item in values.get("variant", "").split(",")]
        options = [item.strip() for item in values.get("options", "").split(",") if item.strip()]

        while len(variants) < len(layouts):
            variants.append("")

        parsed_layouts: list[dict[str, str]] = []
        for layout, variant in zip(layouts, variants, strict=False):
            display_name = layout.upper() if not variant else f"{layout.upper()} ({variant})"
            layout_id = layout if not variant else f"{layout}:{variant}"
            parsed_layouts.append(
                {
                    "layout": layout,
                    "variant": variant,
                    "layout_id": layout_id,
                    "display_name": display_name,
                }
            )

        return {
            "rules": values.get("rules", ""),
            "model": values.get("model", ""),
            "options": options,
            "layouts": parsed_layouts,
        }

    def _resolve_toggle_sequence(self, query: dict[str, object]) -> list[str] | None:
        options = [str(item) for item in query.get("options", [])]
        for option in options:
            if option in TOGGLE_OPTION_KEY_MAP:
                return TOGGLE_OPTION_KEY_MAP[option]
        return None

    def _emit_key_combo(self, keys: list[str]) -> None:
        local_display = display.Display()
        if not local_display.query_extension("XTEST").present:
            local_display.close()
            raise RuntimeError("XTEST extension is unavailable, cannot synthesize the user's configured layout toggle")
        try:
            keycodes = [self._keycode_for_name(local_display, key_name) for key_name in keys]
            for keycode in keycodes:
                xtest.fake_input(local_display, X.KeyPress, keycode)
            for keycode in reversed(keycodes):
                xtest.fake_input(local_display, X.KeyRelease, keycode)
            local_display.sync()
        finally:
            local_display.close()

    def _keycode_for_name(self, local_display: display.Display, key_name: str) -> int:
        keysym_name = KEYSYM_NAME_MAP.get(key_name, key_name)
        keysym = string_to_keysym(keysym_name)
        if keysym == 0 and len(keysym_name) == 1:
            keysym = ord(keysym_name)
        if keysym == 0:
            keysym = getattr(latin1, f"XK_{keysym_name}", 0)
        if keysym == 0:
            raise RuntimeError(f"Unsupported synthetic toggle key: {key_name}")
        keycode = local_display.keysym_to_keycode(keysym)
        if keycode == 0:
            raise RuntimeError(f"Unable to resolve X11 keycode for toggle key: {key_name}")
        return keycode
