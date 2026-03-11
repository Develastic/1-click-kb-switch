from pathlib import Path

from one_click_kb_switch.core.config import AppConfig


def test_defaults_can_be_created(tmp_path: Path):
    target = tmp_path / 'config.json'
    config = AppConfig.create_from_defaults(target)
    assert target.exists()
    assert config.schema_version == 2
    assert config.play_switch_sound is True


def test_schema_v1_is_migrated_to_sound_enabled(tmp_path: Path):
    target = tmp_path / "config.json"
    target.write_text(
        "{\n  \"schema_version\": 1,\n  \"has_completed_first_run\": false,\n  \"start_minimized_after_first_run\": true,\n  \"play_switch_sound\": false,\n  \"label_overrides\": {},\n  \"hotkeys\": []\n}\n",
        encoding="utf-8",
    )

    config = AppConfig.load(target)

    assert config.schema_version == 2
    assert config.play_switch_sound is True
