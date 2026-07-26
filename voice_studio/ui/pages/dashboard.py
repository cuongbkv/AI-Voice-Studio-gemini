"""
ui/pages/dashboard.py
======================
Landing page: quick stats, recent history, and a realtime colored log panel
fed by logs.UILogHandler.
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from logs import LEVEL_COLORS
from history_repository import HistoryRepository
from voice_repository import VoiceRepository


class DashboardPage(ctk.CTkFrame):
    """Overview page shown on launch."""

    def __init__(
        self,
        master,
        voice_repo: VoiceRepository,
        history_repo: HistoryRepository,
        on_navigate: Callable[[str], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._voice_repo = voice_repo
        self._history_repo = history_repo
        self._on_navigate = on_navigate

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="Dashboard", font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        self._stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._stats_frame.grid(row=1, column=0, sticky="ew", padx=20)
        self._stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self._build_stat_cards()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=20, pady=20)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Recent history
        recent_frame = ctk.CTkFrame(body, corner_radius=10)
        recent_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(
            recent_frame, text="Hoạt động gần đây", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=14, pady=(14, 6))
        self._recent_scroll = ctk.CTkScrollableFrame(recent_frame, fg_color="transparent")
        self._recent_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Log panel
        log_frame = ctk.CTkFrame(body, corner_radius=10)
        log_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        ctk.CTkLabel(
            log_frame, text="Log realtime", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=14, pady=(14, 6))
        self.log_textbox = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_textbox.configure(state="disabled")
        for level, color in LEVEL_COLORS.items():
            self.log_textbox.tag_config(level, foreground=color)

        self.refresh()

    # ------------------------------------------------------------------ #
    def _build_stat_cards(self) -> None:
        voices = self._voice_repo.all()
        history = self._history_repo.all()
        favorites = [v for v in voices if v.favorite]

        stats = [
            ("Tổng số Voice", str(len(voices))),
            ("Đã tạo (lịch sử)", str(len(history))),
            ("Voice yêu thích", str(len(favorites))),
            ("Thể loại", str(len(self._voice_repo.all_categories()))),
        ]
        for i, (label, value) in enumerate(stats):
            card = ctk.CTkFrame(self._stats_frame, corner_radius=10)
            card.grid(row=0, column=i, sticky="ew", padx=6, pady=6)
            ctk.CTkLabel(
                card, text=value, font=ctk.CTkFont(size=26, weight="bold")
            ).pack(padx=16, pady=(14, 0))
            ctk.CTkLabel(card, text=label, text_color="#8A8A8A").pack(
                padx=16, pady=(0, 14)
            )

    def refresh(self) -> None:
        """Refresh stat cards and recent activity list (call after generation)."""
        for widget in self._stats_frame.winfo_children():
            widget.destroy()
        self._build_stat_cards()

        for widget in self._recent_scroll.winfo_children():
            widget.destroy()
        recent = self._history_repo.all()[:8]
        if not recent:
            ctk.CTkLabel(
                self._recent_scroll, text="Chưa có hoạt động nào.", text_color="#8A8A8A"
            ).pack(anchor="w", pady=4)
        for entry in recent:
            row = ctk.CTkFrame(self._recent_scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row, text=f"{entry.date}  •  {entry.voice_name}", anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
            ).pack(anchor="w")
            ctk.CTkLabel(
                row, text=entry.text[:70] + ("…" if len(entry.text) > 70 else ""),
                anchor="w", text_color="#8A8A8A", font=ctk.CTkFont(size=11),
            ).pack(anchor="w")

    def append_log(self, level: str, message: str) -> None:
        """Called (via .after from the UI thread) by the app's log callback."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n", level)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
