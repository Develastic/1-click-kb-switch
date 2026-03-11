from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

from one_click_kb_switch.logging_utils import get_logger
from one_click_kb_switch.paths import asset_path


class SwitchSoundPlayer:
    def __init__(self) -> None:
        self.sound_file = asset_path("sounds", "switch-click.wav")
        self._linux_player = shutil.which("paplay") if sys.platform.startswith("linux") else None
        self._warned_missing_asset = False
        self._warned_unsupported_runtime = False

    def play(self) -> None:
        logger = get_logger()
        if not self.sound_file.exists():
            if not self._warned_missing_asset:
                logger.warning("Switch sound asset is missing: %s", self.sound_file)
                self._warned_missing_asset = True
            return

        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(
                str(self.sound_file),
                winsound.SND_ASYNC | winsound.SND_FILENAME | winsound.SND_NODEFAULT,
            )
            logger.debug("Played switch sound via winsound: %s", self.sound_file)
            return

        if sys.platform.startswith("linux"):
            if not self._linux_player:
                if not self._warned_unsupported_runtime:
                    logger.warning("Switch sound requires paplay on Linux, but it was not found in PATH")
                    self._warned_unsupported_runtime = True
                return
            subprocess.Popen(
                [self._linux_player, str(self.sound_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            logger.debug("Played switch sound via %s: %s", self._linux_player, self.sound_file)
            return

        if not self._warned_unsupported_runtime:
            logger.warning("Switch sound is not implemented for platform: %s", sys.platform)
            self._warned_unsupported_runtime = True


__all__ = ["SwitchSoundPlayer"]
