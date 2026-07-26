"""
cache.py
========
Simple content-addressed disk cache so identical (text, voice, params)
combinations don't re-trigger a Gemini API call.

Cache layout:
    cache/
        index.json          -> {hash: {"path": ..., "created": ...}}
        <hash>.wav          -> the cached WAV audio

The cache stores the *raw* WAV (before user-chosen format conversion), since
format conversion is cheap and local, while the API call is the expensive part.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import CACHE_DIR
from api.models import GenerationParams

logger = logging.getLogger("AI Voice Studio")

_INDEX_PATH = CACHE_DIR / "index.json"


@dataclass
class CacheEntry:
    path: str
    created: str


class GenerationCache:
    """Content-addressed cache keyed by a hash of (text, voice_id, params)."""

    def __init__(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, CacheEntry] = self._load_index()

    # ------------------------------------------------------------------ #
    @staticmethod
    def make_key(text: str, voice_id: str, params: GenerationParams) -> str:
        """Build a stable hash key for a given generation request."""
        payload = json.dumps(
            {"text": text, "voice_id": voice_id, "params": asdict(params)},
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def get(self, key: str) -> Optional[str]:
        """Return the cached WAV path for `key`, or None if not cached / missing."""
        entry = self._index.get(key)
        if entry is None:
            return None
        if not Path(entry.path).exists():
            # Stale index entry (file was deleted manually)
            del self._index[key]
            self._save_index()
            return None
        return entry.path

    def put(self, key: str, wav_bytes: bytes) -> str:
        """Store `wav_bytes` under `key` and return the cache file path."""
        cache_path = CACHE_DIR / f"{key}.wav"
        with open(cache_path, "wb") as f:
            f.write(wav_bytes)
        self._index[key] = CacheEntry(
            path=str(cache_path), created=datetime.now().isoformat()
        )
        self._save_index()
        return str(cache_path)

    def clear(self) -> int:
        """Delete all cached files and the index. Returns count removed."""
        count = 0
        for entry in self._index.values():
            try:
                Path(entry.path).unlink(missing_ok=True)
                count += 1
            except OSError as exc:
                logger.warning("Không thể xoá file cache %s: %s", entry.path, exc)
        self._index.clear()
        self._save_index()
        return count

    # ------------------------------------------------------------------ #
    def _load_index(self) -> dict[str, CacheEntry]:
        if not _INDEX_PATH.exists():
            return {}
        try:
            with open(_INDEX_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return {k: CacheEntry(**v) for k, v in raw.items()}
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning("Cache index lỗi, sẽ tạo lại: %s", exc)
            return {}

    def _save_index(self) -> None:
        with open(_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self._index.items()},
                f, ensure_ascii=False, indent=2,
            )
