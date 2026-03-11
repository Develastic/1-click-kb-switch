from __future__ import annotations

from ctypes import POINTER, Structure, byref, c_int, c_long, c_size_t, c_ssize_t, c_void_p, windll
from ctypes.wintypes import DWORD, HINSTANCE, HKL, HWND, LPARAM, WPARAM

LRESULT = c_ssize_t
from threading import Event, Thread
from typing import Callable

from one_click_kb_switch.core.hotkeys import InputEvent
from one_click_kb_switch.core.layouts import build_layout
from one_click_kb_switch.core.models import LayoutInfo, PlatformWarning
from one_click_kb_switch.platform.base import PlatformBackend

user32 = windll.user32
kernel32 = windll.kernel32
WM_INPUTLANGCHANGEREQUEST = 0x0050
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_RBUTTONDOWN = 0x0204
WM_LBUTTONDOWN = 0x0201
HC_ACTION = 0
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3
VK_LSHIFT = 0xA0
VK_RSHIFT = 0xA1


COMMON_LAYOUT_NAMES = {
    "00000409": "English US",
    "00000809": "English UK",
    "00000419": "Russian",
    "00000408": "Greek",
    "00000407": "German",
    "0000040C": "French",
    "00000804": "Chinese",
}

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [("vkCode", DWORD), ("scanCode", DWORD), ("flags", DWORD), ("time", DWORD), ("dwExtraInfo", c_size_t)]


class MSLLHOOKSTRUCT(Structure):
    _fields_ = [("pt_x", c_long), ("pt_y", c_long), ("mouseData", DWORD), ("flags", DWORD), ("time", DWORD), ("dwExtraInfo", c_size_t)]


class WindowsBackend(PlatformBackend):
    def __init__(self) -> None:
        self._hook_thread: Thread | None = None
        self._stop_event = Event()
        self._callback: Callable[[InputEvent], None] | None = None

    def list_layouts(self) -> list[LayoutInfo]:
        count = user32.GetKeyboardLayoutList(0, None)
        handles = (HKL * count)()
        user32.GetKeyboardLayoutList(count, handles)
        items: list[LayoutInfo] = []
        for handle in handles:
            layout_id = f"{handle & 0xFFFFFFFF:08X}"
            display_name = COMMON_LAYOUT_NAMES.get(layout_id, layout_id)
            items.append(build_layout(layout_id, display_name))
        return items

    def get_active_layout(self) -> str | None:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        thread_id = user32.GetWindowThreadProcessId(hwnd, None)
        hkl = user32.GetKeyboardLayout(thread_id)
        return f"{hkl & 0xFFFFFFFF:08X}"

    def switch_layout(self, layout_id: str) -> None:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            raise RuntimeError("No foreground window is available")
        target = int(layout_id, 16)
        user32.PostMessageW(hwnd, WM_INPUTLANGCHANGEREQUEST, 0, LPARAM(target))
        user32.ActivateKeyboardLayout(HKL(target), 0)

    def start_input_hooks(self, callback: Callable[[InputEvent], None]) -> None:
        self._callback = callback
        if self._hook_thread and self._hook_thread.is_alive():
            return
        self._stop_event.clear()
        self._hook_thread = Thread(target=self._run_hook_loop, daemon=True)
        self._hook_thread.start()

    def stop_input_hooks(self) -> None:
        self._stop_event.set()

    def get_platform_warnings(self) -> list[PlatformWarning]:
        return []

    def debug_snapshot(self) -> dict[str, object]:
        return {
            "backend": "windows-winapi",
            "installed_layouts": [item.layout_id for item in self.list_layouts()],
            "active_layout": self.get_active_layout(),
        }

    def _run_hook_loop(self) -> None:
        from ctypes import CFUNCTYPE, cast
        from ctypes.wintypes import MSG

        keyboard_callback_type = CFUNCTYPE(LRESULT, c_int, WPARAM, LPARAM)
        mouse_callback_type = CFUNCTYPE(LRESULT, c_int, WPARAM, LPARAM)

        @keyboard_callback_type
        def keyboard_proc(code: int, wparam: WPARAM, lparam: LPARAM) -> LRESULT:
            if code == HC_ACTION and self._callback:
                payload = cast(lparam, POINTER(KBDLLHOOKSTRUCT)).contents
                key_name = {VK_LCONTROL: "LeftCtrl", VK_RCONTROL: "RightCtrl", VK_LSHIFT: "LeftShift", VK_RSHIFT: "RightShift"}.get(payload.vkCode, f"VK_{payload.vkCode}")
                if wparam in {WM_KEYDOWN, WM_SYSKEYDOWN}:
                    self._callback(InputEvent(key=key_name, kind="down"))
                elif wparam in {WM_KEYUP, WM_SYSKEYUP}:
                    self._callback(InputEvent(key=key_name, kind="up"))
            return user32.CallNextHookEx(None, code, wparam, lparam)

        @mouse_callback_type
        def mouse_proc(code: int, wparam: WPARAM, lparam: LPARAM) -> LRESULT:
            if code == HC_ACTION and self._callback and wparam in {WM_LBUTTONDOWN, WM_RBUTTONDOWN}:
                self._callback(InputEvent(key="Mouse", kind="mouse"))
            return user32.CallNextHookEx(None, code, wparam, lparam)

        h_instance = kernel32.GetModuleHandleW(None)
        keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, keyboard_proc, HINSTANCE(h_instance), 0)
        mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_proc, HINSTANCE(h_instance), 0)
        msg = MSG()
        while not self._stop_event.is_set() and user32.GetMessageW(byref(msg), HWND(0), 0, 0) != 0:
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))
        if keyboard_hook:
            user32.UnhookWindowsHookEx(keyboard_hook)
        if mouse_hook:
            user32.UnhookWindowsHookEx(mouse_hook)
