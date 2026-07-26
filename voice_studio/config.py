"""
config.py
=========
Centralized configuration for AI Voice Studio.

This module owns:
    - Static path constants (base dir, voices.json, settings.json, cache, output, logs)
    - The `AppSettings` dataclass which represents everything the user can configure
    - Loading / saving of settings.json (persisted user configuration)

No other module should hardcode a path or read/write settings.json directly.
Everything goes through `AppSettings.load()` / `settings.save()`.
"""

from __future__ import annotations

import json
import os
import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Static paths (all relative to this file, so the app can run from anywhere)
# --------------------------------------------------------------------------- #
BASE_DIR: Path = Path(__file__).resolve().parent
VOICES_JSON_PATH: Path = BASE_DIR / "voices.json"
SETTINGS_JSON_PATH: Path = BASE_DIR / "settings.json"
HISTORY_JSON_PATH: Path = BASE_DIR / "history.json"
DEFAULT_OUTPUT_DIR: Path = BASE_DIR / "output"
CACHE_DIR: Path = BASE_DIR / "cache"
LOG_DIR: Path = BASE_DIR / "logs_dir"

APP_NAME: str = "AI Voice Studio"
APP_VERSION: str = "1.0.0"
WINDOW_SIZE: str = "1400x900"

# Gemini TTS model options exposed in Settings
GEMINI_TTS_MODELS: list[str] = [
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
]

# Supported export formats
SUPPORTED_FORMATS: list[str] = ["wav", "mp3", "flac", "aac"]

THEMES: list[str] = ["Dark", "Light"]


@dataclass
class AppSettings:
    """
    Persisted user settings (stored as settings.json).

    Attributes:
        api_keys: List of Google Gemini API keys (for failover rotation).
        api_key: Legacy single Google Gemini API key (kept for compatibility).
        model: Which Gemini TTS model to use.
        output_folder: Where generated audio files are written.
        theme: "Dark" or "Light".
        auto_update_voice_list: Whether to re-read voices.json on every launch
            (kept True by default since voices.json is designed to be hot-swappable).
        favorites: List of favorite voice IDs.
        default_format: Default export format.
        window_geometry: Last window size/position (optional, best effort).
    """

    api_keys: list[str] = field(default_factory=list)
    api_key: str = ""
    model: str = GEMINI_TTS_MODELS[0]
    output_folder: str = str(DEFAULT_OUTPUT_DIR)
    theme: str = "Dark"
    auto_update_voice_list: bool = True
    favorites: list[str] = field(default_factory=list)
    default_format: str = "wav"
    window_geometry: str = WINDOW_SIZE

    # ------------------------------------------------------------------ #
    @classmethod
    def load(cls) -> "AppSettings":
        """Load settings from settings.json, creating defaults if missing/corrupt."""
        if not SETTINGS_JSON_PATH.exists():
            settings = cls()
            settings.save()
            return settings

        try:
            with open(SETTINGS_JSON_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Only keep known fields so old/corrupt keys don't break the app
            known_fields = {k: raw[k] for k in cls.__dataclass_fields__ if k in raw}
            settings = cls(**known_fields)

            # Migration: if api_keys is empty but api_key (str) is present, migrate it
            if not settings.api_keys and settings.api_key:
                settings.api_keys = [settings.api_key.strip()]

            # Clean and deduplicate keys while preserving order
            clean_keys: list[str] = []
            for k in settings.api_keys:
                k_clean = str(k).strip()
                if k_clean and k_clean not in clean_keys:
                    clean_keys.append(k_clean)
            settings.api_keys = clean_keys

            # Keep legacy api_key synced with first key
            if settings.api_keys:
                settings.api_key = settings.api_keys[0]

            return settings
        except (json.JSONDecodeError, OSError) as exc:
            logging.getLogger(APP_NAME).warning(
                "Could not read settings.json (%s). Falling back to defaults.", exc
            )
            return cls()

    def get_api_keys(self) -> list[str]:
        """Return non-empty configured API keys, or fallback to environment variable."""
        keys = [k.strip() for k in self.api_keys if k and k.strip()]
        if not keys and self.api_key.strip():
            keys = [self.api_key.strip()]
        if not keys:
            env_key = get_env_api_key().strip()
            if env_key:
                keys = [env_key]
        return keys

    def save(self) -> None:
        """Persist current settings to settings.json."""
        # Ensure api_keys are clean
        clean_keys: list[str] = []
        for k in self.api_keys:
            k_clean = str(k).strip()
            if k_clean and k_clean not in clean_keys:
                clean_keys.append(k_clean)
        self.api_keys = clean_keys
        if self.api_keys:
            self.api_key = self.api_keys[0]

        SETTINGS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    def ensure_dirs(self) -> None:
        """Make sure output/cache/log directories exist."""
        Path(self.output_folder).mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_env_api_key() -> str:
    """Fallback: allow API key via environment variable GEMINI_API_KEY."""
    return os.environ.get("GEMINI_API_KEY", "")
