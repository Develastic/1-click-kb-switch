from pathlib import Path

from one_click_kb_switch.core.config import AppConfig


def test_defaults_can_be_created(tmp_path: Path):
    target = tmp_path / 'config.json'
    config = AppConfig.create_from_defaults(target)
    assert target.exists()
    assert config.schema_version == 1
