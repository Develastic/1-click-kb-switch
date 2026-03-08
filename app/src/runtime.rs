#[derive(Debug, Clone, Default)]
pub struct AppRuntimeState {
    pub active_layout_id: Option<String>,
    pub registered_hotkeys: Vec<String>,
    pub hook_status: HookStatus,
    pub tray_status: TrayStatus,
    pub last_switch_error: Option<String>,
    pub pending_capture_layout_id: Option<String>,
}

#[derive(Debug, Clone, Default)]
pub enum HookStatus {
    #[default]
    Inactive,
    Active,
    Failed(String),
}

#[derive(Debug, Clone, Default)]
pub enum TrayStatus {
    #[default]
    Inactive,
    Active,
    Failed(String),
}
