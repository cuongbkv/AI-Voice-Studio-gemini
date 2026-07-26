"""
ui/pages/history.py
=====================
Lists every past generation (date, voice, prompt, text, duration, output
path, API time) with a "Play" action that loads the file into the shared
audio player.
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from history_repository import HistoryRepository
from player import AudioPlayer
from ui.components.audio_player_widget import AudioPlayerWidget
import utils

COLUMNS = [
    ("date", "Ngày", 140),
    ("voice_name", "Voice", 100),
    ("prompt_template", "Prompt", 100),
    ("text", "Text", 300),
    ("duration_seconds", "Duration", 80),
    ("output_path", "Output", 220),
    ("api_time_seconds", "API Time (s)", 90),
]


class HistoryPage(ctk.CTkFrame):
    """Read-only history table with playback support."""

    def __init__(self, master, history_repo: HistoryRepository, player: AudioPlayer) -> None:
        super().__init__(master, fg_color="transparent")
        self._history_repo = history_repo
        self._player = player
        self._entries_by_iid: dict[str, str] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="History", font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=20)
        ctk.CTkButton(toolbar, text="🔄 Làm mới", command=self.refresh, width=100).pack(
            side="left"
        )
        ctk.CTkButton(
            toolbar, text="▶ Phát lại đã chọn", command=self._play_selected, width=140
        ).pack(side="left", padx=8)

        table_frame = ctk.CTkFrame(self, corner_radius=10)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            table_frame, columns=[c[0] for c in COLUMNS], show="headings",
            style="Voice.Treeview",
        )
        for col_id, heading, width in COLUMNS:
            self._tree.heading(col_id, text=heading)
            self._tree.column(col_id, width=width, anchor="w")
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        vsb.grid(row=0, column=1, sticky="ns", pady=10)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.bind("<Double-1>", lambda _e: self._play_selected())

        self._player_widget = AudioPlayerWidget(self, self._player)
        self._player_widget.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))

        self.refresh()

    def refresh(self) -> None:
        """Reload history.json into the table."""
        for row in self._tree.get_children():
            self._tree.delete(row)
        self._entries_by_iid.clear()

        for i, entry in enumerate(self._history_repo.all()):
            iid = str(i)
            self._tree.insert(
                "", "end", iid=iid,
                values=(
                    entry.date, entry.voice_name, entry.prompt_template,
                    utils.truncate_text(entry.text, 80),
                    utils.format_duration(entry.duration_seconds),
                    entry.output_path, entry.api_time_seconds,
                ),
            )
            self._entries_by_iid[iid] = entry.output_path

    def _play_selected(self) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        path = self._entries_by_iid.get(selection[0])
        if path and os.path.exists(path):
            entries = self._history_repo.all()
            idx = int(selection[0])
            duration = entries[idx].duration_seconds if idx < len(entries) else 0
            self._player_widget.load_file(path, duration)
            self._player.load_and_play(path)
