from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

from one_click_kb_switch.config import load_metadata


@dataclass(frozen=True, slots=True)
class AppPaths:
    config_dir: Path
    data_dir: Path
    log_dir: Path
    runtime_dir: Path
    config_file: Path
    html_log_file: Path
    instance_lock_file: Path

    @classmethod
    def detect(cls) -> "AppPaths":
        metadata = load_metadata()
        dirs = PlatformDirs(appname=metadata.canonical_name, appauthor=metadata.company, roaming=True)
        config_dir = Path(dirs.user_config_dir)
        data_dir = Path(dirs.user_data_dir)
        log_dir = Path(dirs.user_log_dir)
        runtime_root = Path(dirs.user_runtime_dir or dirs.user_data_dir)
        runtime_dir = runtime_root / "runtime"
        return cls(
            config_dir=config_dir,
            data_dir=data_dir,
            log_dir=log_dir,
            runtime_dir=runtime_dir,
            config_file=config_dir / "config.json",
            html_log_file=log_dir / "session.html",
            instance_lock_file=runtime_dir / "instance.lock",
        )

    def ensure(self) -> None:
        for directory in {self.config_dir, self.data_dir, self.log_dir, self.runtime_dir}:
            directory.mkdir(parents=True, exist_ok=True)
