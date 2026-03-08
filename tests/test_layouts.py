from one_click_kb_switch.core.layouts import build_layout, choose_default_pair, generate_auto_label, is_english_layout


def test_detects_english_layouts():
    assert is_english_layout('English US')
    assert is_english_layout('US')
    assert not is_english_layout('Greek')


def test_generates_labels():
    assert generate_auto_label('United States') == 'UN'
    assert generate_auto_label('RU') == 'RU'
    assert generate_auto_label('') == 'KB'


def test_choose_default_pair():
    layouts = [build_layout('us', 'US'), build_layout('gr', 'Greek')]
    assert choose_default_pair(layouts) == ('us', 'gr')
