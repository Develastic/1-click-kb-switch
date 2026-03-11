from __future__ import annotations

from dataclasses import dataclass

from one_click_kb_switch.core.models import HotkeyBinding

PRIMARY_DEFAULT_KEY = "LeftCtrl"
SECONDARY_DEFAULT_KEY = "LeftShift"
LEGACY_PRIMARY_DEFAULT_KEY = "RightCtrl"
LEGACY_SECONDARY_DEFAULT_KEY = "RightShift"
SINGLE_CLICK_OPTIONS = ["Ignore", "LeftCtrl", "LeftShift", "RightCtrl", "RightShift"]


class HotkeyConflictError(ValueError):
    pass


def normalize_modifier_names(modifiers: list[str]) -> list[str]:
    aliases = {
        "leftctrl": "LeftCtrl",
        "rightctrl": "RightCtrl",
        "leftshift": "LeftShift",
        "rightshift": "RightShift",
        "leftalt": "LeftAlt",
        "rightalt": "RightAlt",
        "leftsuper": "LeftSuper",
        "rightsuper": "RightSuper",
    }
    normalized = set()
    for item in modifiers:
        token = item.strip()
        if not token:
            continue
        normalized.add(aliases.get(token.replace("_", "").replace(" ", "").lower(), token))
    return sorted(normalized)


def canonical_binding(binding: HotkeyBinding) -> str:
    if binding.binding_type == "single_click":
        return f"single:{normalize_modifier_names([binding.trigger_key])[0] if binding.trigger_key else ''}"
    modifier_text = "+".join(normalize_modifier_names(binding.modifiers))
    trigger_key = normalize_modifier_names([binding.trigger_key])[0] if binding.trigger_key in {
        "LeftCtrl", "RightCtrl", "LeftShift", "RightShift", "LeftAlt", "RightAlt", "LeftSuper", "RightSuper"
    } else binding.trigger_key.strip()
    return f"combo:{modifier_text}+{trigger_key}"


def validate_binding(binding: HotkeyBinding) -> None:
    if not binding.layout_id:
        raise ValueError("layout_id is required")
    if not binding.trigger_key:
        raise ValueError("trigger_key is required")
    if binding.binding_type not in {"single_click", "combo"}:
        raise ValueError("Unsupported binding type")
    if binding.binding_type == "single_click" and binding.modifiers:
        raise ValueError("Single-click binding must not contain modifiers")


def validate_unique(bindings: list[HotkeyBinding]) -> None:
    seen: dict[str, HotkeyBinding] = {}
    for binding in bindings:
        validate_binding(binding)
        key = canonical_binding(binding)
        if key in seen:
            raise HotkeyConflictError(f"Conflicting binding: {key}")
        seen[key] = binding


def default_bindings(english_layout_id: str | None, non_english_layout_id: str | None) -> list[HotkeyBinding]:
    bindings: list[HotkeyBinding] = []
    if english_layout_id:
        bindings.append(HotkeyBinding(layout_id=english_layout_id, binding_type="single_click", trigger_key=PRIMARY_DEFAULT_KEY))
    if non_english_layout_id:
        bindings.append(HotkeyBinding(layout_id=non_english_layout_id, binding_type="single_click", trigger_key=SECONDARY_DEFAULT_KEY))
    return bindings


def legacy_default_bindings(english_layout_id: str | None, non_english_layout_id: str | None) -> list[HotkeyBinding]:
    bindings: list[HotkeyBinding] = []
    if english_layout_id:
        bindings.append(HotkeyBinding(layout_id=english_layout_id, binding_type="single_click", trigger_key=LEGACY_PRIMARY_DEFAULT_KEY))
    if non_english_layout_id:
        bindings.append(HotkeyBinding(layout_id=non_english_layout_id, binding_type="single_click", trigger_key=LEGACY_SECONDARY_DEFAULT_KEY))
    return bindings


def has_legacy_default_bindings(bindings: list[HotkeyBinding], english_layout_id: str | None, non_english_layout_id: str | None) -> bool:
    legacy = legacy_default_bindings(english_layout_id, non_english_layout_id)
    if len(bindings) != len(legacy):
        return False
    return {canonical_binding(item) for item in bindings} == {canonical_binding(item) for item in legacy}


def upsert_custom_binding(bindings: list[HotkeyBinding], new_binding: HotkeyBinding) -> list[HotkeyBinding]:
    filtered = [item for item in bindings if not (item.layout_id == new_binding.layout_id and item.binding_type == "combo")]
    filtered.append(new_binding)
    validate_unique(filtered)
    return filtered


def upsert_single_click_binding(bindings: list[HotkeyBinding], layout_id: str, trigger_key: str | None) -> list[HotkeyBinding]:
    filtered = [item for item in bindings if not (item.layout_id == layout_id and item.binding_type == "single_click")]
    if trigger_key:
        filtered.append(HotkeyBinding(layout_id=layout_id, binding_type="single_click", trigger_key=trigger_key))
    validate_unique(filtered)
    return filtered


def clear_custom_binding(bindings: list[HotkeyBinding], layout_id: str) -> list[HotkeyBinding]:
    return [item for item in bindings if not (item.layout_id == layout_id and item.binding_type == "combo")]


def clear_all_bindings(bindings: list[HotkeyBinding], layout_id: str) -> list[HotkeyBinding]:
    return [item for item in bindings if item.layout_id != layout_id]


@dataclass(slots=True)
class InputEvent:
    key: str
    kind: str


class SingleClickDetector:
    def __init__(self, target_key: str) -> None:
        self.target_key = target_key
        self._pressed = False
        self._blocked = False

    def feed(self, event: InputEvent) -> bool:
        if event.kind == "mouse":
            if self._pressed:
                self._blocked = True
            return False
        if event.key == self.target_key and event.kind == "down":
            self._pressed = True
            self._blocked = False
            return False
        if event.key == self.target_key and event.kind == "up":
            should_trigger = self._pressed and not self._blocked
            self._pressed = False
            self._blocked = False
            return should_trigger
        if self._pressed and event.kind in {"down", "up"}:
            self._blocked = True
        return False
