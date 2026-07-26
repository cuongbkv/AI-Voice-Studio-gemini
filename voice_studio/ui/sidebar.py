"""
ui/sidebar.py
=============
Left navigation sidebar: Dashboard / Voice Library / Generate Voice /
History / Settings / About.
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

PAGES: list[str] = [
    "Dashboard",
    "Voice Library",
    "Generate Voice",
    "History",
    "Settings",
    "About",
]

PAGE_ICONS: dict[str, str] = {
    "Dashboard": "🏠",
    "Voice Library": "🎙️",
    "Generate Voice": "🪄",
    "History": "🕒",
    "Settings": "⚙️",
    "About": "ℹ️",
}


class Sidebar(ctk.CTkFrame):
    """Fixed-width navigation rail on the left of the main window."""

    def __init__(self, master, on_navigate: Callable[[str], None]) -> None:
        super().__init__(master, width=220, corner_radius=0)
        self.grid_propagate(False)
        self._on_navigate = on_navigate
        self._buttons: dict[str, ctk.CTkButton] = {}

        title = ctk.CTkLabel(
            self, text="AI Voice Studio", font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(24, 4), padx=16, anchor="w")

        subtitle = ctk.CTkLabel(
            self, text="Gemini TTS Studio", font=ctk.CTkFont(size=12),
            text_color="#8A8A8A",
        )
        subtitle.pack(pady=(0, 24), padx=16, anchor="w")

        for page in PAGES:
            btn = ctk.CTkButton(
                self,
                text=f"{PAGE_ICONS[page]}  {page}",
                anchor="w",
                fg_color="transparent",
                hover_color=("gray80", "gray25"),
                text_color=("gray10", "gray90"),
                corner_radius=8,
                height=42,
                font=ctk.CTkFont(size=14),
                command=lambda p=page: self._handle_click(p),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self._buttons[page] = btn

        self.set_active("Dashboard")

    def _handle_click(self, page: str) -> None:
        self.set_active(page)
        self._on_navigate(page)

    def set_active(self, page: str) -> None:
        """Visually highlight the currently active page's button."""
        for name, btn in self._buttons.items():
            if name == page:
                btn.configure(fg_color=("gray75", "gray30"))
            else:
                btn.configure(fg_color="transparent")
