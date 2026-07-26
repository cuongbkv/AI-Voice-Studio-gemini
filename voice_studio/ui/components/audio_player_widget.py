"""
ui/components/audio_player_widget.py
=====================================
A compact play/pause/stop/seek/volume/loop control bar backed by
`player.AudioPlayer`. Embedded in the Generate Voice page and reusable
anywhere audio needs to be played back.
"""

from __future__ import annotations

import logging
from typing import Optional

import customtkinter as ctk

from player import AudioPlayer

logger = logging.getLogger("AI Voice Studio")


class AudioPlayerWidget(ctk.CTkFrame):
    """Playback controls for a single loaded audio file."""

    def __init__(self, master, player: AudioPlayer) -> None:
        super().__init__(master, corner_radius=10)
        self._player = player
        self._current_file: Optional[str] = None
        self._duration_seconds: float = 0.0
        self._updating_slider = False

        self.grid_columnconfigure(2, weight=1)

        self._play_btn = ctk.CTkButton(
            self, text="▶", width=40, command=self._toggle_play
        )
        self._play_btn.grid(row=0, column=0, padx=(10, 4), pady=10)

        self._stop_btn = ctk.CTkButton(self, text="⏹", width=40, command=self._stop)
        self._stop_btn.grid(row=0, column=1, padx=4, pady=10)

        self._seek_slider = ctk.CTkSlider(
            self, from_=0, to=100, command=self._on_seek_drag
        )
        self._seek_slider.set(0)
        self._seek_slider.grid(row=0, column=2, sticky="ew", padx=8, pady=10)

        self._time_label = ctk.CTkLabel(self, text="0:00 / 0:00", width=90)
        self._time_label.grid(row=0, column=3, padx=4, pady=10)

        self._loop_var = ctk.BooleanVar(value=False)
        self._loop_check = ctk.CTkCheckBox(
            self, text="Loop", variable=self._loop_var, command=self._on_loop_toggle,
            width=20,
        )
        self._loop_check.grid(row=0, column=4, padx=8, pady=10)

        self._volume_slider = ctk.CTkSlider(
            self, from_=0, to=1, command=self._on_volume_change, width=100
        )
        self._volume_slider.set(1.0)
        self._volume_slider.grid(row=0, column=5, padx=(4, 10), pady=10)

    # ------------------------------------------------------------------ #
    def load_file(self, path: str, duration_seconds: float = 0.0) -> None:
        """Load (but do not auto-play) a new audio file."""
        self._current_file = path
        self._duration_seconds = duration_seconds
        self._seek_slider.configure(to=max(duration_seconds, 1))
        self._seek_slider.set(0)
        self._update_time_label(0)
        self._play_btn.configure(text="▶")

    def _toggle_play(self) -> None:
        if not self._current_file:
            return
        if self._player.is_playing():
            self._player.pause()
            self._play_btn.configure(text="▶")
        elif self._player.is_paused():
            self._player.resume()
            self._play_btn.configure(text="⏸")
        else:
            self._player.load_and_play(self._current_file)
            self._play_btn.configure(text="⏸")

    def _stop(self) -> None:
        self._player.stop()
        self._play_btn.configure(text="▶")
        self._seek_slider.set(0)
        self._update_time_label(0)

    def _on_seek_drag(self, value: float) -> None:
        if self._updating_slider or not self._current_file:
            return
        self._player.seek(float(value))
        self._update_time_label(float(value))

    def _on_loop_toggle(self) -> None:
        self._player.set_loop(self._loop_var.get())

    def _on_volume_change(self, value: float) -> None:
        self._player.set_volume(float(value))

    def _update_time_label(self, current: float) -> None:
        from utils import format_duration
        total = format_duration(self._duration_seconds)
        cur = format_duration(current)
        self._time_label.configure(text=f"{cur} / {total}")
