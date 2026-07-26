"""
ui/components/voice_detail_panel.py
====================================
Right-hand side panel shown when a voice is selected in the Voice Library.
Displays full metadata and offers a "Preview" button (generates a short
sample and plays it without saving to disk) plus a "Use this voice" button
that jumps to Generate Voice pre-selected.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

import customtkinter as ctk

from api.models import Voice, GenerationParams
from api.gemini import GeminiTTSClient, GeminiAPIError
from player import AudioPlayer

logger = logging.getLogger("AI Voice Studio")

PREVIEW_TEXT = "Xin chào, đây là giọng đọc mẫu."


class VoiceDetailPanel(ctk.CTkFrame):
    """Shows details for one Voice and lets the user preview or select it."""

    def __init__(
        self,
        master,
        player: AudioPlayer,
        get_client: Callable[[], Optional[GeminiTTSClient]],
        on_use_voice: Callable[[Voice], None],
        on_toggle_favorite: Callable[[str], bool],
    ) -> None:
        super().__init__(master, corner_radius=10, width=340)
        self.grid_propagate(False)
        self._player = player
        self._get_client = get_client
        self._on_use_voice = on_use_voice
        self._on_toggle_favorite = on_toggle_favorite
        self._voice: Optional[Voice] = None

        self._build_widgets()
        self.show_empty()

    def _build_widgets(self) -> None:
        self._icon_label = ctk.CTkLabel(self, text="🎙️", font=ctk.CTkFont(size=48))
        self._icon_label.pack(pady=(20, 4))

        self._name_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=20, weight="bold")
        )
        self._name_label.pack(pady=(0, 2))

        self._style_label = ctk.CTkLabel(self, text="", text_color="#8A8A8A")
        self._style_label.pack(pady=(0, 12))

        self._desc_label = ctk.CTkLabel(
            self, text="", wraplength=300, justify="left"
        )
        self._desc_label.pack(padx=16, pady=(0, 12), fill="x")

        self._info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._info_frame.pack(padx=16, pady=(0, 12), fill="x")
        self._info_labels: dict[str, ctk.CTkLabel] = {}
        for i, field_name in enumerate(
            ["Giới tính", "Pitch đề xuất", "Speed đề xuất", "Emotion đề xuất", "Ngôn ngữ"]
        ):
            key_lbl = ctk.CTkLabel(
                self._info_frame, text=f"{field_name}:", font=ctk.CTkFont(weight="bold")
            )
            key_lbl.grid(row=i, column=0, sticky="w", pady=2)
            val_lbl = ctk.CTkLabel(self._info_frame, text="-")
            val_lbl.grid(row=i, column=1, sticky="w", padx=(6, 0), pady=2)
            self._info_labels[field_name] = val_lbl

        self._tags_label = ctk.CTkLabel(
            self, text="", wraplength=300, justify="left", text_color="#5DA9F0"
        )
        self._tags_label.pack(padx=16, pady=(0, 12), fill="x")

        self._example_label = ctk.CTkLabel(
            self, text="", wraplength=300, justify="left", font=ctk.CTkFont(size=12, slant="italic")
        )
        self._example_label.pack(padx=16, pady=(0, 16), fill="x")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(padx=16, pady=(0, 16), fill="x")
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self._preview_btn = ctk.CTkButton(
            btn_frame, text="▶ Preview", command=self._on_preview_clicked
        )
        self._preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self._fav_btn = ctk.CTkButton(
            btn_frame, text="⭐ Favorite", command=self._on_favorite_clicked,
            fg_color="transparent", border_width=1,
        )
        self._fav_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self._use_btn = ctk.CTkButton(
            self, text="Dùng voice này để Generate →", command=self._on_use_clicked
        )
        self._use_btn.pack(padx=16, pady=(0, 20), fill="x")

        self._status_label = ctk.CTkLabel(self, text="", text_color="#8A8A8A")
        self._status_label.pack(padx=16, pady=(0, 10))

    # ------------------------------------------------------------------ #
    def show_empty(self) -> None:
        """Show placeholder state when no voice is selected."""
        self._voice = None
        self._name_label.configure(text="Chọn một voice")
        self._style_label.configure(text="")
        self._desc_label.configure(text="Click vào một dòng trong bảng để xem chi tiết.")
        self._tags_label.configure(text="")
        self._example_label.configure(text="")
        for lbl in self._info_labels.values():
            lbl.configure(text="-")
        self._preview_btn.configure(state="disabled")
        self._fav_btn.configure(state="disabled")
        self._use_btn.configure(state="disabled")

    def show_voice(self, voice: Voice) -> None:
        """Populate the panel with `voice`'s details."""
        self._voice = voice
        self._name_label.configure(text=voice.name)
        self._style_label.configure(text=f"{voice.style} • {', '.join(voice.category[:3])}")
        self._desc_label.configure(text=voice.description)
        self._info_labels["Giới tính"].configure(text=voice.gender)
        self._info_labels["Pitch đề xuất"].configure(text=voice.recommended_pitch)
        self._info_labels["Speed đề xuất"].configure(text=voice.recommended_speed)
        self._info_labels["Emotion đề xuất"].configure(text=voice.recommended_emotion)
        self._info_labels["Ngôn ngữ"].configure(text=voice.language)
        self._tags_label.configure(text="  ".join(f"#{t}" for t in voice.tags))
        self._example_label.configure(
            text=f"Ví dụ: {voice.example_usage}" if voice.example_usage else ""
        )
        self._fav_btn.configure(
            text="★ Đã thích" if voice.favorite else "⭐ Favorite",
            state="normal",
        )
        self._preview_btn.configure(state="normal")
        self._use_btn.configure(state="normal")
        self._status_label.configure(text="")

    # ------------------------------------------------------------------ #
    def _on_favorite_clicked(self) -> None:
        if not self._voice:
            return
        new_state = self._on_toggle_favorite(self._voice.id)
        self._voice.favorite = new_state
        self._fav_btn.configure(text="★ Đã thích" if new_state else "⭐ Favorite")

    def _on_use_clicked(self) -> None:
        if self._voice:
            self._on_use_voice(self._voice)

    def _on_preview_clicked(self) -> None:
        if not self._voice:
            return
        client = self._get_client()
        if client is None:
            self._status_label.configure(
                text="Vui lòng cấu hình API Key trong Settings.", text_color="#EF5350"
            )
            return

        self._preview_btn.configure(state="disabled", text="Đang tạo...")
        self._status_label.configure(text="Đang tạo giọng mẫu...", text_color="#8A8A8A")

        voice_id = self._voice.id
        thread = threading.Thread(
            target=self._generate_preview, args=(client, voice_id), daemon=True
        )
        thread.start()

    def _generate_preview(self, client: GeminiTTSClient, voice_id: str) -> None:
        """Runs on a background thread: generate a short preview and play it
        directly from memory (no file saved), as required."""
        import tempfile
        import os

        try:
            wav_bytes, _elapsed = client.generate_speech(
                PREVIEW_TEXT, voice_id, GenerationParams()
            )
            # Preview is not saved permanently: write to a temp file only so
            # pygame (which needs a path/file-like object) can play it, then
            # let the OS clean it up.
            tmp_path = os.path.join(tempfile.gettempdir(), f"_preview_{voice_id}.wav")
            with open(tmp_path, "wb") as f:
                f.write(wav_bytes)
            self._player.load_and_play(tmp_path)
            self.after(0, lambda: self._status_label.configure(
                text="Đang phát giọng mẫu...", text_color="#66BB6A"
            ))
        except GeminiAPIError as exc:
            logger.error("Lỗi preview voice %s: %s", voice_id, exc)
            self.after(0, lambda: self._status_label.configure(
                text=str(exc), text_color="#EF5350"
            ))
        finally:
            self.after(0, lambda: self._preview_btn.configure(
                state="normal", text="▶ Preview"
            ))
