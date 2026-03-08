use crate::layouts::LayoutInfo;
use anyhow::Result;

#[derive(Debug, Clone)]
pub struct PlatformWarning {
    pub message: String,
}

pub trait PlatformBackend {
    fn list_layouts(&self) -> Result<Vec<LayoutInfo>>;
    fn get_active_layout(&self) -> Result<Option<String>>;
    fn switch_layout(&self, layout_id: &str) -> Result<()>;
    fn platform_warnings(&self) -> Vec<PlatformWarning>;
}

#[cfg(target_os = "linux")]
pub mod linux_x11;
#[cfg(target_os = "windows")]
pub mod windows;

pub fn build_backend() -> Box<dyn PlatformBackend> {
    #[cfg(target_os = "linux")]
    {
        Box::new(linux_x11::LinuxX11Backend::default())
    }
    #[cfg(target_os = "windows")]
    {
        Box::new(windows::WindowsBackend::default())
    }
}
