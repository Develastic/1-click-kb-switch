use anyhow::{Context, Result};
use font8x8::{BASIC_FONTS, UnicodeFonts};
use tao::event_loop::EventLoopProxy;
use tray_icon::menu::{Menu, MenuEvent, MenuItem};
use tray_icon::{Icon, TrayIcon, TrayIconBuilder, TrayIconEvent};

#[derive(Debug, Clone)]
pub enum TrayCommand {
    ShowWindow,
    Exit,
}

pub struct TrayController {
    pub tray_icon: TrayIcon,
    pub show_item: MenuItem,
    pub exit_item: MenuItem,
}

impl TrayController {
    pub fn build(proxy: EventLoopProxy<TrayCommand>, label: &str) -> Result<Self> {
        let menu = Menu::new();
        let show_item = MenuItem::new("Show main window", true, None);
        let exit_item = MenuItem::new("Exit", true, None);
        let show_id = show_item.id().clone();
        let exit_id = exit_item.id().clone();

        TrayIconEvent::set_event_handler(Some({
            let proxy = proxy.clone();
            move |_event| {
                let _ = proxy.send_event(TrayCommand::ShowWindow);
            }
        }));
        MenuEvent::set_event_handler(Some(move |event: MenuEvent| {
            let command = if event.id == show_id {
                TrayCommand::ShowWindow
            } else if event.id == exit_id {
                TrayCommand::Exit
            } else {
                return;
            };
            let _ = proxy.send_event(command);
        }));

        menu.append_items(&[&show_item, &exit_item])?;

        let icon = generate_text_icon(label)?;
        let tray_icon = TrayIconBuilder::new()
            .with_menu(Box::new(menu))
            .with_tooltip(&format!("One Click KB Switch ({label})"))
            .with_icon(icon)
            .build()
            .context("failed to build tray icon")?;

        Ok(Self {
            tray_icon,
            show_item,
            exit_item,
        })
    }

    pub fn update_label(&self, label: &str) -> Result<()> {
        self.tray_icon
            .set_icon(Some(generate_text_icon(label)?))
            .context("failed to update tray icon")?;
        self.tray_icon
            .set_tooltip(Some(format!("One Click KB Switch ({label})")))
            .context("failed to update tray tooltip")?;
        Ok(())
    }
}

pub fn generate_text_icon(label: &str) -> Result<Icon> {
    let label = normalize_label(label);
    let width = 64;
    let height = 64;
    let mut rgba = vec![0u8; width * height * 4];
    for pixel in rgba.chunks_exact_mut(4) {
        pixel.copy_from_slice(&[18, 97, 160, 255]);
    }

    for (index, ch) in label.chars().take(2).enumerate() {
        let glyph = BASIC_FONTS
            .get(ch)
            .or_else(|| BASIC_FONTS.get('K'))
            .context("font glyph not available")?;
        let x_offset = 8 + index * 24;
        let y_offset = 16;
        for (row, bits) in glyph.iter().enumerate() {
            for col in 0..8 {
                let mask = 1 << col;
                if bits & mask == 0 {
                    continue;
                }
                for dy in 0..4 {
                    for dx in 0..3 {
                        let x = x_offset + (7 - col) * 3 + dx;
                        let y = y_offset + row * 4 + dy;
                        let idx = (y * width + x) * 4;
                        rgba[idx..idx + 4].copy_from_slice(&[255, 255, 255, 255]);
                    }
                }
            }
        }
    }

    Icon::from_rgba(rgba, width as u32, height as u32)
        .context("failed to create tray icon from rgba")
}

fn normalize_label(label: &str) -> String {
    let trimmed = label.trim();
    if trimmed.is_empty() {
        return "KB".to_string();
    }
    trimmed.chars().take(2).collect::<String>().to_uppercase()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn icon_generation_works_for_default_label() {
        generate_text_icon("KB").unwrap();
    }
}
