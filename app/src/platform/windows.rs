#![cfg(target_os = "windows")]

use crate::layouts::{LayoutInfo, build_info};
use crate::platform::{PlatformBackend, PlatformWarning};
use anyhow::{Context, Result, bail};
use windows::Win32::Foundation::{HWND, LPARAM, WPARAM};
use windows::Win32::Globalization::{
    GetLocaleInfoEx, LCIDToLocaleName, LOCALE_SLOCALIZEDDISPLAYNAME,
};
use windows::Win32::UI::Input::KeyboardAndMouse::{
    ACTIVATE_KEYBOARD_LAYOUT_FLAGS, ActivateKeyboardLayout, GetKeyboardLayout,
    GetKeyboardLayoutList, HKL, KLF_ACTIVATE, KLF_SETFORPROCESS, KLF_SUBSTITUTE_OK,
    LoadKeyboardLayoutW,
};
use windows::Win32::UI::WindowsAndMessaging::{
    GetForegroundWindow, GetWindowThreadProcessId, PostMessageW, WM_INPUTLANGCHANGEREQUEST,
};
use windows::core::PCWSTR;

#[derive(Debug, Default)]
pub struct WindowsBackend;

impl PlatformBackend for WindowsBackend {
    fn list_layouts(&self) -> Result<Vec<LayoutInfo>> {
        let active_id = self.get_active_layout()?;
        let layouts = installed_keyboard_layouts()?;
        Ok(layouts
            .into_iter()
            .map(|entry| {
                let override_label = String::new();
                let mut info = build_info(&entry.klid, &entry.display_name, &override_label);
                if active_id.as_deref() == Some(entry.klid.as_str()) {
                    info.label_override = info.label_override.to_uppercase();
                }
                info
            })
            .collect())
    }

    fn get_active_layout(&self) -> Result<Option<String>> {
        let hwnd = foreground_window()?;
        let thread_id = foreground_thread_id(hwnd);
        let hkl = unsafe { GetKeyboardLayout(thread_id) };
        if is_invalid_hkl(hkl) {
            return Ok(None);
        }
        Ok(Some(hkl_to_klid(hkl)))
    }

    fn switch_layout(&self, layout_id: &str) -> Result<()> {
        let target_hkl = resolve_target_hkl(layout_id)?;
        unsafe {
            ActivateKeyboardLayout(
                target_hkl,
                ACTIVATE_KEYBOARD_LAYOUT_FLAGS(KLF_ACTIVATE.0 | KLF_SETFORPROCESS.0),
            )
        }
        .context("failed to activate keyboard layout in the current process")?;

        let hwnd = foreground_window()?;
        unsafe {
            PostMessageW(
                Some(hwnd),
                WM_INPUTLANGCHANGEREQUEST,
                WPARAM(0),
                LPARAM(target_hkl.0 as isize),
            )
        }
        .context("failed to request keyboard layout change for the foreground window")?;

        Ok(())
    }

