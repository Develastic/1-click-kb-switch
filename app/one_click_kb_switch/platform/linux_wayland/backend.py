from __future__ import annotations

from one_click_kb_switch.core.models import PlatformWarning
from one_click_kb_switch.platform.linux_x11.backend import LinuxX11Backend


class LinuxWaylandBackend(LinuxX11Backend):
    def get_platform_warnings(self) -> list[PlatformWarning]:
        return [
            PlatformWarning(
                code="wayland-experimental",
                message="Wayland support is experimental. Global single-click hooks may be limited by compositor security rules.",
            )
        ]
