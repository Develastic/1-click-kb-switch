from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from one_click_kb_switch.core.controller import RuntimeController
from one_click_kb_switch.core.models import LayoutInfo
from one_click_kb_switch.ui.tray import TrayIcon


def run_app(controller: RuntimeController) -> int:
    _ensure_tk_support()
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = MainWindow(root, controller)
    root.mainloop()
    return 0 if app.exit_requested else 1


def _ensure_tk_support() -> None:
    if tk.TkVersion < 8.6:
        raise RuntimeError("Tk/Tcl support is missing or too old. Use a Python build with Tk support.")


class MainWindow:
    def __init__(self, root: ctk.CTk, controller: RuntimeController) -> None:
        self.root = root
        self.controller = controller
        self.exit_requested = False
        self._label_vars: dict[str, tk.StringVar] = {}
        self.root.title("1-Click-KB-Switch")
        self.root.geometry("860x640")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(300, self._poll_active_layout)
        self._build_layout()
        self.tray = TrayIcon(controller.state.tray_label, self.show_window, self.exit_app)
        self.tray.run()
        self.controller.start_hooks(self._switch_from_hook)
        if self.controller.config.has_completed_first_run and self.controller.config.start_minimized_after_first_run:
            self.hide_window()
        else:
            self.controller.mark_first_run_complete()

    def _build_layout(self) -> None:
        header = ctk.CTkLabel(
            self.root,
            text="Directed keyboard switching: one key, one layout.",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        header.pack(padx=20, pady=(20, 10), anchor="w")

        switches = ctk.CTkFrame(self.root)
        switches.pack(fill="x", padx=20, pady=(0, 10))
        self.sound_var = tk.BooleanVar(value=self.controller.config.play_switch_sound)
        self.minimized_var = tk.BooleanVar(value=self.controller.config.start_minimized_after_first_run)
        ctk.CTkCheckBox(switches, text="Play sound on successful switch", variable=self.sound_var, command=self._toggle_sound).pack(anchor="w", padx=12, pady=8)
        ctk.CTkCheckBox(switches, text="Start minimized after first run", variable=self.minimized_var, command=self._toggle_start_minimized).pack(anchor="w", padx=12, pady=8)

        help_text = ctk.CTkLabel(
            self.root,
            text="Default single-click bindings: RightCtrl → English, RightShift → first non-English layout.",
            justify="left",
        )
        help_text.pack(padx=20, pady=(0, 10), anchor="w")

        self.warning_box = ctk.CTkTextbox(self.root, height=90)
        self.warning_box.pack(fill="x", padx=20, pady=(0, 10))
        self.warning_box.insert("1.0", self._warning_text())
        self.warning_box.configure(state="disabled")

        self.layouts_frame = ctk.CTkScrollableFrame(self.root, label_text="Detected layouts")
        self.layouts_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._render_layouts()

    def _render_layouts(self) -> None:
        for child in self.layouts_frame.winfo_children():
            child.destroy()
        self._label_vars.clear()
        for index, layout in enumerate(self.controller.layouts):
            row = ctk.CTkFrame(self.layouts_frame)
            row.grid(row=index, column=0, padx=8, pady=8, sticky="ew")
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=layout.display_name, width=180, anchor="w").grid(row=0, column=0, padx=8, pady=6, sticky="w")
            binding_text = self._binding_text(layout)
            ctk.CTkLabel(row, text=binding_text, width=220, anchor="w").grid(row=0, column=1, padx=8, pady=6, sticky="w")
            ctk.CTkLabel(row, text=f"Auto: {layout.auto_label}", width=80).grid(row=0, column=2, padx=8, pady=6)
            label_var = tk.StringVar(value=layout.label_override)
            self._label_vars[layout.layout_id] = label_var
            entry = ctk.CTkEntry(row, textvariable=label_var, width=90)
            entry.grid(row=0, column=3, padx=8, pady=6)
            ctk.CTkButton(row, text="Save label", width=100, command=lambda layout_id=layout.layout_id, value=label_var: self._save_label(layout_id, value.get())).grid(row=0, column=4, padx=8, pady=6)
            ctk.CTkButton(row, text="Capture custom", width=120, command=lambda layout_id=layout.layout_id: self._capture_custom(layout_id)).grid(row=0, column=5, padx=8, pady=6)
            ctk.CTkButton(row, text="Clear custom", width=100, command=lambda layout_id=layout.layout_id: self._clear_custom(layout_id)).grid(row=0, column=6, padx=8, pady=6)

    def _binding_text(self, layout: LayoutInfo) -> str:
        matches = [item for item in self.controller.config.hotkeys if item.layout_id == layout.layout_id]
        if not matches:
            return "No binding"
        parts = []
        for item in matches:
            if item.binding_type == "single_click":
                parts.append(f"Single click {item.trigger_key}")
            else:
                modifier_text = "+".join(item.modifiers)
                parts.append(f"Custom {modifier_text}+{item.trigger_key}" if modifier_text else f"Custom {item.trigger_key}")
        return " | ".join(parts)

    def _save_label(self, layout_id: str, value: str) -> None:
        self.controller.update_label_override(layout_id, value)
        self.tray.update_label(self.controller.state.tray_label)

    def _capture_custom(self, layout_id: str) -> None:
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Capture custom hotkey")
        dialog.geometry("320x160")
        ctk.CTkLabel(dialog, text="Press the key or combination inside this dialog.").pack(padx=16, pady=(16, 8))
        result = ctk.CTkLabel(dialog, text="Waiting for input...")
        result.pack(padx=16, pady=8)
        state = {"modifiers": [], "key": None}

        def on_key(event) -> None:
            key = event.keysym
            if key in {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Super_L", "Super_R"}:
                if key not in state["modifiers"]:
                    state["modifiers"].append(key.replace("_L", "").replace("_R", ""))
                result.configure(text=" + ".join(state["modifiers"]))
                return
            state["key"] = key
            result.configure(text=" + ".join(state["modifiers"] + [key]))

        def save() -> None:
            if not state["key"]:
                messagebox.showerror("Capture custom hotkey", "No key was captured.")
                return
            self.controller.apply_custom_binding(layout_id, state["key"], state["modifiers"])
            self._render_layouts()
            dialog.destroy()

        dialog.bind("<KeyPress>", on_key)
        ctk.CTkButton(dialog, text="Save", command=save).pack(pady=(10, 6))
        ctk.CTkButton(dialog, text="Cancel", command=dialog.destroy).pack(pady=(0, 12))
        dialog.focus_force()
        dialog.grab_set()

    def _clear_custom(self, layout_id: str) -> None:
        self.controller.clear_custom_binding(layout_id)
        self._render_layouts()

    def _toggle_sound(self) -> None:
        self.controller.set_play_switch_sound(self.sound_var.get())

    def _toggle_start_minimized(self) -> None:
        self.controller.set_start_minimized(self.minimized_var.get())

    def _warning_text(self) -> str:
        warnings = [item.message for item in self.controller.state.warnings]
        if self.controller.state.last_switch_error:
            warnings.append(self.controller.state.last_switch_error)
        return "\n".join(warnings) if warnings else "No platform warnings."

    def _poll_active_layout(self) -> None:
        try:
            self.controller.refresh_active_layout()
            self.tray.update_label(self.controller.state.tray_label)
        except Exception as exc:  # noqa: BLE001
            self.controller.state.last_switch_error = str(exc)
        self.root.after(800, self._poll_active_layout)

    def _switch_from_hook(self, layout_id: str) -> None:
        switched = self.controller.switch_layout(layout_id)
        if switched and self.controller.config.play_switch_sound:
            self._play_switch_sound()
        self.tray.update_label(self.controller.state.tray_label)

    def _play_switch_sound(self) -> None:
        if sys.platform == "win32":
            import winsound

            winsound.MessageBeep(winsound.MB_OK)
        else:
            self.root.bell()

    def _on_close(self) -> None:
        self.hide_window()

    def hide_window(self) -> None:
        self.root.withdraw()

    def show_window(self) -> None:
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.lift)
        self.root.after(0, self.root.focus_force)

    def exit_app(self) -> None:
        self.exit_requested = True
        self.controller.stop_hooks()
        self.tray.stop()
        self.root.after(0, self.root.destroy)
