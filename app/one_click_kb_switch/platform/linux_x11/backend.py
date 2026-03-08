from __future__ import annotations

import subprocess
from threading import Event, Thread
from typing import Callable

from Xlib import X, display
from Xlib.ext import record
from Xlib.protocol import rq

from one_click_kb_switch.core.hotkeys import InputEvent
from one_click_kb_switch.core.layouts import build_layout
from one_click_kb_switch.core.models import LayoutInfo, PlatformWarning
from one_click_kb_switch.platform.base import PlatformBackend


class LinuxX11Backend(PlatformBackend):
    def __init__(self) -> None:
        self._record_display = None
        self._local_display = None
        self._record_context = None
        self._thread: Thread | None = None
        self._stop = Event()

    def list_layouts(self) -> list[LayoutInfo]:
        output = subprocess.check_output(["setxkbmap", "-query"], text=True)
        layouts_line = next((line for line in output.splitlines() if line.startswith("layout:")), "layout: us")
        layouts = [item.strip() for item in layouts_line.split(":", 1)[1].split(",") if item.strip()]
        return [build_layout(layout_id=item, display_name=item.upper()) for item in layouts]

    def get_active_layout(self) -> str | None:
        output = subprocess.check_output(["setxkbmap", "-query"], text=True)
        layouts_line = next((line for line in output.splitlines() if line.startswith("layout:")), "layout: us")
        return layouts_line.split(":", 1)[1].split(",")[0].strip()

    def switch_layout(self, layout_id: str) -> None:
        subprocess.check_call(["setxkbmap", layout_id])

    def start_input_hooks(self, callback: Callable[[InputEvent], None]) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._listen, args=(callback,), daemon=True)
        self._thread.start()

    def stop_input_hooks(self) -> None:
        self._stop.set()
        if self._record_display and self._record_context:
            self._record_display.record_disable_context(self._record_context)

    def get_platform_warnings(self) -> list[PlatformWarning]:
        return []

    def _listen(self, callback: Callable[[InputEvent], None]) -> None:
        self._local_display = display.Display()
        self._record_display = display.Display()
        if not self._record_display.has_extension("RECORD"):
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
                    key = self._local_display.keycode_to_keysym(event.detail, 0)
                    key_name = {105: "RightCtrl", 62: "RightShift"}.get(event.detail, str(key))
                    callback(InputEvent(key=key_name, kind="down"))
                elif event.type == X.KeyRelease:
                    key = self._local_display.keycode_to_keysym(event.detail, 0)
                    key_name = {105: "RightCtrl", 62: "RightShift"}.get(event.detail, str(key))
                    callback(InputEvent(key=key_name, kind="up"))
                elif event.type in {X.ButtonPress, X.ButtonRelease}:
                    callback(InputEvent(key="Mouse", kind="mouse"))

        self._record_display.record_enable_context(self._record_context, handler)
