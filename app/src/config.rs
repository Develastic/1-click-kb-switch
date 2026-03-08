use crate::hotkeys::{HotkeyBinding, validate_unique};
use crate::layouts::LayoutInfo;
use anyhow::{Context, Result};
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

const DEFAULTS_JSON: &str = include_str!("../assets/config.json.defaults");

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AppConfig {
    pub play_switch_sound: bool,
    pub start_minimized_after_first_run: bool,
    pub has_completed_first_run: bool,
    pub layouts: Vec<LayoutInfo>,
    pub hotkey_bindings: Vec<HotkeyBinding>,
}

#[derive(Debug, Clone)]
pub struct AppPaths {
    pub config_dir: PathBuf,
    pub config_path: PathBuf,
}

impl AppPaths {
    pub fn detect() -> Result<Self> {
        let dirs = ProjectDirs::from("com", "mykola", "one-click-kb-switch")
            .context("cannot resolve OS-specific config directory")?;
        let config_dir = dirs.config_dir().to_path_buf();
        Ok(Self {
            config_path: config_dir.join("config.json"),
            config_dir,
        })
    }
}

impl AppConfig {
    pub fn defaults() -> Result<Self> {
        serde_json::from_str(DEFAULTS_JSON).context("cannot parse embedded default config")
    }

    pub fn load(path: &Path) -> Result<Self> {
        let raw = fs::read_to_string(path)
            .with_context(|| format!("cannot read config: {}", path.display()))?;
        let config: Self = serde_json::from_str(&raw).context("cannot parse config json")?;
        config.validate()?;
        Ok(config)
    }

    pub fn save(&self, path: &Path) -> Result<()> {
        self.validate()?;
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .with_context(|| format!("cannot create config directory: {}", parent.display()))?;
        }
        let payload = serde_json::to_string_pretty(self).context("cannot encode config json")?;
        fs::write(path, payload)
            .with_context(|| format!("cannot write config: {}", path.display()))?;
        Ok(())
    }

    pub fn create_from_defaults(path: &Path) -> Result<Self> {
        let config = Self::defaults()?;
        config.save(path)?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<()> {
        validate_unique(&self.hotkey_bindings).context("hotkey validation failed")?;
        for layout in &self.layouts {
            anyhow::ensure!(!layout.id.trim().is_empty(), "layout id is required");
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_can_be_created() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("config.json");
        let config = AppConfig::create_from_defaults(&path).unwrap();
        assert!(config.play_switch_sound);
        assert!(path.exists());
    }

    #[test]
    fn conflicting_bindings_are_rejected_on_load() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("config.json");
        fs::write(
            &path,
            r#"{
  "play_switch_sound": true,
  "start_minimized_after_first_run": true,
  "has_completed_first_run": true,
  "layouts": [{"id":"us","display_name":"English US","is_english":true,"auto_label":"EU","label_override":""}],
  "hotkey_bindings": [
    {"layout_id":"us","binding_type":"single_click","key":"RightCtrl","modifiers":[],"display":"RightCtrl","is_custom":false},
    {"layout_id":"ru","binding_type":"single_click","key":"RightCtrl","modifiers":[],"display":"RightCtrl","is_custom":false}
  ]
}"#,
        )
        .unwrap();
        assert!(AppConfig::load(&path).is_err());
    }
}
