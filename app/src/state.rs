use crate::config::{AppConfig, AppPaths};
use crate::hotkeys::{
    BindingType, HotkeyBinding, clear_custom_binding, default_bindings, display_for_combo,
    upsert_custom_binding,
};
use crate::layouts::{DEFAULT_LABEL, LayoutInfo, choose_default_pair, effective_label};
use crate::platform::PlatformBackend;
use crate::runtime::{AppRuntimeState, HookStatus, TrayStatus};
use crate::sound;
use anyhow::Result;

#[derive(Debug, Clone)]
pub struct AppModel {
    pub paths: AppPaths,
    pub config: AppConfig,
    pub layouts: Vec<LayoutInfo>,
    pub warnings: Vec<String>,
    pub tray_label: String,
    pub show_main_window: bool,
    pub runtime: AppRuntimeState,
}

pub struct AppService {
    backend: Box<dyn PlatformBackend>,
}

impl AppService {
    pub fn new(backend: Box<dyn PlatformBackend>) -> Self {
        Self { backend }
    }

    pub fn bootstrap(&self, paths: AppPaths) -> Result<AppModel> {
        let (mut config, first_run) = if paths.config_path.exists() {
            (AppConfig::load(&paths.config_path)?, false)
        } else {
            (AppConfig::create_from_defaults(&paths.config_path)?, true)
        };

        let detected_layouts = self.backend.list_layouts().unwrap_or_default();
        if !detected_layouts.is_empty() {
            config.layouts = detected_layouts;
        }

        if config.hotkey_bindings.is_empty() {
            let (english, alternate) = choose_default_pair(&config.layouts);
            let (bindings, _) = default_bindings(english.as_deref(), alternate.as_deref());
            config.hotkey_bindings = bindings;
        }

        config.has_completed_first_run = true;
        config.save(&paths.config_path)?;

        let active_layout_id = self.backend.get_active_layout().ok().flatten();
        let tray_label = active_layout_id
            .as_deref()
            .and_then(|active_id| {
                config
                    .layouts
                    .iter()
                    .find(|layout| layout.id == active_id)
                    .map(effective_label)
            })
            .or_else(|| config.layouts.first().map(effective_label))
            .unwrap_or_else(|| DEFAULT_LABEL.to_string());

        let mut warnings = self.collect_warnings(&config);
        warnings.extend(
            self.backend
                .platform_warnings()
                .into_iter()
                .map(|item| item.message),
        );
        let show_main_window = first_run || !config.start_minimized_after_first_run;

        Ok(AppModel {
            paths,
            layouts: config.layouts.clone(),
            config,
            warnings,
            tray_label,
            show_main_window,
            runtime: AppRuntimeState {
                active_layout_id,
                hook_status: HookStatus::Inactive,
                tray_status: TrayStatus::Inactive,
                ..AppRuntimeState::default()
            },
        })
    }

    pub fn persist(&self, model: &AppModel) -> Result<()> {
        model.config.save(&model.paths.config_path)
    }

    pub fn switch_layout(&self, model: &mut AppModel, layout_id: &str) -> Result<()> {
        match self.backend.switch_layout(layout_id) {
            Ok(()) => {
                model.runtime.active_layout_id = Some(layout_id.to_string());
                model.runtime.last_switch_error = None;
                if let Some(layout) = model
                    .config
                    .layouts
                    .iter()
                    .find(|item| item.id == layout_id)
                {
                    model.tray_label = effective_label(layout);
                }
                sound::play_switch(model.config.play_switch_sound)?;
                Ok(())
            }
            Err(err) => {
                model.runtime.last_switch_error = Some(err.to_string());
                Err(err)
            }
        }
    }

    pub fn refresh_active_layout(&self, model: &mut AppModel) -> Result<bool> {
        let active_layout_id = self.backend.get_active_layout()?;
        let changed = active_layout_id != model.runtime.active_layout_id;
        model.runtime.active_layout_id = active_layout_id.clone();
        if let Some(active_id) = active_layout_id {
            if let Some(layout) = model
                .config
                .layouts
                .iter()
                .find(|item| item.id == active_id)
            {
                model.tray_label = effective_label(layout);
            }
        }
        Ok(changed)
    }

    pub fn set_play_switch_sound(&self, model: &mut AppModel, enabled: bool) {
        model.config.play_switch_sound = enabled;
    }

