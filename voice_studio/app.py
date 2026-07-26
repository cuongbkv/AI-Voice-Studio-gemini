"""
app.py
======
Application entry point for AI Voice Studio.

Responsibilities of this module (and only this module):
    - Create the CTk root window and sidebar navigation
    - Own the long-lived shared objects (settings, repositories, cache, player)
      and pass them into each page — no globals anywhere else
    - Wire the logger so log lines stream into the Dashboard page
    - Rebuild the shared GeminiTTSClient whenever Settings are saved

Run with:  python app.py
"""

from __future__ import annotations

import logging

import customtkinter as ctk

from config import AppSettings, APP_NAME, WINDOW_SIZE
from logs import setup_logging
from voice_repository import VoiceRepository
from history_repository import HistoryRepository
from cache import GenerationCache
from player import AudioPlayer
from api.gemini import GeminiTTSClient
from api.models import Voice

from ui.sidebar import Sidebar, PAGES
from ui.pages.dashboard import DashboardPage
from ui.pages.voice_library import VoiceLibraryPage
from ui.pages.generate_voice import GenerateVoicePage
from ui.pages.history import HistoryPage
from ui.pages.settings import SettingsPage
from ui.pages.about import AboutPage


class VoiceStudioApp(ctk.CTk):
    """Root application window; owns shared state and page switching."""

    def __init__(self) -> None:
        super().__init__()

        # --- Shared state -------------------------------------------------
        self.settings = AppSettings.load()
        self.settings.ensure_dirs()

        ctk.set_appearance_mode(self.settings.theme.lower())
        ctk.set_default_color_theme("blue")

        self.voice_repo = VoiceRepository(favorites=self.settings.favorites)
        self.history_repo = HistoryRepository()
        self.cache = GenerationCache()
        self.player = AudioPlayer()
        self._client: GeminiTTSClient | None = self._build_client()

        self.title(APP_NAME)
        self.geometry(WINDOW_SIZE)
        self.minsize(1100, 700)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Must exist before logging starts, since log records can arrive
        # (via _on_log_line) before _build_pages() has populated this dict.
        self._pages: dict[str, ctk.CTkFrame] = {}

        # --- Logging: file + console + Dashboard log panel ----------------
        self.logger = setup_logging(ui_callback=self._on_log_line)
        self.logger.info("%s đã khởi động.", APP_NAME)
        if self._client is None:
            self.logger.warning("Chưa có API Key. Vào Settings để cấu hình Gemini API Key.")

        # --- Sidebar + pages ------------------------------------------------
        self.sidebar = Sidebar(self, on_navigate=self._show_page)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.grid(row=0, column=1, sticky="nsew")
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)

        self._build_pages()
        self._show_page("Dashboard")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    def _build_client(self) -> GeminiTTSClient | None:
        keys = self.settings.get_api_keys()
        if not keys:
            return None
        return GeminiTTSClient(keys, self.settings.model)

    def get_client(self) -> GeminiTTSClient | None:
        """Passed into pages so they always fetch the *current* client
        (rebuilt after Settings changes) instead of capturing a stale one."""
        return self._client

    # ------------------------------------------------------------------ #
    def _build_pages(self) -> None:
        dashboard = DashboardPage(
            self._container, self.voice_repo, self.history_repo, self._show_page
        )
        dashboard.grid(row=0, column=0, sticky="nsew")
        self._pages["Dashboard"] = dashboard

        voice_library = VoiceLibraryPage(
            self._container,
            self.voice_repo,
            self.player,
            self.get_client,
            on_use_voice=self._use_voice_in_generate,
            on_favorite_changed=self._persist_favorites,
        )
        voice_library.grid(row=0, column=0, sticky="nsew")
        self._pages["Voice Library"] = voice_library

        generate_voice = GenerateVoicePage(
            self._container,
            self.settings,
            self.voice_repo,
            self.history_repo,
            self.cache,
            self.player,
            self.get_client,
            on_generation_complete=self._on_generation_complete,
        )
        generate_voice.grid(row=0, column=0, sticky="nsew")
        self._pages["Generate Voice"] = generate_voice

        history = HistoryPage(self._container, self.history_repo, self.player)
        history.grid(row=0, column=0, sticky="nsew")
        self._pages["History"] = history

        settings_page = SettingsPage(
            self._container, self.settings, self.cache, self._on_settings_changed
        )
        settings_page.grid(row=0, column=0, sticky="nsew")
        self._pages["Settings"] = settings_page

        about = AboutPage(self._container)
        about.grid(row=0, column=0, sticky="nsew")
        self._pages["About"] = about

    def _show_page(self, name: str) -> None:
        if name not in self._pages:
            return
        self._pages[name].tkraise()
        self.sidebar.set_active(name)

    # ------------------------------------------------------------------ #
    def _use_voice_in_generate(self, voice: Voice) -> None:
        """'Use this voice' in Voice Library: preselect it and jump pages."""
        generate_page: GenerateVoicePage = self._pages["Generate Voice"]  # type: ignore[assignment]
        generate_page.preselect_voice(voice)
        self._show_page("Generate Voice")

    def _persist_favorites(self) -> None:
        self.settings.favorites = self.voice_repo.favorites_list()
        self.settings.save()

    def _on_generation_complete(self) -> None:
        dashboard: DashboardPage = self._pages["Dashboard"]  # type: ignore[assignment]
        history_page: HistoryPage = self._pages["History"]  # type: ignore[assignment]
        dashboard.refresh()
        history_page.refresh()

    def _on_settings_changed(self, settings: AppSettings) -> None:
        self._client = self._build_client()
        self.logger.info("Đã cập nhật cấu hình. Model: %s", settings.model)

    # ------------------------------------------------------------------ #
    def _on_log_line(self, level: str, message: str) -> None:
        """Called from logging (any thread) -> marshal to the UI thread."""
        dashboard = self._pages.get("Dashboard")
        if dashboard is not None:
            self.after(0, lambda: dashboard.append_log(level, message))  # type: ignore[union-attr]

    def _on_close(self) -> None:
        self.player.stop()
        self.destroy()


def main() -> None:
    """Entry point: create and run the application."""
    app = VoiceStudioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
