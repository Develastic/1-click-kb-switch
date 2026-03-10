from one_click_kb_switch.platform.linux_x11.backend import LinuxX11Backend


def test_parse_setxkbmap_query_preserves_variants_and_options():
    payload = LinuxX11Backend._parse_setxkbmap_query(
        "rules:      evdev\nmodel:      pc105\nlayout:     us,ru\nvariant:    ,phonetic\noptions:    grp:ctrl_space_toggle,compose:ralt\n"
    )
    assert payload["options"] == ["grp:ctrl_space_toggle", "compose:ralt"]
    assert payload["layouts"][0]["layout_id"] == "us"
    assert payload["layouts"][1]["layout_id"] == "ru:phonetic"
    assert payload["layouts"][1]["display_name"] == "RU (phonetic)"
