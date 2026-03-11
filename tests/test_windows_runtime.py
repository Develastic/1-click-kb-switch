import sys

import pytest

from one_click_kb_switch.single_instance import SingleInstanceGuard


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only import test")
def test_windows_backend_module_imports():
    import one_click_kb_switch.platform.windows.backend as backend

    assert backend.LRESULT is not None


def test_single_instance_release_is_safe_without_lock(tmp_path):
    guard = SingleInstanceGuard(tmp_path / "instance.lock")
    guard.handle = (tmp_path / "instance.lock").open("w", encoding="utf-8")
    guard.locked = False

    guard.release()

    assert guard.handle is None
    assert guard.locked is False
