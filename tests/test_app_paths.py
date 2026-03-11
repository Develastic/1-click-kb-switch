from pathlib import Path

from one_click_kb_switch.app_paths import AppPaths


def test_detected_paths_point_to_os_managed_locations():
    paths = AppPaths.detect()

    assert paths.config_file.name == "config.json"
    assert paths.html_log_file.name == "session.html"
    assert paths.instance_lock_file.name == "instance.lock"
    assert isinstance(paths.config_dir, Path)
    assert isinstance(paths.data_dir, Path)
    assert isinstance(paths.log_dir, Path)
    assert isinstance(paths.runtime_dir, Path)
