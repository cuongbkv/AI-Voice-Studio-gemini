"""
ui/pages/settings.py
======================
API Key, output folder, theme, and auto-update-voice-list toggle.
Also exposes a "Clear cache" action since cache.py is otherwise invisible
to the user.
"""

from __future__ import annotations

from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from config import AppSettings, GEMINI_TTS_MODELS, THEMES
from cache import GenerationCache


class SettingsPage(ctk.CTkFrame):
    """User-configurable application settings."""

    def __init__(
        self,
        master,
        settings: AppSettings,
        cache: GenerationCache,
        on_settings_changed: Callable[[AppSettings], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._settings = settings
        self._cache = cache
        self._on_settings_changed = on_settings_changed

        ctk.CTkLabel(
            self, text="Settings", font=ctk.CTkFont(size=26, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 16))

        panel = ctk.CTkFrame(self, corner_radius=10)
        panel.pack(fill="x", padx=20)

        # API Keys (Multi-line)
        key_label_row = ctk.CTkFrame(panel, fg_color="transparent")
        key_label_row.pack(anchor="w", padx=20, pady=(20, 4), fill="x")
        ctk.CTkLabel(key_label_row, text="Danh sách Gemini API Keys", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(key_label_row, text=" (nhập mỗi Key trên một dòng)", text_color="#8A8A8A").pack(side="left", padx=4)

        self._api_key_box = ctk.CTkTextbox(panel, width=550, height=90)
        existing_keys = "\n".join(settings.get_api_keys())
        self._api_key_box.insert("1.0", existing_keys)
        self._api_key_box.pack(anchor="w", padx=20, pady=(0, 16))

        # Model
        ctk.CTkLabel(panel, text="Model", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=20, pady=(0, 4)
        )
        self._model_var = ctk.StringVar(value=settings.model)
        ctk.CTkOptionMenu(panel, values=GEMINI_TTS_MODELS, variable=self._model_var, width=300).pack(
            anchor="w", padx=20, pady=(0, 16)
        )

        # Output folder
        ctk.CTkLabel(panel, text="Output Folder", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=20, pady=(0, 4)
        )
        folder_row = ctk.CTkFrame(panel, fg_color="transparent")
        folder_row.pack(anchor="w", padx=20, pady=(0, 16), fill="x")
        self._folder_var = ctk.StringVar(value=settings.output_folder)
        ctk.CTkEntry(folder_row, textvariable=self._folder_var, width=350).pack(side="left")
        ctk.CTkButton(folder_row, text="...", width=36, command=self._browse_folder).pack(
            side="left", padx=6
        )

        # Theme
        ctk.CTkLabel(panel, text="Theme", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=20, pady=(0, 4)
        )
        self._theme_var = ctk.StringVar(value=settings.theme)
        ctk.CTkSegmentedButton(
            panel, values=THEMES, variable=self._theme_var, command=self._on_theme_preview
        ).pack(anchor="w", padx=20, pady=(0, 16))

        # Auto update voice list
        self._auto_update_var = ctk.BooleanVar(value=settings.auto_update_voice_list)
        ctk.CTkCheckBox(
            panel, text="Tự động cập nhật danh sách voice khi khởi động (đọc lại voices.json)",
            variable=self._auto_update_var,
        ).pack(anchor="w", padx=20, pady=(0, 20))

        # Buttons
        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(anchor="w", padx=20, pady=(0, 20))
        ctk.CTkButton(btn_row, text="💾 Lưu Settings", command=self._save).pack(side="left")
        ctk.CTkButton(
            btn_row, text="🔄 Reset Cờ Limit Keys", fg_color="transparent", border_width=1,
            command=self._reset_key_limits,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_row, text="🗑 Xoá Cache", fg_color="transparent", border_width=1,
            command=self._clear_cache,
        ).pack(side="left", padx=8)

        self._status_label = ctk.CTkLabel(self, text="", text_color="#66BB6A")
        self._status_label.pack(anchor="w", padx=20, pady=(0, 10))

    def _browse_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self._folder_var.get() or ".")
        if folder:
            self._folder_var.set(folder)

    def _on_theme_preview(self, value: str) -> None:
        ctk.set_appearance_mode(value.lower())

    def _clear_cache(self) -> None:
        count = self._cache.clear()
        self._status_label.configure(text=f"Đã xoá {count} file cache.")

    def _reset_key_limits(self) -> None:
        self._on_settings_changed(self._settings)
        self._status_label.configure(text="Đã làm mới danh sách và reset cờ limit của tất cả API Key.")

    def _save(self) -> None:
        raw_keys = self._api_key_box.get("1.0", "end-1c")
        keys = [line.strip() for line in raw_keys.splitlines() if line.strip()]
        self._settings.api_keys = keys
        self._settings.model = self._model_var.get()
        self._settings.output_folder = self._folder_var.get().strip()
        self._settings.theme = self._theme_var.get()
        self._settings.auto_update_voice_list = self._auto_update_var.get()
        self._settings.ensure_dirs()
        self._settings.save()
        count = len(self._settings.api_keys)
        self._status_label.configure(text=f"Đã lưu settings.json thành công ({count} API Keys).")
        self._on_settings_changed(self._settings)

