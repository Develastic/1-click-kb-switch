import sys
from pathlib import Path

import pytest

if sys.platform == "win32":
    pytestmark = pytest.mark.skip(reason="Linux X11 backend tests are not applicable on Windows")
else:
    from one_click_kb_switch.logging_utils import configure_logging
    from one_click_kb_switch.platform.linux_x11.backend import LinuxX11Backend


def test_parse_setxkbmap_query_preserves_variants_and_options():
    payload = LinuxX11Backend._parse_setxkbmap_query(
        "rules:      evdev\nmodel:      pc105\nlayout:     us,ru\nvariant:    ,phonetic\noptions:    grp:ctrl_space_toggle,compose:ralt\n"
    )
    assert payload["options"] == ["grp:ctrl_space_toggle", "compose:ralt"]
    assert payload["layouts"][0]["layout_id"] == "us"
    assert payload["layouts"][1]["layout_id"] == "ru:phonetic"
    assert payload["layouts"][1]["display_name"] == "RU (phonetic)"


def test_resolve_toggle_sequence_uses_existing_xkb_option():
    configure_logging(debug=True, html_log_path=Path("/tmp/one-click-kb-switch-test-log.html"))
    backend = LinuxX11Backend()
    payload = LinuxX11Backend._parse_setxkbmap_query(
        "rules:      evdev\nmodel:      pc105\nlayout:     us,ru\nvariant:    ,rud_rus\noptions:    grp:ctrl_space_toggle\n"
    )

    assert backend._resolve_toggle_sequence(payload) == ["LeftCtrl", "Space"]
