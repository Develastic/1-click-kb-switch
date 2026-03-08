from __future__ import annotations

from pathlib import Path
import sys


PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parents[1]


def bundle_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return REPO_ROOT


def asset_path(*parts: str) -> Path:
    roots = [bundle_root() / "assets", bundle_root() / "app" / "assets"]
    suffix = Path(*parts)
    for root in roots:
        candidate = root / suffix
        if candidate.exists():
            return candidate
    return roots[0] / suffix