    fn platform_warnings(&self) -> Vec<PlatformWarning> {
        vec![PlatformWarning {
            message: "Single-click low-level hooks are not implemented yet on Windows.".to_string(),
        }]
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct WindowsLayoutEntry {
    klid: String,
    display_name: String,
}

fn installed_keyboard_layouts() -> Result<Vec<WindowsLayoutEntry>> {
    let count = unsafe { GetKeyboardLayoutList(None) };
    if count <= 0 {
        bail!("GetKeyboardLayoutList returned no keyboard layouts");
    }

    let mut buffer = vec![HKL::default(); count as usize];
    let written = unsafe { GetKeyboardLayoutList(Some(buffer.as_mut_slice())) };
    if written <= 0 {
        bail!("GetKeyboardLayoutList failed to enumerate keyboard layouts");
    }

    let mut items = Vec::with_capacity(written as usize);
    for hkl in buffer.into_iter().take(written as usize) {
        let klid = hkl_to_klid(hkl);
        let display_name = display_name_for_hkl(hkl)?;
        items.push(WindowsLayoutEntry { klid, display_name });
    }
    Ok(items)
}

fn resolve_target_hkl(layout_id: &str) -> Result<HKL> {
    let normalized = normalize_klid(layout_id)?;
    if let Some(entry) = installed_keyboard_layouts()?
        .into_iter()
        .find(|entry| entry.klid.eq_ignore_ascii_case(&normalized))
    {
        return parse_hkl(&entry.klid);
    }

    let wide = to_wide_null(&normalized);
    let hkl = unsafe {
        LoadKeyboardLayoutW(
            PCWSTR(wide.as_ptr()),
            ACTIVATE_KEYBOARD_LAYOUT_FLAGS(
                KLF_ACTIVATE.0 | KLF_SETFORPROCESS.0 | KLF_SUBSTITUTE_OK.0,
            ),
        )
    }
    .with_context(|| format!("failed to load keyboard layout {normalized}"))?;

    Ok(hkl)
}

fn display_name_for_hkl(hkl: HKL) -> Result<String> {
    let locale_id = language_id_from_hkl(hkl);
    if locale_id == 0 {
        return Ok(hkl_to_klid(hkl));
    }

    let mut locale_name = vec![0u16; 85];
    let locale_name_len =
        unsafe { LCIDToLocaleName(locale_id, Some(locale_name.as_mut_slice()), 0) };
    if locale_name_len <= 1 {
        return Ok(hkl_to_klid(hkl));
    }
    let locale_name = String::from_utf16_lossy(&locale_name[..locale_name_len as usize - 1]);

    let locale_name_wide = to_wide_null(&locale_name);
    let mut localized_name = vec![0u16; 256];
    let display_len = unsafe {
        GetLocaleInfoEx(
            PCWSTR(locale_name_wide.as_ptr()),
            LOCALE_SLOCALIZEDDISPLAYNAME,
            Some(localized_name.as_mut_slice()),
        )
    };
    if display_len <= 1 {
        return Ok(locale_name);
    }

    Ok(String::from_utf16_lossy(
        &localized_name[..display_len as usize - 1],
    ))
}

fn foreground_window() -> Result<HWND> {
    let hwnd = unsafe { GetForegroundWindow() };
    if hwnd.is_invalid() {
        bail!("no foreground window is available for keyboard layout switching")
    }
    Ok(hwnd)
}

fn foreground_thread_id(hwnd: HWND) -> u32 {
    unsafe { GetWindowThreadProcessId(hwnd, None) }
}

fn language_id_from_hkl(hkl: HKL) -> u32 {
    ((hkl.0 as usize) & 0xffff) as u32
}

fn hkl_to_klid(hkl: HKL) -> String {
    format!("{:08X}", (hkl.0 as usize) & 0xffff_ffff)
}

fn parse_hkl(klid: &str) -> Result<HKL> {
    let value = u32::from_str_radix(klid, 16)
        .with_context(|| format!("invalid keyboard layout id: {klid}"))?;
    Ok(HKL(value as usize as *mut core::ffi::c_void))
}

fn normalize_klid(layout_id: &str) -> Result<String> {
    let trimmed = layout_id.trim();
    if trimmed.is_empty() {
        bail!("keyboard layout id is required");
    }
    if trimmed.len() != 8 || !trimmed.chars().all(|ch| ch.is_ascii_hexdigit()) {
        bail!("keyboard layout id must be an 8-digit hexadecimal string");
    }
    Ok(trimmed.to_uppercase())
}

fn is_invalid_hkl(hkl: HKL) -> bool {
    hkl.0.is_null()
}

fn to_wide_null(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(core::iter::once(0)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalizes_klid() {
        assert_eq!(normalize_klid("00000409").unwrap(), "00000409");
        assert!(normalize_klid("409").is_err());
        assert!(normalize_klid("00000ZZZ").is_err());
    }

    #[test]
    fn converts_hkl_to_and_from_klid() {
        let hkl = parse_hkl("00000419").unwrap();
        assert_eq!(hkl_to_klid(hkl), "00000419");
        assert_eq!(language_id_from_hkl(hkl), 0x0419);
    }

    #[test]
    fn wide_strings_are_nul_terminated() {
        let wide = to_wide_null("00000409");
        assert_eq!(*wide.last().unwrap(), 0);
    }
}
