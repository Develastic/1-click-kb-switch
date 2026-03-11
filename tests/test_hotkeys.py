import pytest

from one_click_kb_switch.core.controller import RuntimeController
from one_click_kb_switch.core.hotkeys import (
    HotkeyConflictError,
    InputEvent,
    SingleClickDetector,
    default_bindings,
    normalize_modifier_names,
    upsert_single_click_binding,
    validate_unique,
)
from one_click_kb_switch.core.models import HotkeyBinding, LayoutInfo


def test_default_bindings():
    bindings = default_bindings('us', 'gr')
    assert bindings[0].trigger_key == 'LeftCtrl'
    assert bindings[1].trigger_key == 'LeftShift'


def test_conflicts_are_rejected():
    with pytest.raises(HotkeyConflictError):
        validate_unique([
            HotkeyBinding(layout_id='us', binding_type='single_click', trigger_key='RightCtrl'),
            HotkeyBinding(layout_id='gr', binding_type='single_click', trigger_key='RightCtrl'),
        ])


def test_single_click():
    detector = SingleClickDetector('RightCtrl')
    assert not detector.feed(InputEvent(key='RightCtrl', kind='down'))
    assert detector.feed(InputEvent(key='RightCtrl', kind='up'))
    assert not detector.feed(InputEvent(key='RightCtrl', kind='down'))
    assert not detector.feed(InputEvent(key='Mouse', kind='mouse'))
    assert not detector.feed(InputEvent(key='RightCtrl', kind='up'))


def test_upsert_single_click_binding_replaces_previous_layout_binding():
    bindings = [
        HotkeyBinding(layout_id='us', binding_type='single_click', trigger_key='LeftCtrl'),
        HotkeyBinding(layout_id='gr', binding_type='single_click', trigger_key='LeftShift'),
    ]

    updated = upsert_single_click_binding(bindings, 'gr', 'RightShift')

    assert any(item.layout_id == 'gr' and item.trigger_key == 'RightShift' for item in updated)
    assert not any(item.layout_id == 'gr' and item.trigger_key == 'LeftShift' for item in updated)


def test_normalize_modifier_names_preserves_side_specific_names():
    assert normalize_modifier_names(["leftctrl", "RightShift", "LeftCtrl"]) == ["LeftCtrl", "RightShift"]


def test_reconcile_hotkeys_upgrades_base_layout_to_single_detected_variant():
    bindings = [HotkeyBinding(layout_id="ru", binding_type="single_click", trigger_key="LeftShift")]
    layouts = [
        LayoutInfo(layout_id="us", display_name="US", is_english=True, auto_label="US"),
        LayoutInfo(layout_id="ru:rud_rus", display_name="RU (rud_rus)", is_english=False, auto_label="RU"),
    ]

    reconciled = RuntimeController._reconcile_hotkeys(bindings, layouts)

    assert reconciled[0].layout_id == "ru:rud_rus"
