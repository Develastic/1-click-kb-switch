from __future__ import annotations

import os
import sys

from one_click_kb_switch.platform.base import PlatformBackend
from one_click_kb_switch.platform.linux_wayland.backend import LinuxWaylandBackend
from one_click_kb_switch.platform.linux_x11.backend import LinuxX11Backend
from one_click_kb_switch.platform.windows.backend import WindowsBackend


def create_platform_backend() -> PlatformBackend:
    if sys.platform == "win32":
        return WindowsBackend()
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland":
        return LinuxWaylandBackend()
    return LinuxX11Backend()
