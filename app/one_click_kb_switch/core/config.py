from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from one_click_kb_switch.app_paths import AppPaths
from one_click_kb_switch.config import load_metadata
from one_click_kb_switch.paths import asset_path
from one_click_kb_switch.core.hotkeys import validate_unique
from one_click_kb_switch.core.models import HotkeyBinding


@dataclass(slots=True)
class AppConfig:
    schema_version: int
    has_completed_first_run: bool
    start_minimized_after_first_run: bool
    play_switch_sound: bool
    label_overrides: dict[str, str] = field(default_factory=dict)
    hotkeys: list[HotkeyBinding] = field(default_factory=list)

    @classmethod
    def defaults_path(cls) -> Path:
        return asset_path("config.json.defaults")

    @classmethod
    def user_config_path(cls) -> Path:
        return AppPaths.detect().config_file

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        target = path or cls.user_config_path()
        payload = json.loads(target.read_text(encoding="utf-8"))
        config = cls.from_dict(payload)
        config.validate()
        return config

    def save(self, path: Path | None = None) -> None:
        target = path or self.user_config_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def create_from_defaults(cls, path: Path | None = None) -> "AppConfig":
        config = cls.from_dict(json.loads(cls.defaults_path().read_text(encoding="utf-8")))
        config.validate()
        config.save(path)
        return config

    @classmethod
    def from_dict(cls, payload: dict) -> "AppConfig":
        return cls(
            schema_version=int(payload["schema_version"]),
            has_completed_first_run=bool(payload.get("has_completed_first_run", False)),
            start_minimized_after_first_run=bool(payload.get("start_minimized_after_first_run", True)),
            play_switch_sound=bool(payload.get("play_switch_sound", False)),
            label_overrides={str(key): str(value).upper() for key, value in payload.get("label_overrides", {}).items()},
            hotkeys=[HotkeyBinding(**item) for item in payload.get("hotkeys", [])],
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "has_completed_first_run": self.has_completed_first_run,
            "start_minimized_after_first_run": self.start_minimized_after_first_run,
            "play_switch_sound": self.play_switch_sound,
            "label_overrides": self.label_overrides,
            "hotkeys": [asdict(item) for item in self.hotkeys],
        }

    def validate(self) -> None:
        expected = load_metadata().config_schema_version
        if self.schema_version != expected:
            raise ValueError(f"Unsupported config schema version: {self.schema_version}")
        validate_unique(self.hotkeys)
