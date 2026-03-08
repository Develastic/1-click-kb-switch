#![cfg(target_os = "windows")]

use crate::hotkeys::{InputEvent, InputEventKind};
use anyhow::{Context, Result, anyhow};
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Mutex, OnceLock};
use std::thread::{self, JoinHandle};
use windows::Win32::Foundation::{HINSTANCE, LPARAM, LRESULT, WPARAM};
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::System::Threading::GetCurrentThreadId;
use windows::Win32::UI::Input::KeyboardAndMouse::{
    VK_LCONTROL, VK_LMENU, VK_LSHIFT, VK_LWIN, VK_MENU, VK_RCONTROL, VK_RMENU, VK_RSHIFT, VK_RWIN,
    VK_SHIFT,
};
use windows::Win32::UI::WindowsAndMessaging::{
    CallNextHookEx, DispatchMessageW, GetMessageW, HC_ACTION, HHOOK, KBDLLHOOKSTRUCT, MSG,
    MSLLHOOKSTRUCT, PostThreadMessageW, SetWindowsHookExW, TranslateMessage, UnhookWindowsHookEx,
    WH_KEYBOARD_LL, WH_MOUSE_LL, WM_KEYDOWN, WM_KEYUP, WM_LBUTTONDOWN, WM_MBUTTONDOWN,
    WM_MOUSEWHEEL, WM_QUIT, WM_RBUTTONDOWN, WM_SYSKEYDOWN, WM_SYSKEYUP, WM_XBUTTONDOWN,
};

static INPUT_SENDER: OnceLock<Mutex<Option<Sender<InputEvent>>>> = OnceLock::new();

pub struct WindowsHookRuntime {
    thread_id: u32,
    handle: Option<JoinHandle<()>>,
}

impl WindowsHookRuntime {
    pub fn start() -> Result<(Self, Receiver<InputEvent>)> {
        let (ready_tx, ready_rx) = mpsc::channel();
        let (input_tx, input_rx) = mpsc::channel();
        let handle = thread::Builder::new()
            .name("kb-switch-win-hooks".to_string())
            .spawn(move || {
                let sender = INPUT_SENDER.get_or_init(|| Mutex::new(None));
                *sender.lock().expect("sender mutex poisoned") = Some(input_tx);

                let module = unsafe { GetModuleHandleW(None) }
                    .map(HINSTANCE::from)
                    .unwrap_or_default();
                let keyboard_hook = unsafe {
                    SetWindowsHookExW(WH_KEYBOARD_LL, Some(keyboard_hook_proc), Some(module), 0)
                };
                let mouse_hook = unsafe {
                    SetWindowsHookExW(WH_MOUSE_LL, Some(mouse_hook_proc), Some(module), 0)
                };
                let thread_id = unsafe { GetCurrentThreadId() };
                let init_result = match (keyboard_hook, mouse_hook) {
                    (Ok(keyboard_hook), Ok(mouse_hook)) => {
                        let _ = ready_tx.send(Ok(thread_id));
                        run_message_loop(sender, keyboard_hook, mouse_hook);
                        return;
                    }
                    _ => Err(anyhow!("failed to register low-level Windows hooks")),
                };
                let _ = ready_tx.send(init_result);
                *sender.lock().expect("sender mutex poisoned") = None;
            })
            .context("failed to start Windows hook thread")?;

        let thread_id = ready_rx
            .recv()
            .context("failed to receive Windows hook initialization status")??;

        Ok((
            Self {
                thread_id,
                handle: Some(handle),
            },
            input_rx,
        ))
    }

    pub fn stop(&mut self) {
        unsafe {
            let _ = PostThreadMessageW(self.thread_id, WM_QUIT, WPARAM(0), LPARAM(0));
        }
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}

impl Drop for WindowsHookRuntime {
    fn drop(&mut self) {
        self.stop();
    }
}

fn run_message_loop(
    sender: &Mutex<Option<Sender<InputEvent>>>,
    keyboard_hook: HHOOK,
    mouse_hook: HHOOK,
) {
    let mut message = MSG::default();
    while unsafe { GetMessageW(&mut message, None, 0, 0) }.into() {
        unsafe {
            let _ = TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    }

    unsafe {
        let _ = UnhookWindowsHookEx(keyboard_hook);
        let _ = UnhookWindowsHookEx(mouse_hook);
    }
    *sender.lock().expect("sender mutex poisoned") = None;
}

unsafe extern "system" fn keyboard_hook_proc(code: i32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    if code == HC_ACTION as i32 {
        let info = unsafe { *(lparam.0 as *const KBDLLHOOKSTRUCT) };
        let kind = match wparam.0 as u32 {
            WM_KEYDOWN | WM_SYSKEYDOWN => Some(InputEventKind::KeyDown),
            WM_KEYUP | WM_SYSKEYUP => Some(InputEventKind::KeyUp),
            _ => None,
        };
        if let Some(kind) = kind {
            send_input(InputEvent {
                kind,
                key: map_vk_code(info.vkCode),
            });
        }
    }

    unsafe { CallNextHookEx(None, code, wparam, lparam) }
}

unsafe extern "system" fn mouse_hook_proc(code: i32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    let _ = lparam.0 as *const MSLLHOOKSTRUCT;
    if code == HC_ACTION as i32 {
        match wparam.0 as u32 {
            WM_LBUTTONDOWN | WM_RBUTTONDOWN | WM_MBUTTONDOWN | WM_XBUTTONDOWN | WM_MOUSEWHEEL => {
                send_input(InputEvent {
                    kind: InputEventKind::MouseClick,
                    key: "Mouse".to_string(),
                });
            }
            _ => {}
        }
    }

    unsafe { CallNextHookEx(None, code, wparam, lparam) }
}

fn send_input(event: InputEvent) {
    if let Some(sender) = INPUT_SENDER.get() {
        if let Some(channel) = sender.lock().expect("sender mutex poisoned").as_ref() {
            let _ = channel.send(event);
        }
    }
}

fn map_vk_code(vk_code: u32) -> String {
    match vk_code {
        value if value == VK_RCONTROL.0 as u32 => "RightCtrl".to_string(),
        value if value == VK_RSHIFT.0 as u32 => "RightShift".to_string(),
        value if value == VK_LCONTROL.0 as u32 => "LeftCtrl".to_string(),
        value if value == VK_LSHIFT.0 as u32 => "LeftShift".to_string(),
        value if value == VK_MENU.0 as u32 || value == VK_LMENU.0 as u32 => "LeftAlt".to_string(),
        value if value == VK_RMENU.0 as u32 => "RightAlt".to_string(),
        value if value == VK_LWIN.0 as u32 => "LeftWin".to_string(),
        value if value == VK_RWIN.0 as u32 => "RightWin".to_string(),
        value if value == VK_SHIFT.0 as u32 => "Shift".to_string(),
        other => format!("VK_{other:03}"),
    }
}
