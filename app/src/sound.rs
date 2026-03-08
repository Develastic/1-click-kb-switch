use anyhow::Result;

pub fn play_switch(enabled: bool) -> Result<()> {
    if !enabled {
        return Ok(());
    }

    #[cfg(target_os = "windows")]
    {
        use windows::Win32::System::Diagnostics::Debug::MessageBeep;
        use windows::Win32::UI::WindowsAndMessaging::MB_OK;
        unsafe { MessageBeep(MB_OK) }?;
    }

    Ok(())
}
