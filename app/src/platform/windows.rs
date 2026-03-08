#![cfg(target_os = "windows")]

use crate::layouts::LayoutInfo;
use crate::platform::{PlatformBackend, PlatformWarning};
use anyhow::{Result, bail};

#[derive(Debug, Default)]
pub struct WindowsBackend;

impl PlatformBackend for WindowsBackend {
    fn list_layouts(&self) -> Result<Vec<LayoutInfo>> {
        bail!("Windows layout enumeration is not implemented yet")
    }

    fn get_active_layout(&self) -> Result<Option<String>> {
        bail!("Windows active layout query is not implemented yet")
    }

    fn switch_layout(&self, _layout_id: &str) -> Result<()> {
        bail!("Windows layout switching is not implemented yet")
    }

    fn platform_warnings(&self) -> Vec<PlatformWarning> {
        vec![
            PlatformWarning {
                message:
                    "Windows backend is a native-first scaffold; layout APIs are not wired yet."
                        .to_string(),
            },
            PlatformWarning {
                message: "Single-click low-level hooks are not implemented yet on Windows."
                    .to_string(),
            },
        ]
    }
}
