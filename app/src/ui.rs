use crate::state::AppModel;
use crate::tray::{TrayCommand, TrayController};
use anyhow::{Context, Result};
use tao::dpi::LogicalSize;
use tao::event::{Event, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoop, EventLoopBuilder};
use tao::window::{Window, WindowBuilder};

pub fn run(model: AppModel) -> Result<()> {
    let event_loop = EventLoopBuilder::<TrayCommand>::with_user_event().build();
    let proxy = event_loop.create_proxy();
    let tray = TrayController::build(proxy, &model.tray_label)?;
    let window = build_window(&event_loop, &model)?;
    window.set_visible(model.show_main_window);
    update_window_title(&window, &model);

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;
        match event {
            Event::UserEvent(TrayCommand::ShowWindow) => {
                window.set_visible(true);
                window.set_focus();
            }
            Event::UserEvent(TrayCommand::Exit) => {
                *control_flow = ControlFlow::Exit;
            }
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                ..
            } => {
                window.set_visible(false);
            }
            Event::WindowEvent {
                event: WindowEvent::Focused(true),
                ..
            } => {
                let _ = tray.update_label(&model.tray_label);
            }
            _ => {}
        }
    })
}

fn build_window(event_loop: &EventLoop<TrayCommand>, model: &AppModel) -> Result<Window> {
    WindowBuilder::new()
        .with_title(window_title(model))
        .with_inner_size(LogicalSize::new(900.0, 620.0))
        .build(event_loop)
        .context("failed to create tao window")
}

fn update_window_title(window: &Window, model: &AppModel) {
    window.set_title(&window_title(model));
}

fn window_title(model: &AppModel) -> String {
    let layouts = model
        .layouts
        .iter()
        .map(|layout| {
            format!(
                "{} [{}]",
                layout.display_name,
                if layout.label_override.is_empty() {
                    &layout.auto_label
                } else {
                    &layout.label_override
                }
            )
        })
        .collect::<Vec<_>>()
        .join(" | ");
    let warnings = if model.warnings.is_empty() {
        "No warnings".to_string()
    } else {
        format!("Warnings: {}", model.warnings.join("; "))
    };
    format!("One Click KB Switch — layouts: {} — {}", layouts, warnings)
}