    pub fn set_start_minimized_after_first_run(&self, model: &mut AppModel, enabled: bool) {
        model.config.start_minimized_after_first_run = enabled;
    }

    pub fn upsert_custom_combo(
        &self,
        model: &mut AppModel,
        layout_id: &str,
        key: String,
        modifiers: Vec<String>,
    ) -> Result<()> {
        let binding = HotkeyBinding {
            layout_id: layout_id.to_string(),
            binding_type: BindingType::Combo,
            display: display_for_combo(&modifiers, &key),
            key,
            modifiers,
            is_custom: true,
        };
        upsert_custom_binding(&mut model.config.hotkey_bindings, binding)?;
        model.runtime.pending_capture_layout_id = None;
        Ok(())
    }

    pub fn clear_custom_binding(&self, model: &mut AppModel, layout_id: &str) -> bool {
        clear_custom_binding(&mut model.config.hotkey_bindings, layout_id)
    }

    pub fn set_registered_hotkeys(&self, model: &mut AppModel, hotkeys: Vec<String>) {
        model.runtime.registered_hotkeys = hotkeys;
    }

    fn collect_warnings(&self, config: &AppConfig) -> Vec<String> {
        let mut warnings = Vec::new();
        let (english, alternate) = choose_default_pair(&config.layouts);
        if english.is_none() {
            warnings.push("English layout was not detected.".to_string());
        }
        if alternate.is_none() {
            warnings.push("Alternative non-English layout was not detected.".to_string());
        }
        warnings
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::layouts::build_info;
    use crate::platform::{PlatformBackend, PlatformWarning};

    #[derive(Debug)]
    struct FakeBackend {
        layouts: Vec<LayoutInfo>,
        active: Option<String>,
    }

    impl PlatformBackend for FakeBackend {
        fn list_layouts(&self) -> Result<Vec<LayoutInfo>> {
            Ok(self.layouts.clone())
        }

        fn get_active_layout(&self) -> Result<Option<String>> {
            Ok(self.active.clone())
        }

        fn switch_layout(&self, _layout_id: &str) -> Result<()> {
            Ok(())
        }

        fn platform_warnings(&self) -> Vec<PlatformWarning> {
            Vec::new()
        }
    }

    #[test]
    fn first_run_creates_config_and_shows_window() {
        let temp = tempfile::tempdir().unwrap();
        let paths = AppPaths {
            config_dir: temp.path().to_path_buf(),
            config_path: temp.path().join("config.json"),
        };
        let service = AppService::new(Box::new(FakeBackend {
            layouts: vec![
                build_info("us", "English US", ""),
                build_info("ru", "Russian", ""),
            ],
            active: Some("ru".to_string()),
        }));

        let model = service.bootstrap(paths).unwrap();
        assert!(model.show_main_window);
        assert_eq!(model.tray_label, "RU");
        assert_eq!(model.config.hotkey_bindings.len(), 2);
        assert_eq!(model.runtime.active_layout_id.as_deref(), Some("ru"));
    }

    #[test]
    fn switch_layout_updates_tray_label() {
        let temp = tempfile::tempdir().unwrap();
        let paths = AppPaths {
            config_dir: temp.path().to_path_buf(),
            config_path: temp.path().join("config.json"),
        };
        let service = AppService::new(Box::new(FakeBackend {
            layouts: vec![build_info("us", "English US", "")],
            active: Some("us".to_string()),
        }));
        let mut model = service.bootstrap(paths).unwrap();
        model.config.layouts.push(build_info("fr", "French", "FR"));
        service.switch_layout(&mut model, "fr").unwrap();
        assert_eq!(model.tray_label, "FR");
    }

    #[test]
    fn custom_binding_is_saved_in_model() {
        let temp = tempfile::tempdir().unwrap();
        let paths = AppPaths {
            config_dir: temp.path().to_path_buf(),
            config_path: temp.path().join("config.json"),
        };
        let service = AppService::new(Box::new(FakeBackend {
            layouts: vec![build_info("us", "English US", "")],
            active: Some("us".to_string()),
        }));
        let mut model = service.bootstrap(paths).unwrap();
        service
            .upsert_custom_combo(&mut model, "us", "KeyQ".into(), vec!["Ctrl".into()])
            .unwrap();
        assert!(
            model
                .config
                .hotkey_bindings
                .iter()
                .any(|item| item.is_custom)
        );
    }
}
