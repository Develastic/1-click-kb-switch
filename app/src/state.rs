use crate::config::{AppConfig, AppPaths};
use crate::hotkeys::default_bindings;
use crate::layouts::{DEFAULT_LABEL, LayoutInfo, choose_default_pair, effective_label};
use crate::platform::PlatformBackend;
use anyhow::Result;

#[derive(Debug, Clone)]
pub struct AppModel {
    pub paths: AppPaths,
    pub config: AppConfig,
    pub layouts: Vec<LayoutInfo>,
    pub warnings: Vec<String>,
    pub tray_label: String,
    pub show_main_window: bool,
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

        let tray_label = self
            .backend
            .get_active_layout()
            .ok()
            .flatten()
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
        })
    }

    pub fn persist(&self, model: &AppModel) -> Result<()> {
        model.config.save(&model.paths.config_path)
    }

    pub fn switch_layout(&self, model: &mut AppModel, layout_id: &str) -> Result<()> {
        self.backend.switch_layout(layout_id)?;
        if let Some(layout) = model
            .config
            .layouts
            .iter()
            .find(|item| item.id == layout_id)
        {
            model.tray_label = effective_label(layout);
        }
        Ok(())
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
}
