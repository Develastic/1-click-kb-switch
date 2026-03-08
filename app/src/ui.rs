use crate::hotkeys::{
    BindingType, HotkeyBinding, InputEvent, InputEventKind, SingleClickDetector,
    binding_to_global_hotkey, custom_bindings,
};
use crate::runtime::TrayStatus;
use crate::state::{AppModel, AppService};
use crate::tray::{TrayCommand, TrayController};
use anyhow::{Context, Result};
use global_hotkey::{GlobalHotKeyEvent, GlobalHotKeyManager, hotkey::HotKey};
use std::collections::HashMap;
use std::time::{Duration, Instant};
use tao::dpi::LogicalSize;
use tao::event::{Event, StartCause, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoop, EventLoopBuilder};
use tao::keyboard::{KeyCode, ModifiersState};
use tao::window::{Window, WindowBuilder};

#[cfg(target_os = "windows")]
use crate::platform::windows_hooks::WindowsHookRuntime;
#[cfg(target_os = "windows")]
use crate::runtime::HookStatus;

struct ComboHotkeyRegistry {
    _manager: GlobalHotKeyManager,
    bindings_by_id: HashMap<u32, String>,
    labels: Vec<String>,
}

impl ComboHotkeyRegistry {
    fn register(bindings: &[HotkeyBinding]) -> Result<Self> {
        let manager =
            GlobalHotKeyManager::new().context("failed to create global hotkey manager")?;
        let mut bindings_by_id = HashMap::new();
        let mut labels = Vec::new();
        let custom = custom_bindings(bindings);
        let hotkeys = custom
            .iter()
            .filter(|binding| matches!(binding.binding_type, BindingType::Combo))
            .map(binding_to_global_hotkey)
            .collect::<Result<Vec<HotKey>>>()?;
        manager
            .register_all(&hotkeys)
            .context("failed to register global hotkeys")?;
        for (binding, hotkey) in custom.iter().zip(hotkeys.iter()) {
            bindings_by_id.insert(hotkey.id(), binding.layout_id.clone());
            labels.push(binding.display.clone());
        }
        Ok(Self {
            _manager: manager,
            bindings_by_id,
            labels,
        })
    }
}

pub fn run(service: AppService, mut model: AppModel) -> Result<()> {
    let event_loop = EventLoopBuilder::<TrayCommand>::with_user_event().build();
    let proxy = event_loop.create_proxy();
    let mut tray = TrayController::build(proxy.clone(), &model)?;
    model.runtime.tray_status = TrayStatus::Active;
    let window = build_window(&event_loop, &model)?;
    window.set_visible(model.show_main_window);
    update_window_title(&window, &model);

    #[cfg(target_os = "windows")]
    let (mut hook_runtime, input_rx) = match WindowsHookRuntime::start() {
        Ok(result) => {
            model.runtime.hook_status = HookStatus::Active;
            Some(result)
        }
        Err(err) => {
            model.runtime.hook_status = HookStatus::Failed(err.to_string());
            None
        }
    }
    .map_or((None, None), |(runtime, receiver)| {
        (Some(runtime), Some(receiver))
    });

    #[cfg(not(target_os = "windows"))]
    let (_hook_runtime, input_rx): (Option<()>, Option<std::sync::mpsc::Receiver<InputEvent>>) =
        (None, None);

    let mut combo_registry = register_combo_registry(&service, &mut model);
    let mut ctrl_detector = SingleClickDetector::new("RightCtrl");
    let mut shift_detector = SingleClickDetector::new("RightShift");
    let mut current_modifiers = ModifiersState::empty();
    let mut last_active_refresh = Instant::now();

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::WaitUntil(Instant::now() + Duration::from_millis(250));
        match event {
            Event::NewEvents(StartCause::ResumeTimeReached { .. }) | Event::MainEventsCleared => {
                if let Some(receiver) = input_rx.as_ref() {
                    while let Ok(input_event) = receiver.try_recv() {
                        handle_input_event(
                            &service,
                            &mut model,
                            &mut ctrl_detector,
                            &mut shift_detector,
                            input_event,
                            &mut tray,
                            &window,
                            &proxy,
                            &mut combo_registry,
                        );
                    }
                }

                while let Ok(event) = GlobalHotKeyEvent::receiver().try_recv() {
                    if let Some(registry) = combo_registry.as_ref() {
                        if let Some(layout_id) = registry.bindings_by_id.get(&event.id()) {
                            if event.state().is_pressed() {
                                if let Err(err) = service.switch_layout(&mut model, layout_id) {
                                    model.runtime.last_switch_error = Some(err.to_string());
                                } else {
                                    let _ = service.persist(&model);
                                }
                                rebuild_tray(&mut tray, &proxy, &model);
                                update_window_title(&window, &model);
                            }
                        }
                    }
                }

                if last_active_refresh.elapsed() >= Duration::from_millis(400) {
                    if service.refresh_active_layout(&mut model).unwrap_or(false) {
                        rebuild_tray(&mut tray, &proxy, &model);
                        update_window_title(&window, &model);
                    }
                    last_active_refresh = Instant::now();
                }
            }
            Event::UserEvent(command) => {
                handle_tray_command(
                    command,
                    &service,
                    &mut model,
                    &window,
                    control_flow,
                    &proxy,
                    &mut tray,
                    &mut combo_registry,
                );
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
                let _ = service.refresh_active_layout(&mut model);
                rebuild_tray(&mut tray, &proxy, &model);
                update_window_title(&window, &model);
            }
            Event::WindowEvent {
                event: WindowEvent::ModifiersChanged(modifiers),
                ..
            } => {
                current_modifiers = modifiers;
            }
            Event::WindowEvent {
                event:
                    WindowEvent::KeyboardInput {
                        event,
                        is_synthetic,
                        ..
                    },
                ..
            } => {
                if !is_synthetic {
                    handle_capture_key(
                        &service,
                        &mut model,
                        &event.physical_key,
                        event.state.is_pressed(),
                        current_modifiers,
                        &window,
                        &proxy,
                        &mut tray,
                        &mut combo_registry,
                    );
                }
            }
            _ => {}
        }

        if matches!(*control_flow, ControlFlow::Exit) {
            #[cfg(target_os = "windows")]
            if let Some(runtime) = hook_runtime.as_mut() {
                runtime.stop();
            }
        }
    })
}

