use crate::hotkeys::custom_bindings;
use crate::state::AppModel;
use anyhow::{Context, Result};
use font8x8::{BASIC_FONTS, UnicodeFonts};
use tao::event_loop::EventLoopProxy;
use tray_icon::menu::{
    CheckMenuItem, Menu, MenuEvent, MenuId, MenuItem, PredefinedMenuItem, Submenu,
};
use tray_icon::{Icon, TrayIcon, TrayIconBuilder, TrayIconEvent};

#[derive(Debug, Clone)]
pub enum TrayCommand {
    ShowWindow,
    Exit,
    SwitchLayout(String),
    ToggleSound,
    ToggleStartMinimized,
    BeginCustomCapture(String),
    ClearCustomBinding(String),
}

pub struct TrayController {
    pub tray_icon: TrayIcon,
}

impl TrayController {
    pub fn build(proxy: EventLoopProxy<TrayCommand>, model: &AppModel) -> Result<Self> {
        let menu = Menu::new();

        let show_item =
            MenuItem::with_id(MenuId("show_window".into()), "Show main window", true, None);
        let exit_item = MenuItem::with_id(MenuId("exit".into()), "Exit", true, None);
        let toggle_sound = CheckMenuItem::with_id(
            MenuId("toggle_sound".into()),
            "Play switch sound",
            true,
            model.config.play_switch_sound,
            None,
        );
        let toggle_start_minimized = CheckMenuItem::with_id(
            MenuId("toggle_start_minimized".into()),
            "Start minimized after first run",
            true,
            model.config.start_minimized_after_first_run,
            None,
        );

        let layout_menu = Submenu::new("Switch layout", true);
        for layout in &model.layouts {
            let label = format!(
                "{} [{}]",
                layout.display_name,
                if layout.label_override.is_empty() {
                    &layout.auto_label
                } else {
                    &layout.label_override
                }
            );
            let item =
                MenuItem::with_id(MenuId(format!("switch:{}", layout.id)), label, true, None);
            layout_menu.append(&item)?;
        }

        let capture_menu = Submenu::new("Capture custom hotkey", true);
        let clear_capture_menu = Submenu::new("Clear custom hotkey", true);
        let custom_by_layout = custom_bindings(&model.config.hotkey_bindings)
            .into_iter()
            .map(|item| (item.layout_id, item.display))
            .collect::<std::collections::HashMap<_, _>>();
        for layout in &model.layouts {
            let capture_text = if let Some(display) = custom_by_layout.get(&layout.id) {
                format!("{} ({display})", layout.display_name)
            } else {
                layout.display_name.clone()
            };
            let capture_item = MenuItem::with_id(
                MenuId(format!("capture:{}", layout.id)),
                capture_text,
                true,
                None,
            );
            capture_menu.append(&capture_item)?;
            if custom_by_layout.contains_key(&layout.id) {
                let clear_item = MenuItem::with_id(
                    MenuId(format!("clear_capture:{}", layout.id)),
                    layout.display_name.clone(),
                    true,
                    None,
                );
                clear_capture_menu.append(&clear_item)?;
            }
        }

        let settings_menu = Submenu::new("Settings", true);
        settings_menu.append_items(&[&toggle_sound, &toggle_start_minimized])?;

        menu.append_items(&[
            &show_item,
            &PredefinedMenuItem::separator(),
            &layout_menu,
            &capture_menu,
            &clear_capture_menu,
            &settings_menu,
            &PredefinedMenuItem::separator(),
            &exit_item,
        ])?;

        TrayIconEvent::set_event_handler(Some({
            let proxy = proxy.clone();
            move |_event| {
                let _ = proxy.send_event(TrayCommand::ShowWindow);
            }
        }));
        MenuEvent::set_event_handler(Some(move |event: MenuEvent| {
            if let Some(command) = parse_menu_command(&event.id.0) {
                let _ = proxy.send_event(command);
            }
        }));

        let icon = generate_text_icon(&model.tray_label)?;
        let tray_icon = TrayIconBuilder::new()
            .with_menu(Box::new(menu))
            .with_tooltip(&format!("One Click KB Switch ({})", model.tray_label))
            .with_icon(icon)
            .build()
            .context("failed to build tray icon")?;

        Ok(Self { tray_icon })
    }
}

fn parse_menu_command(id: &str) -> Option<TrayCommand> {
    match id {
        "show_window" => Some(TrayCommand::ShowWindow),
        "exit" => Some(TrayCommand::Exit),
        "toggle_sound" => Some(TrayCommand::ToggleSound),
        "toggle_start_minimized" => Some(TrayCommand::ToggleStartMinimized),
        _ => {
            if let Some(value) = id.strip_prefix("switch:") {
                return Some(TrayCommand::SwitchLayout(value.to_string()));
            }
            if let Some(value) = id.strip_prefix("capture:") {
                return Some(TrayCommand::BeginCustomCapture(value.to_string()));
            }
            if let Some(value) = id.strip_prefix("clear_capture:") {
                return Some(TrayCommand::ClearCustomBinding(value.to_string()));
            }
            None
        }
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

    #[test]
    fn parses_tray_commands() {
        assert!(matches!(
            parse_menu_command("toggle_sound"),
            Some(TrayCommand::ToggleSound)
        ));
        assert!(matches!(
            parse_menu_command("switch:00000409"),
            Some(TrayCommand::SwitchLayout(_))
        ));
    }
}
