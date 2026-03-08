import pytest

from one_click_kb_switch.core.hotkeys import HotkeyConflictError, InputEvent, SingleClickDetector, default_bindings, validate_unique
from one_click_kb_switch.core.models import HotkeyBinding


def test_default_bindings():
    bindings = default_bindings('us', 'gr')
    assert bindings[0].trigger_key == 'RightCtrl'
    assert bindings[1].trigger_key == 'RightShift'


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
