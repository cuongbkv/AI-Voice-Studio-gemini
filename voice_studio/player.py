"""
player.py
=========
Integrated audio player used by the Generate Voice page and voice preview
buttons. Wraps `pygame.mixer` because it is lightweight, pure-Python-friendly,
and needs no native codec setup beyond what pygame ships with.

Limitations (documented rather than hidden):
    - Seeking mid-playback is best-effort: pygame's `mixer.music.play(start=...)`
      reliably supports seeking for OGG/MP3 but not all WAV encodings, so `seek()`
      stops and restarts playback from the requested position, which is a
      pragmatic tradeoff for a single-file desktop tool.
    - Looping is implemented via `loops=-1` passed to `play()`.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import pygame

logger = logging.getLogger("AI Voice Studio")


class AudioPlayer:
    """Small stateful wrapper around pygame.mixer.music for one active track."""

    def __init__(self) -> None:
        self._available: bool = True
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error as exc:
                # No audio device available (e.g. some servers/sandboxes, or a
                # machine with no sound hardware). Degrade gracefully instead
                # of crashing the whole app: playback controls become no-ops
                # and a warning is logged once here.
                logger.warning(
                    "Không thể khởi tạo thiết bị âm thanh (%s). "
                    "Tính năng phát âm thanh sẽ bị vô hiệu hoá.", exc
                )
                self._available = False
        self._current_path: Optional[str] = None
        self._is_paused: bool = False
        self._loop: bool = False
        self._volume: float = 1.0
        self._position_offset: float = 0.0  # seconds, for seek bookkeeping
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    def load_and_play(self, path: str, start_seconds: float = 0.0) -> None:
        """Load `path` and start playback from `start_seconds`."""
        if not self._available:
            logger.warning("Bỏ qua phát audio: không có thiết bị âm thanh.")
            return
        with self._lock:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self._volume)
                loops = -1 if self._loop else 0
                pygame.mixer.music.play(loops=loops, start=start_seconds)
                self._current_path = path
                self._position_offset = start_seconds
                self._is_paused = False
                logger.info("Đang phát: %s", path)
            except pygame.error as exc:
                logger.error("Không thể phát file audio %s: %s", path, exc)

    def pause(self) -> None:
        """Pause playback if currently playing."""
        if not self._available:
            return
        with self._lock:
            if self._current_path and not self._is_paused:
                pygame.mixer.music.pause()
                self._is_paused = True

    def resume(self) -> None:
        """Resume playback if currently paused."""
        if not self._available:
            return
        with self._lock:
            if self._current_path and self._is_paused:
                pygame.mixer.music.unpause()
                self._is_paused = False

    def stop(self) -> None:
        """Stop playback entirely."""
        if not self._available:
            return
        with self._lock:
            pygame.mixer.music.stop()
            self._current_path = None
            self._is_paused = False
            self._position_offset = 0.0

    def seek(self, seconds: float) -> None:
        """Best-effort seek: restarts playback of the current file at `seconds`."""
        if self._current_path:
            self.load_and_play(self._current_path, start_seconds=seconds)

    def set_volume(self, volume: float) -> None:
        """Set playback volume, 0.0 - 1.0."""
        self._volume = max(0.0, min(1.0, volume))
        if self._available:
            pygame.mixer.music.set_volume(self._volume)

    def set_loop(self, loop: bool) -> None:
        """Enable/disable looping for the *next* play() call."""
        self._loop = loop

    def is_playing(self) -> bool:
        """Whether audio is actively playing (not paused, not stopped)."""
        if not self._available:
            return False
        return pygame.mixer.music.get_busy() and not self._is_paused

    def is_paused(self) -> bool:
        return self._is_paused

    def current_path(self) -> Optional[str]:
        return self._current_path
