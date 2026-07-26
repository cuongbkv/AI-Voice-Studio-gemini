"""
ui/pages/voice_library.py
==========================
The core page of the app: browse all voices loaded from voices.json in a
sortable/filterable/searchable table, with a detail panel on the right.

Uses tkinter.ttk.Treeview for the table since CustomTkinter has no native
table widget; the Treeview is themed to blend in with the CTk dark/light
theme as closely as ttk allows.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

import customtkinter as ctk

from api.models import Voice
from api.gemini import GeminiTTSClient
from player import AudioPlayer
from voice_repository import VoiceRepository, SORT_OPTIONS
from ui.components.voice_detail_panel import VoiceDetailPanel

COLUMNS = [
    ("id", "ID", 90),
    ("name", "Voice Name", 130),
    ("gender", "Gender", 70),
    ("style", "Style", 110),
    ("category", "Category", 160),
    ("language", "Language", 80),
    ("description", "Description", 260),
    ("rating", "Rating", 70),
    ("favorite", "Favorite", 70),
]


class VoiceLibraryPage(ctk.CTkFrame):
    """Browse / search / filter / sort all voices; select one for detail view."""

    def __init__(
        self,
        master,
        voice_repo: VoiceRepository,
        player: AudioPlayer,
        get_client: Callable[[], Optional[GeminiTTSClient]],
        on_use_voice: Callable[[Voice], None],
        on_favorite_changed: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._repo = voice_repo
        self._on_favorite_changed = on_favorite_changed
        self._selected_categories: set[str] = set()
        self._favorites_only = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="Voice Library", font=ctk.CTkFont(size=26, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        self._build_toolbar()
        self._build_body(player, get_client, on_use_voice)

        self.refresh()

    # ------------------------------------------------------------------ #
    def _build_toolbar(self) -> None:
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=20)
        toolbar.grid_columnconfigure(0, weight=1)

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self.refresh())
        search_entry = ctk.CTkEntry(
            toolbar, placeholder_text="🔍 Tìm theo tên, style, mô tả, category...",
            textvariable=self._search_var,
        )
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._sort_var = ctk.StringVar(value=SORT_OPTIONS[0])
        sort_menu = ctk.CTkOptionMenu(
            toolbar, values=SORT_OPTIONS, variable=self._sort_var,
            command=lambda *_: self.refresh(), width=140,
        )
        sort_menu.grid(row=0, column=1, padx=4)

        self._fav_var = ctk.BooleanVar(value=False)
        fav_check = ctk.CTkCheckBox(
            toolbar, text="Chỉ Favorite", variable=self._fav_var,
            command=self._on_fav_toggle,
        )
        fav_check.grid(row=0, column=2, padx=8)

        # Category filter chips (scrollable row)
        chip_scroll = ctk.CTkScrollableFrame(
            toolbar, orientation="horizontal", height=44, fg_color="transparent"
        )
        chip_scroll.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self._category_buttons: dict[str, ctk.CTkButton] = {}
        for cat in self._repo.all_categories():
            btn = ctk.CTkButton(
                chip_scroll, text=cat, width=90, height=26,
                fg_color="transparent", border_width=1,
                font=ctk.CTkFont(size=11),
                command=lambda c=cat: self._toggle_category(c),
            )
            btn.pack(side="left", padx=3)
            self._category_buttons[cat] = btn

    def _build_body(
        self,
        player: AudioPlayer,
        get_client: Callable[[], Optional[GeminiTTSClient]],
        on_use_voice: Callable[[Voice], None],
    ) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=20, pady=(10, 20))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        table_frame = ctk.CTkFrame(body, corner_radius=10)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Voice.Treeview", background="#2b2b2b", fieldbackground="#2b2b2b",
            foreground="white", rowheight=28, borderwidth=0,
        )
        style.configure(
            "Voice.Treeview.Heading", background="#1f1f1f", foreground="white",
            borderwidth=0, font=("Segoe UI", 10, "bold"),
        )
        style.map("Voice.Treeview", background=[("selected", "#3a7ebf")])

        self._tree = ttk.Treeview(
            table_frame,
            columns=[c[0] for c in COLUMNS],
            show="headings",
            style="Voice.Treeview",
        )
        for col_id, heading, width in COLUMNS:
            self._tree.heading(col_id, text=heading)
            self._tree.column(col_id, width=width, anchor="w")
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        vsb.grid(row=0, column=1, sticky="ns", pady=10)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.bind("<<TreeviewSelect>>", self._on_row_selected)
        self._tree.bind("<Double-1>", self._on_row_double_click)

        self._detail_panel = VoiceDetailPanel(
            body, player, get_client, on_use_voice, self._toggle_favorite
        )
        self._detail_panel.grid(row=0, column=1, sticky="ns")

    # ------------------------------------------------------------------ #
    def _toggle_category(self, category: str) -> None:
        if category in self._selected_categories:
            self._selected_categories.discard(category)
            self._category_buttons[category].configure(fg_color="transparent")
        else:
            self._selected_categories.add(category)
            self._category_buttons[category].configure(fg_color=("gray75", "gray30"))
        self.refresh()

    def _on_fav_toggle(self) -> None:
        self._favorites_only = self._fav_var.get()
        self.refresh()

    def _toggle_favorite(self, voice_id: str) -> bool:
        new_state = self._repo.toggle_favorite(voice_id)
        self._on_favorite_changed()
        self.refresh(keep_selection=True)
        return new_state

    def _on_row_selected(self, _event=None) -> None:
        selection = self._tree.selection()
        if not selection:
            self._detail_panel.show_empty()
            return
        voice_id = selection[0]
        voice = self._repo.get(voice_id)
        if voice:
            self._detail_panel.show_voice(voice)

    def _on_row_double_click(self, _event=None) -> None:
        # Double click plays the preview immediately via the detail panel.
        self._on_row_selected()
        self._detail_panel._on_preview_clicked()  # noqa: SLF001 - intentional reuse

    # ------------------------------------------------------------------ #
    def refresh(self, keep_selection: bool = False) -> None:
        """Re-run the current search/filter/sort and repopulate the table."""
        selected = self._tree.selection() if keep_selection else ()
        for row in self._tree.get_children():
            self._tree.delete(row)

        voices = self._repo.query(
            search_text=self._search_var.get(),
            categories=list(self._selected_categories),
            sort_by=self._sort_var.get(),
            favorites_only=self._favorites_only,
        )
        for voice in voices:
            stars = "★" * voice.rating + "☆" * (5 - voice.rating)
            fav_icon = "⭐" if voice.favorite else ""
            self._tree.insert(
                "", "end", iid=voice.id,
                values=(
                    voice.id, voice.name, voice.gender, voice.style,
                    ", ".join(voice.category), voice.language,
                    voice.description, stars, fav_icon,
                ),
            )

        if selected and self._tree.exists(selected[0]):
            self._tree.selection_set(selected[0])