fn register_combo_registry(
    service: &AppService,
    model: &mut AppModel,
) -> Option<ComboHotkeyRegistry> {
    match ComboHotkeyRegistry::register(&model.config.hotkey_bindings) {
        Ok(registry) => {
            service.set_registered_hotkeys(model, registry.labels.clone());
            Some(registry)
        }
        Err(err) => {
            model.runtime.last_switch_error = Some(format!("Hotkey registration failed: {err}"));
            service.set_registered_hotkeys(model, Vec::new());
            None
        }
    }
}

fn handle_input_event(
    service: &AppService,
    model: &mut AppModel,
    ctrl_detector: &mut SingleClickDetector,
    shift_detector: &mut SingleClickDetector,
    input_event: InputEvent,
    tray: &mut TrayController,
    window: &Window,
    proxy: &tao::event_loop::EventLoopProxy<TrayCommand>,
    combo_registry: &mut Option<ComboHotkeyRegistry>,
) {
    let english_layout = model
        .config
        .hotkey_bindings
        .iter()
        .find(|item| {
            matches!(item.binding_type, BindingType::SingleClick) && item.key == "RightCtrl"
        })
        .map(|item| item.layout_id.clone());
    let alternate_layout = model
        .config
        .hotkey_bindings
        .iter()
        .find(|item| {
            matches!(item.binding_type, BindingType::SingleClick) && item.key == "RightShift"
        })
        .map(|item| item.layout_id.clone());

    if ctrl_detector.feed(&input_event) {
        if let Some(layout_id) = english_layout {
            if service.switch_layout(model, &layout_id).is_ok() {
                let _ = service.persist(model);
                rebuild_tray(tray, proxy, model);
                update_window_title(window, model);
            }
        }
    }

    if shift_detector.feed(&input_event) {
        if let Some(layout_id) = alternate_layout {
            if service.switch_layout(model, &layout_id).is_ok() {
                let _ = service.persist(model);
                rebuild_tray(tray, proxy, model);
                update_window_title(window, model);
            }
        }
    }

    if matches!(input_event.kind, InputEventKind::MouseClick)
        && model.runtime.pending_capture_layout_id.is_some()
    {
        model.runtime.pending_capture_layout_id = None;
        update_window_title(window, model);
    }

    if combo_registry.is_none() {
        *combo_registry = register_combo_registry(service, model);
    }
}

fn handle_tray_command(
    command: TrayCommand,
    service: &AppService,
    model: &mut AppModel,
    window: &Window,
    control_flow: &mut ControlFlow,
    proxy: &tao::event_loop::EventLoopProxy<TrayCommand>,
    tray: &mut TrayController,
    combo_registry: &mut Option<ComboHotkeyRegistry>,
) {
    match command {
        TrayCommand::ShowWindow => {
            window.set_visible(true);
            window.set_focus();
        }
        TrayCommand::Exit => {
            *control_flow = ControlFlow::Exit;
        }
        TrayCommand::SwitchLayout(layout_id) => {
            if let Err(err) = service.switch_layout(model, &layout_id) {
                model.runtime.last_switch_error = Some(err.to_string());
            } else {
                let _ = service.persist(model);
            }
            rebuild_tray(tray, proxy, model);
            update_window_title(window, model);
        }
        TrayCommand::ToggleSound => {
            service.set_play_switch_sound(model, !model.config.play_switch_sound);
            let _ = service.persist(model);
            rebuild_tray(tray, proxy, model);
            update_window_title(window, model);
        }
        TrayCommand::ToggleStartMinimized => {
            service.set_start_minimized_after_first_run(
                model,
                !model.config.start_minimized_after_first_run,
            );
            let _ = service.persist(model);
            rebuild_tray(tray, proxy, model);
            update_window_title(window, model);
        }
        TrayCommand::BeginCustomCapture(layout_id) => {
            model.runtime.pending_capture_layout_id = Some(layout_id);
            window.set_visible(true);
            window.set_focus();
            update_window_title(window, model);
        }
        TrayCommand::ClearCustomBinding(layout_id) => {
            if service.clear_custom_binding(model, &layout_id) {
                let _ = service.persist(model);
                *combo_registry = register_combo_registry(service, model);
                rebuild_tray(tray, proxy, model);
                update_window_title(window, model);
            }
        }
    }
}

