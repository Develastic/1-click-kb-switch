from __future__ import annotations

import os
import shutil
import subprocess
from threading import Event, Thread
from typing import Callable

from Xlib import X, display
from Xlib.ext import record
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
        raise RuntimeError(
            "Linux X11 directed switching is temporarily disabled in this build because the current implementation cannot switch layouts without risking user XKB settings. Run with --debug and inspect the console diagnostics."
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
        return [
            PlatformWarning(
                code="linux-x11-switch-disabled",
                message="Linux X11 directed switching is disabled in this build until a non-destructive layout switch path is implemented.",
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
        output = self._run_optional_command(["xset", "-q"])
        if not output:
            return 0
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
