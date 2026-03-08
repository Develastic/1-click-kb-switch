from __future__ import annotations

from string import ascii_letters

from one_click_kb_switch.core.models import LayoutInfo

ENGLISH_NAMES = {
    "en",
    "english",
    "english us",
    "english uk",
    "us",
    "gb",
    "united states",
    "united kingdom",
}


def normalize_display_name(value: str) -> str:
    return " ".join(value.strip().split())


def is_english_layout(name: str) -> bool:
    normalized = normalize_display_name(name).lower()
    return normalized in ENGLISH_NAMES or normalized.startswith("english") or normalized in {"us", "gb"}


def generate_auto_label(name: str) -> str:
    letters = [char for char in normalize_display_name(name) if char in ascii_letters]
    if len(letters) >= 2:
        return f"{letters[0]}{letters[1]}".upper()
    if len(letters) == 1:
        return f"{letters[0]}K".upper()
    compact = normalize_display_name(name).replace(" ", "")
    if len(compact) >= 2:
        return compact[:2].upper()
    return "KB"


def build_layout(layout_id: str, display_name: str, label_override: str = "") -> LayoutInfo:
    normalized_name = normalize_display_name(display_name)
    return LayoutInfo(
        layout_id=layout_id,
        display_name=normalized_name,
        is_english=is_english_layout(normalized_name),
        auto_label=generate_auto_label(normalized_name),
        label_override=label_override.strip().upper(),
    )


def choose_default_pair(layouts: list[LayoutInfo]) -> tuple[str | None, str | None]:
    english = next((item.layout_id for item in layouts if item.is_english), None)
    non_english = next((item.layout_id for item in layouts if not item.is_english), None)
    return english, non_english