fn handle_capture_key(
    service: &AppService,
    model: &mut AppModel,
    physical_key: &KeyCode,
    pressed: bool,
    modifiers: ModifiersState,
    window: &Window,
    proxy: &tao::event_loop::EventLoopProxy<TrayCommand>,
    tray: &mut TrayController,
    combo_registry: &mut Option<ComboHotkeyRegistry>,
) {
    if !pressed {
        return;
    }
    let Some(layout_id) = model.runtime.pending_capture_layout_id.clone() else {
        return;
    };

    let key_name = format!("{:?}", physical_key);
    if is_modifier_key(&key_name) {
        return;
    }
    let modifiers = modifiers_to_names(modifiers);
    if let Err(err) = service.upsert_custom_combo(model, &layout_id, key_name.clone(), modifiers) {
        model.runtime.last_switch_error = Some(err.to_string());
    } else {
        let _ = service.persist(model);
        *combo_registry = register_combo_registry(service, model);
        rebuild_tray(tray, proxy, model);
    }
    update_window_title(window, model);
}

fn build_window(event_loop: &EventLoop<TrayCommand>, model: &AppModel) -> Result<Window> {
    WindowBuilder::new()
        .with_title(window_title(model))
        .with_inner_size(LogicalSize::new(960.0, 640.0))
        .build(event_loop)
        .context("failed to create tao window")
}

fn rebuild_tray(
    tray: &mut TrayController,
    proxy: &tao::event_loop::EventLoopProxy<TrayCommand>,
    model: &AppModel,
) {
    if let Ok(new_tray) = TrayController::build(proxy.clone(), model) {
        *tray = new_tray;
    }
}

fn update_window_title(window: &Window, model: &AppModel) {
    window.set_title(&window_title(model));
}

fn window_title(model: &AppModel) -> String {
    let layouts = model
        .layouts
        .iter()
        .map(|layout| {
            let marker = if model.runtime.active_layout_id.as_deref() == Some(layout.id.as_str()) {
                "*"
            } else {
                " "
            };
            format!(
                "{marker}{} [{}]",
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
    let runtime = format!(
        "hooks={:?}; tray={:?}; combos={}",
        model.runtime.hook_status,
        model.runtime.tray_status,
        if model.runtime.registered_hotkeys.is_empty() {
            "none".to_string()
        } else {
            model.runtime.registered_hotkeys.join(", ")
        }
    );
    let capture = model
        .runtime
        .pending_capture_layout_id
        .as_deref()
        .map(|layout_id| format!("Capture mode for {layout_id}: press a key or combo"))
        .unwrap_or_else(|| {
            "Use tray menu to switch layouts and capture custom hotkeys".to_string()
        });
    let warning = model
        .runtime
        .last_switch_error
        .clone()
        .or_else(|| model.warnings.first().cloned())
        .unwrap_or_else(|| "No warnings".to_string());
    format!(
        "One Click KB Switch — {} — {} — {} — {}",
        layouts, runtime, capture, warning
    )
}

fn modifiers_to_names(modifiers: ModifiersState) -> Vec<String> {
    let mut names = Vec::new();
    if modifiers.control_key() {
        names.push("Ctrl".to_string());
    }
    if modifiers.alt_key() {
        names.push("Alt".to_string());
    }
    if modifiers.shift_key() {
        names.push("Shift".to_string());
    }
    if modifiers.super_key() {
        names.push("Meta".to_string());
    }
    names
}

fn is_modifier_key(key_name: &str) -> bool {
    matches!(
        key_name,
        "ShiftLeft"
            | "ShiftRight"
            | "ControlLeft"
            | "ControlRight"
            | "AltLeft"
            | "AltRight"
            | "SuperLeft"
            | "SuperRight"
    )
}

trait ElementStateExt {
    fn is_pressed(&self) -> bool;
}

impl ElementStateExt for tao::event::ElementState {
    fn is_pressed(&self) -> bool {
        matches!(self, tao::event::ElementState::Pressed)
    }
}

trait HotKeyStateExt {
    fn is_pressed(&self) -> bool;
}

impl HotKeyStateExt for global_hotkey::HotKeyState {
    fn is_pressed(&self) -> bool {
        matches!(self, global_hotkey::HotKeyState::Pressed)
    }
}
