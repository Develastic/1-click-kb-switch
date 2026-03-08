use anyhow::{Result, anyhow};
use global_hotkey::hotkey::{Code, HotKey, Modifiers};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::str::FromStr;
use thiserror::Error;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum BindingType {
    SingleClick,
    Combo,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HotkeyBinding {
    pub layout_id: String,
    pub binding_type: BindingType,
    pub key: String,
    #[serde(default)]
    pub modifiers: Vec<String>,
    pub display: String,
    #[serde(default)]
    pub is_custom: bool,
}

#[derive(Debug, Error)]
pub enum HotkeyError {
    #[error("layout_id is required")]
    MissingLayout,
    #[error("key is required")]
    MissingKey,
    #[error("single_click binding cannot contain modifiers")]
    SingleClickWithModifiers,
    #[error("binding conflict between layouts {existing} and {incoming}")]
    Conflict { existing: String, incoming: String },
}

impl HotkeyBinding {
    pub fn canonical(&self) -> String {
        let mut modifiers = self.modifiers.clone();
        modifiers.sort();
        let mut parts = modifiers;
        parts.push(self.key.clone());
        parts.push(match self.binding_type {
            BindingType::SingleClick => "single_click".to_string(),
            BindingType::Combo => "combo".to_string(),
        });
        parts.join("+")
    }

    pub fn validate(&self) -> Result<(), HotkeyError> {
        if self.layout_id.trim().is_empty() {
            return Err(HotkeyError::MissingLayout);
        }
        if self.key.trim().is_empty() {
            return Err(HotkeyError::MissingKey);
        }
        if matches!(self.binding_type, BindingType::SingleClick) && !self.modifiers.is_empty() {
            return Err(HotkeyError::SingleClickWithModifiers);
        }
        Ok(())
    }
}

pub fn default_bindings(
    english_id: Option<&str>,
    alternate_id: Option<&str>,
) -> (Vec<HotkeyBinding>, Vec<String>) {
    let mut bindings = Vec::new();
    let mut warnings = Vec::new();

    if let Some(layout_id) = english_id {
        bindings.push(HotkeyBinding {
            layout_id: layout_id.to_string(),
            binding_type: BindingType::SingleClick,
            key: "RightCtrl".to_string(),
            modifiers: Vec::new(),
            display: "RightCtrl (Single Click)".to_string(),
            is_custom: false,
        });
    } else {
        warnings.push("English layout was not detected.".to_string());
    }

    if let Some(layout_id) = alternate_id {
        bindings.push(HotkeyBinding {
            layout_id: layout_id.to_string(),
            binding_type: BindingType::SingleClick,
            key: "RightShift".to_string(),
            modifiers: Vec::new(),
            display: "RightShift (Single Click)".to_string(),
            is_custom: false,
        });
    } else {
        warnings.push("Alternative non-English layout was not detected.".to_string());
    }

    (bindings, warnings)
}

pub fn validate_unique(bindings: &[HotkeyBinding]) -> Result<(), HotkeyError> {
    let mut seen = HashMap::<String, String>::new();
    for binding in bindings {
        binding.validate()?;
        let canonical = binding.canonical();
        if let Some(existing) = seen.get(&canonical) {
            return Err(HotkeyError::Conflict {
                existing: existing.clone(),
                incoming: binding.layout_id.clone(),
            });
        }
        seen.insert(canonical, binding.layout_id.clone());
    }
    Ok(())
}

pub fn display_for_combo(modifiers: &[String], key: &str) -> String {
    let mut parts = normalize_modifier_names(modifiers);
    parts.push(key.to_string());
    parts.join(" + ")
}

pub fn normalize_modifier_names(modifiers: &[String]) -> Vec<String> {
    let mut normalized = modifiers
        .iter()
        .filter_map(|item| match item.trim().to_lowercase().as_str() {
            "ctrl" | "control" => Some("Ctrl".to_string()),
            "alt" => Some("Alt".to_string()),
            "shift" => Some("Shift".to_string()),
            "meta" | "super" | "win" => Some("Meta".to_string()),
            _ => None,
        })
        .collect::<Vec<_>>();
    normalized.sort();
    normalized.dedup();
    normalized
}

pub fn custom_bindings(bindings: &[HotkeyBinding]) -> Vec<HotkeyBinding> {
    bindings
        .iter()
        .filter(|item| item.is_custom)
        .cloned()
        .collect()
}

pub fn upsert_custom_binding(
    bindings: &mut Vec<HotkeyBinding>,
    binding: HotkeyBinding,
) -> Result<()> {
    bindings.retain(|item| !(item.is_custom && item.layout_id == binding.layout_id));
    bindings.push(binding);
    validate_unique(bindings).map_err(|err| anyhow!(err.to_string()))
}

pub fn clear_custom_binding(bindings: &mut Vec<HotkeyBinding>, layout_id: &str) -> bool {
    let before = bindings.len();
    bindings.retain(|item| !(item.is_custom && item.layout_id == layout_id));
    before != bindings.len()
}

pub fn binding_to_global_hotkey(binding: &HotkeyBinding) -> Result<HotKey> {
    if !matches!(binding.binding_type, BindingType::Combo) {
        return Err(anyhow!(
            "only combo bindings can be converted to global hotkeys"
        ));
    }

    let mods = normalize_modifier_names(&binding.modifiers)
        .into_iter()
        .fold(Modifiers::empty(), |mut acc, item| {
            match item.as_str() {
                "Ctrl" => acc |= Modifiers::CONTROL,
                "Alt" => acc |= Modifiers::ALT,
                "Shift" => acc |= Modifiers::SHIFT,
                "Meta" => acc |= Modifiers::SUPER,
                _ => {}
            }
            acc
        });

    let code = Code::from_str(&binding.key)
        .map_err(|err| anyhow!("unsupported hotkey key {}: {err}", binding.key))?;
    Ok(HotKey::new((!mods.is_empty()).then_some(mods), code))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InputEventKind {
    KeyDown,
    KeyUp,
    MouseClick,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InputEvent {
    pub kind: InputEventKind,
    pub key: String,
}

#[derive(Debug, Clone)]
pub struct SingleClickDetector {
    target: String,
    pressed: bool,
    other_activity: bool,
}

impl SingleClickDetector {
    pub fn new(target: impl Into<String>) -> Self {
        Self {
            target: target.into(),
            pressed: false,
            other_activity: false,
        }
    }

    pub fn feed(&mut self, event: &InputEvent) -> bool {
        match event.kind {
            InputEventKind::KeyDown => {
                if event.key == self.target && !self.pressed {
                    self.pressed = true;
                    self.other_activity = false;
                    return false;
                }
                if self.pressed {
                    self.other_activity = true;
                }
            }
            InputEventKind::KeyUp => {
                if event.key == self.target && self.pressed {
                    let trigger = !self.other_activity;
                    self.pressed = false;
                    self.other_activity = false;
                    return trigger;
                }
                if self.pressed {
                    self.other_activity = true;
                }
            }
            InputEventKind::MouseClick => {
                if self.pressed {
                    self.other_activity = true;
                }
            }
        }
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_bindings_use_right_ctrl_and_right_shift() {
        let (bindings, warnings) = default_bindings(Some("us"), Some("ru"));
        assert!(warnings.is_empty());
        assert_eq!(bindings[0].key, "RightCtrl");
        assert_eq!(bindings[1].key, "RightShift");
    }

    #[test]
    fn conflicting_bindings_are_rejected() {
        let bindings = vec![
            HotkeyBinding {
                layout_id: "us".into(),
                binding_type: BindingType::SingleClick,
                key: "RightCtrl".into(),
                modifiers: vec![],
                display: String::new(),
                is_custom: false,
            },
            HotkeyBinding {
                layout_id: "ru".into(),
                binding_type: BindingType::SingleClick,
                key: "RightCtrl".into(),
                modifiers: vec![],
                display: String::new(),
                is_custom: false,
            },
        ];
        assert!(validate_unique(&bindings).is_err());
    }

    #[test]
    fn custom_binding_replaces_previous_one_for_same_layout() {
        let mut bindings = vec![HotkeyBinding {
            layout_id: "ru".into(),
            binding_type: BindingType::Combo,
            key: "KeyQ".into(),
            modifiers: vec!["Ctrl".into()],
            display: "Ctrl + KeyQ".into(),
            is_custom: true,
        }];
        upsert_custom_binding(
            &mut bindings,
            HotkeyBinding {
                layout_id: "ru".into(),
                binding_type: BindingType::Combo,
                key: "KeyW".into(),
                modifiers: vec!["Ctrl".into()],
                display: "Ctrl + KeyW".into(),
                is_custom: true,
            },
        )
        .unwrap();
        assert_eq!(bindings.len(), 1);
        assert_eq!(bindings[0].key, "KeyW");
    }

    #[test]
    fn single_click_detector_only_triggers_without_other_activity() {
        let mut detector = SingleClickDetector::new("RightCtrl");
        assert!(!detector.feed(&InputEvent {
            kind: InputEventKind::KeyDown,
            key: "RightCtrl".into()
        }));
        assert!(detector.feed(&InputEvent {
            kind: InputEventKind::KeyUp,
            key: "RightCtrl".into()
        }));

        let mut detector = SingleClickDetector::new("RightCtrl");
        detector.feed(&InputEvent {
            kind: InputEventKind::KeyDown,
            key: "RightCtrl".into(),
        });
        detector.feed(&InputEvent {
            kind: InputEventKind::MouseClick,
            key: String::new(),
        });
        assert!(!detector.feed(&InputEvent {
            kind: InputEventKind::KeyUp,
            key: "RightCtrl".into()
        }));
    }
}
