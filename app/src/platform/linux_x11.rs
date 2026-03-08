#![cfg(target_os = "linux")]

use crate::layouts::{LayoutInfo, build_info};
use crate::platform::{PlatformBackend, PlatformWarning};
use anyhow::{Context, Result, anyhow};
use std::process::Command;

#[derive(Debug, Default)]
pub struct LinuxX11Backend;

impl PlatformBackend for LinuxX11Backend {
    fn list_layouts(&self) -> Result<Vec<LayoutInfo>> {
        let output = Command::new("setxkbmap")
            .arg("-query")
            .output()
            .context("setxkbmap is required for Linux X11 layout discovery")?;
        if !output.status.success() {
            return Err(anyhow!(
                "setxkbmap -query failed with status {}",
                output.status
            ));
        }
        Ok(parse_query(&String::from_utf8_lossy(&output.stdout)))
    }

    fn get_active_layout(&self) -> Result<Option<String>> {
        let layouts = self.list_layouts()?;
        Ok(layouts.first().map(|item| item.id.clone()))
    }

    fn switch_layout(&self, layout_id: &str) -> Result<()> {
        let status = Command::new("setxkbmap")
            .arg(layout_id)
            .status()
            .with_context(|| format!("failed to execute setxkbmap for layout {layout_id}"))?;
        if !status.success() {
            return Err(anyhow!(
                "setxkbmap returned non-zero status for layout {layout_id}"
            ));
        }
        Ok(())
    }

    fn platform_warnings(&self) -> Vec<PlatformWarning> {
        vec![
            PlatformWarning {
                message: "Linux v1 supports X11 only. Wayland is not supported.".to_string(),
            },
            PlatformWarning {
                message: "Single-click low-level hooks are not implemented yet on Linux X11."
                    .to_string(),
            },
        ]
    }
}

fn parse_query(raw: &str) -> Vec<LayoutInfo> {
    raw.lines()
        .find_map(|line| line.trim().strip_prefix("layout:"))
        .map(|payload| {
            payload
                .split(',')
                .filter_map(|item| {
                    let name = item.trim();
                    (!name.is_empty()).then(|| build_info(name, name, ""))
                })
                .collect()
        })
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::parse_query;

    #[test]
    fn parses_x11_layout_query() {
        let layouts = parse_query("rules: evdev\nmodel: pc105\nlayout: us,ru,fr\n");
        assert_eq!(layouts.len(), 3);
        assert_eq!(layouts[0].id, "us");
        assert_eq!(layouts[1].id, "ru");
        assert_eq!(layouts[2].id, "fr");
    }
}
