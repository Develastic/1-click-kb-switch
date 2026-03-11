from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from one_click_kb_switch.core.controller import RuntimeController
from one_click_kb_switch.core.hotkeys import (
    PRIMARY_DEFAULT_KEY,
    SECONDARY_DEFAULT_KEY,
    SINGLE_CLICK_OPTIONS,
    HotkeyConflictError,
    normalize_modifier_names,
)
from one_click_kb_switch.core.models import LayoutInfo
from one_click_kb_switch.ui.tray import TrayIcon


SURFACE = "#f3f5f9"
CARD = "#ffffff"
ACCENT = "#1f6feb"
ACCENT_SOFT = "#eaf2ff"
TEXT = "#162033"
MUTED = "#6b7280"
BORDER = "#d8dee9"
WARNING_BG = "#fff4d6"
WARNING_TEXT = "#8a5a00"
SUCCESS_BG = "#ecfdf3"
SUCCESS_TEXT = "#156f3d"


def run_app(controller: RuntimeController) -> int:
    _ensure_tk_support()
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk(fg_color=SURFACE)
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
        self._single_click_vars: dict[str, tk.StringVar] = {}
        self._layout_rows: dict[str, dict[str, ctk.CTkBaseClass]] = {}
        self.root.title("1-Click-KB-Switch")
        self.root.geometry("1180x760")
        self.root.minsize(1060, 700)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(300, self._poll_active_layout)
        self._build_layout()
        self.tray = TrayIcon(controller.state.tray_label, self.show_window, self.exit_app)
        self.tray.run()
        self.controller.start_hooks(self._switch_from_hook)
        self._refresh_runtime_summary()
        if self.controller.config.has_completed_first_run and self.controller.config.start_minimized_after_first_run:
            self.hide_window()
        else:
            self.controller.mark_first_run_complete()

    def _build_layout(self) -> None:
        shell = ctk.CTkFrame(self.root, fg_color=SURFACE)
        shell.pack(fill="both", expand=True, padx=18, pady=18)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(2, weight=1)

        self._build_header(shell)
        self._build_overview(shell)
        self._build_layout_table(shell)

    def _build_header(self, parent: ctk.CTkFrame) -> None:
        header = ctk.CTkFrame(parent, fg_color=ACCENT, corner_radius=18)
        header.grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="1-Click-KB-Switch",
            text_color="white",
            font=ctk.CTkFont(size=30, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(18, 6))
        ctk.CTkLabel(
            header,
            text="Directed switching for people who want one key to always mean one layout.",
            text_color="#dbe8ff",
            font=ctk.CTkFont(size=14),
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 6))
        ctk.CTkLabel(
            header,
            text=f"Default single-clicks: {PRIMARY_DEFAULT_KEY} → English, {SECONDARY_DEFAULT_KEY} → first non-English layout",
            text_color="#dbe8ff",
            font=ctk.CTkFont(size=13),
        ).grid(row=2, column=0, sticky="w", padx=24, pady=(0, 18))

    def _build_overview(self, parent: ctk.CTkFrame) -> None:
        overview = ctk.CTkFrame(parent, fg_color=SURFACE)
        overview.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        overview.grid_columnconfigure((0, 1), weight=1)

        left = ctk.CTkFrame(overview, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ctk.CTkFrame(overview, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(left, text="Runtime status", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=18, pady=(16, 10))
        self.active_layout_chip = ctk.CTkLabel(left, text="Current layout: KB", fg_color=ACCENT_SOFT, text_color=ACCENT, corner_radius=999, padx=12, pady=8, font=ctk.CTkFont(size=14, weight="bold"))
        self.active_layout_chip.pack(anchor="w", padx=18, pady=(0, 10))
        self.default_binding_label = ctk.CTkLabel(left, text="", text_color=MUTED, justify="left")
        self.default_binding_label.pack(anchor="w", padx=18, pady=(0, 10))
        self.status_banner = ctk.CTkLabel(left, text="", fg_color=SUCCESS_BG, text_color=SUCCESS_TEXT, corner_radius=12, padx=12, pady=10, justify="left")
        self.status_banner.pack(fill="x", padx=18, pady=(0, 18))

        ctk.CTkLabel(right, text="Application behavior", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=18, pady=(16, 10))
        self.sound_var = tk.BooleanVar(value=self.controller.config.play_switch_sound)
        self.minimized_var = tk.BooleanVar(value=self.controller.config.start_minimized_after_first_run)
        ctk.CTkCheckBox(right, text="Play sound after a successful directed switch", variable=self.sound_var, command=self._toggle_sound).pack(anchor="w", padx=18, pady=(0, 10))
        ctk.CTkCheckBox(right, text="Start hidden in tray after the first successful run", variable=self.minimized_var, command=self._toggle_start_minimized).pack(anchor="w", padx=18, pady=(0, 12))
        ctk.CTkLabel(right, text="The tray menu is intentionally minimal: Show main window and Exit.", text_color=MUTED, justify="left", wraplength=420).pack(anchor="w", padx=18, pady=(0, 18))

    def _build_layout_table(self, parent: ctk.CTkFrame) -> None:
        container = ctk.CTkFrame(parent, fg_color=CARD, border_width=1, border_color=BORDER, corner_radius=16)
        container.grid(row=2, column=0, sticky="nsew")
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(container, fg_color=CARD)
        title_row.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(title_row, text="Layouts and hotkeys", text_color=TEXT, font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(title_row, text="Override tray labels, inspect bindings, and capture a custom shortcut.", text_color=MUTED).grid(row=1, column=0, sticky="w", pady=(4, 0))

        self.layouts_frame = ctk.CTkScrollableFrame(container, fg_color=CARD, corner_radius=0, scrollbar_button_color="#a7b0c0", scrollbar_button_hover_color="#7f8a9b")
        self.layouts_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.layouts_frame.grid_columnconfigure(0, weight=1)
        self._render_layouts()

    def _render_layouts(self) -> None:
        for child in self.layouts_frame.winfo_children():
            child.destroy()
        self._layout_rows.clear()
        self._label_vars.clear()
        self._single_click_vars.clear()

        header = ctk.CTkFrame(self.layouts_frame, fg_color=ACCENT_SOFT, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=2, pady=(0, 12))
        for idx, text in enumerate(["Layout", "Directed hotkey", "Tray label", "Actions"]):
            ctk.CTkLabel(header, text=text, text_color=ACCENT, font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=idx, padx=14, pady=10, sticky="w")
        header.grid_columnconfigure(0, weight=3)
        header.grid_columnconfigure(1, weight=3)
        header.grid_columnconfigure(2, weight=3)
        header.grid_columnconfigure(3, weight=4)

        for index, layout in enumerate(self.controller.layouts, start=1):
            row = ctk.CTkFrame(self.layouts_frame, fg_color="#fbfcfe", border_width=1, border_color=BORDER, corner_radius=14)
            row.grid(row=index, column=0, sticky="ew", padx=2, pady=6)
            row.grid_columnconfigure(0, weight=3)
            row.grid_columnconfigure(1, weight=3)
            row.grid_columnconfigure(2, weight=3)
            row.grid_columnconfigure(3, weight=4)

            layout_box = ctk.CTkFrame(row, fg_color="transparent")
            layout_box.grid(row=0, column=0, sticky="ew", padx=(16, 12), pady=14)
            ctk.CTkLabel(layout_box, text=layout.display_name, text_color=TEXT, font=ctk.CTkFont(size=15, weight="bold"), anchor="w").pack(anchor="w")
            ctk.CTkLabel(layout_box, text=f"ID: {layout.layout_id}", text_color=MUTED, font=ctk.CTkFont(size=12), anchor="w").pack(anchor="w", pady=(4, 0))

            binding_box = ctk.CTkFrame(row, fg_color="transparent")
            binding_box.grid(row=0, column=1, sticky="ew", padx=(4, 12), pady=14)
            binding_box.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(binding_box, text="Single click", text_color=MUTED, anchor="w").grid(row=0, column=0, sticky="w")
            single_click_var = tk.StringVar(value=self._single_click_option_value(layout.layout_id))
            self._single_click_vars[layout.layout_id] = single_click_var
            single_click_selector = ctk.CTkOptionMenu(
                binding_box,
                values=SINGLE_CLICK_OPTIONS,
                variable=single_click_var,
                width=180,
                fg_color="#eef1f5",
                text_color=TEXT,
                button_color="#d7deea",
                button_hover_color="#c7cfdd",
                dropdown_fg_color=CARD,
                dropdown_text_color=TEXT,
            )
            single_click_selector.grid(row=1, column=0, sticky="w", pady=(6, 8))
            binding_label = ctk.CTkLabel(binding_box, text=self._binding_text(layout), text_color=TEXT, justify="left", wraplength=260, anchor="w")
            binding_label.grid(row=2, column=0, sticky="w")

            labels_box = ctk.CTkFrame(row, fg_color="transparent")
            labels_box.grid(row=0, column=2, sticky="ew", padx=(4, 12), pady=14)
            ctk.CTkLabel(labels_box, text=f"Auto: {layout.auto_label}", text_color=MUTED, anchor="w").pack(anchor="w")
            effective_chip = ctk.CTkLabel(labels_box, text=f"Shown in tray: {layout.effective_label}", fg_color=ACCENT_SOFT, text_color=ACCENT, corner_radius=999, padx=10, pady=6)
            effective_chip.pack(anchor="w", pady=(8, 0))
            label_var = tk.StringVar(value=layout.label_override)
            self._label_vars[layout.layout_id] = label_var

            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.grid(row=0, column=3, sticky="ew", padx=(4, 16), pady=14)
            actions.grid_columnconfigure(0, weight=1)
            top_actions = ctk.CTkFrame(actions, fg_color="transparent")
            top_actions.grid(row=0, column=0, sticky="ew")
            label_entry = ctk.CTkEntry(top_actions, textvariable=label_var, width=120, placeholder_text="Override")
            label_entry.grid(row=0, column=0, padx=(0, 8), pady=(0, 8), sticky="w")
            ctk.CTkButton(top_actions, text="Save label", width=104, fg_color=ACCENT, hover_color="#1858bb", command=lambda layout_id=layout.layout_id, value=label_var: self._save_label(layout_id, value.get())).grid(row=0, column=1, padx=(0, 8), pady=(0, 8))
            middle_actions = ctk.CTkFrame(actions, fg_color="transparent")
            middle_actions.grid(row=1, column=0, sticky="ew")
            ctk.CTkButton(middle_actions, text="Save directed", width=122, fg_color=ACCENT, hover_color="#1858bb", command=lambda layout_id=layout.layout_id, value=single_click_var: self._save_single_click(layout_id, value.get())).grid(row=0, column=0, padx=(0, 8), pady=(0, 8))
            ctk.CTkButton(middle_actions, text="Ignore layout", width=110, fg_color="#eef1f5", text_color=TEXT, hover_color="#dfe5ee", command=lambda layout_id=layout.layout_id: self._ignore_layout(layout_id)).grid(row=0, column=1, pady=(0, 8))

            bottom_actions = ctk.CTkFrame(actions, fg_color="transparent")
            bottom_actions.grid(row=2, column=0, sticky="ew")
            ctk.CTkButton(bottom_actions, text="Capture combo", width=122, fg_color="#1f2937", hover_color="#111827", command=lambda layout_id=layout.layout_id: self._capture_custom(layout_id)).grid(row=0, column=0, padx=(0, 8))
            ctk.CTkButton(bottom_actions, text="Clear combo", width=110, fg_color="#eef1f5", text_color=TEXT, hover_color="#dfe5ee", command=lambda layout_id=layout.layout_id: self._clear_custom(layout_id)).grid(row=0, column=1)

            self._layout_rows[layout.layout_id] = {
                "binding": binding_label,
                "effective": effective_chip,
            }

    def _binding_text(self, layout: LayoutInfo) -> str:
        single = self.controller.single_click_binding_for_layout(layout.layout_id)
        combo = self.controller.combo_binding_for_layout(layout.layout_id)
        if not single and not combo:
            return "Ignored in directed switching."
        parts = []
        if single:
            parts.append(f"Single click on {single.trigger_key}")
        else:
            parts.append("Single click is disabled")
        if combo:
            modifier_text = " + ".join(combo.modifiers)
            parts.append(f"Custom combo: {modifier_text} + {combo.trigger_key}" if modifier_text else f"Custom key: {combo.trigger_key}")
        else:
            parts.append("No custom combo")
        return "\n".join(parts)

    def _single_click_option_value(self, layout_id: str) -> str:
        binding = self.controller.single_click_binding_for_layout(layout_id)
        return binding.trigger_key if binding else "Ignore"

    def _save_label(self, layout_id: str, value: str) -> None:
        self.controller.update_label_override(layout_id, value)
        self._refresh_layout_row(layout_id)
        self._refresh_runtime_summary()
        self.tray.update_label(self.controller.state.tray_label)

    def _save_single_click(self, layout_id: str, value: str) -> None:
        try:
            self.controller.set_single_click_binding(layout_id, None if value == "Ignore" else value)
        except HotkeyConflictError as exc:
            messagebox.showerror("Save directed hotkey", str(exc))
            self._single_click_vars[layout_id].set(self._single_click_option_value(layout_id))
            return
        self._refresh_layout_row(layout_id)
        self._refresh_runtime_summary()

    def _ignore_layout(self, layout_id: str) -> None:
        self.controller.ignore_layout(layout_id)
        self._single_click_vars[layout_id].set("Ignore")
        self._refresh_layout_row(layout_id)
        self._refresh_runtime_summary()

    def _capture_custom(self, layout_id: str) -> None:
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Capture custom hotkey")
        dialog.geometry("420x250")
        dialog.resizable(False, False)
        dialog.configure(fg_color=SURFACE)
        ctk.CTkLabel(dialog, text="Capture a custom hotkey", text_color=TEXT, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", padx=18, pady=(18, 8))
        ctk.CTkLabel(dialog, text="Hold modifiers first, then press the final key. Use this only for layouts that need an extra directed shortcut.", text_color=MUTED, justify="left", wraplength=360).pack(anchor="w", padx=18, pady=(0, 12))
        result = ctk.CTkLabel(dialog, text="Waiting for input…", fg_color=ACCENT_SOFT, text_color=ACCENT, corner_radius=12, padx=12, pady=12)
        result.pack(fill="x", padx=18, pady=(0, 14))
        state = {"modifiers": [], "key": None}

        def on_key(event) -> None:
            key = self._normalize_capture_key(event.keysym)
            if key in {"LeftShift", "RightShift", "LeftCtrl", "RightCtrl", "LeftAlt", "RightAlt", "LeftSuper", "RightSuper"}:
                normalized = key
                if normalized not in state["modifiers"]:
                    state["modifiers"].append(normalized)
                result.configure(text=" + ".join(state["modifiers"]))
                return
            state["key"] = key
            state["modifiers"] = normalize_modifier_names(state["modifiers"])
            result.configure(text=" + ".join(state["modifiers"] + [key]))

        def save() -> None:
            if not state["key"]:
                messagebox.showerror("Capture custom hotkey", "No key was captured.")
                return
            try:
                self.controller.apply_custom_binding(layout_id, state["key"], state["modifiers"])
            except HotkeyConflictError as exc:
                messagebox.showerror("Capture custom hotkey", str(exc))
                return
            self._refresh_layout_row(layout_id)
            dialog.destroy()

        dialog.bind("<KeyPress>", on_key)
        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkButton(buttons, text="Save", fg_color=ACCENT, hover_color="#1858bb", command=save).pack(side="left")
        ctk.CTkButton(buttons, text="Cancel", fg_color="#eef1f5", text_color=TEXT, hover_color="#dfe5ee", command=dialog.destroy).pack(side="left", padx=(10, 0))
        dialog.focus_force()
        dialog.grab_set()

    def _clear_custom(self, layout_id: str) -> None:
        self.controller.clear_custom_binding(layout_id)
        self._refresh_layout_row(layout_id)

    def _refresh_layout_row(self, layout_id: str) -> None:
        layout = next(item for item in self.controller.layouts if item.layout_id == layout_id)
        widgets = self._layout_rows[layout_id]
        widgets["binding"].configure(text=self._binding_text(layout))
        widgets["effective"].configure(text=f"Shown in tray: {layout.effective_label}")
        self._single_click_vars[layout_id].set(self._single_click_option_value(layout_id))

    def _toggle_sound(self) -> None:
        self.controller.set_play_switch_sound(self.sound_var.get())
        self._refresh_runtime_summary()

    def _toggle_start_minimized(self) -> None:
        self.controller.set_start_minimized(self.minimized_var.get())
        self._refresh_runtime_summary()

    def _warning_text(self) -> str:
        warnings = [item.message for item in self.controller.state.warnings]
        if self.controller.state.last_switch_error:
            warnings.append(self.controller.state.last_switch_error)
        return "\n".join(warnings)

    def _refresh_runtime_summary(self) -> None:
        active_label = self.controller.effective_label(self.controller.state.active_layout_id)
        self.active_layout_chip.configure(text=f"Current layout: {active_label}")
        self.default_binding_label.configure(
            text=(
                f"Default directed hotkeys\n"
                f"• {PRIMARY_DEFAULT_KEY} → English layout\n"
                f"• {SECONDARY_DEFAULT_KEY} → first non-English layout"
            )
        )
        warning_text = self._warning_text()
        if warning_text:
            self.status_banner.configure(text=warning_text, fg_color=WARNING_BG, text_color=WARNING_TEXT)
        else:
            self.status_banner.configure(
                text="Runtime looks healthy. Tray labels are rendered with a real font and the tray menu stays intentionally minimal.",
                fg_color=SUCCESS_BG,
                text_color=SUCCESS_TEXT,
            )

    def _poll_active_layout(self) -> None:
        try:
            self.controller.refresh_active_layout()
            self._refresh_runtime_summary()
            self.tray.update_label(self.controller.state.tray_label)
        except Exception as exc:  # noqa: BLE001
            self.controller.state.last_switch_error = str(exc)
            self._refresh_runtime_summary()
        self.root.after(800, self._poll_active_layout)

    def _switch_from_hook(self, layout_id: str) -> None:
        switched = self.controller.switch_layout(layout_id)
        if switched and self.controller.config.play_switch_sound:
            self._play_switch_sound()
        self._refresh_runtime_summary()
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

    @staticmethod
    def _normalize_capture_key(keysym: str) -> str:
        mapping = {
            "Shift_L": "LeftShift",
            "Shift_R": "RightShift",
            "Control_L": "LeftCtrl",
            "Control_R": "RightCtrl",
            "Alt_L": "LeftAlt",
            "Alt_R": "RightAlt",
            "Super_L": "LeftSuper",
            "Super_R": "RightSuper",
            "Return": "Enter",
            "space": "Space",
        }
        return mapping.get(keysym, keysym)
