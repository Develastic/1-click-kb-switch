from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont
import pystray

from one_click_kb_switch.config import load_metadata
from one_click_kb_switch.paths import asset_path


def _font_candidates() -> list[Path]:
    repo_font = asset_path("fonts", "dejavusans.ttf")
    candidates = [repo_font]
    if Path("C:/Windows/Fonts/segoeui.ttf").exists():
        candidates.insert(0, Path("C:/Windows/Fonts/segoeui.ttf"))
    return candidates


def load_tray_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in _font_candidates():
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    raise RuntimeError("No tray font is available. Ensure Tk/Pillow build includes font support and bundled font exists.")


def render_tray_icon(label: str) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (32, 32, 32, 255))
    draw = ImageDraw.Draw(image)
    font = load_tray_font(28)
    text = (label or "KB")[:2].upper()
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.rounded_rectangle((0, 0, 63, 63), radius=12, fill=(23, 112, 214, 255))
    draw.text(((64 - width) / 2, (64 - height) / 2 - 2), text, font=font, fill=(255, 255, 255, 255))
    return image


class TrayIcon:
    def __init__(self, label: str, on_show: Callable[[], None], on_exit: Callable[[], None]) -> None:
        metadata = load_metadata()
        self._icon = pystray.Icon(
            metadata.canonical_name,
            render_tray_icon(label),
            metadata.canonical_name,
            menu=pystray.Menu(
                pystray.MenuItem("Show main window", lambda *_: on_show()),
                pystray.MenuItem("Exit", lambda *_: on_exit()),
            ),
        )

    def run(self) -> None:
        self._icon.run_detached()

    def update_label(self, label: str) -> None:
        self._icon.icon = render_tray_icon(label)
        self._icon.visible = True

    def stop(self) -> None:
        self._icon.stop()
