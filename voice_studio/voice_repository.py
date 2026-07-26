"""
voice_repository.py
====================
Loads `voices.json` and exposes filter / search / sort / favorite operations.

This is the *only* place that reads voices.json. To add new voices later,
just edit voices.json (or drop in a replacement file) — no code changes,
no UI changes, per the "not hardcoded" requirement.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from config import VOICES_JSON_PATH
from api.models import Voice

logger = logging.getLogger("AI Voice Studio")

SORT_OPTIONS = ["A-Z", "Rating", "Newest", "Favorite"]


class VoiceRepository:
    """In-memory index over the voices defined in voices.json."""

    def __init__(self, favorites: Optional[list[str]] = None) -> None:
        self._voices: list[Voice] = []
        self._favorites: set[str] = set(favorites or [])
        self.reload()

    # ------------------------------------------------------------------ #
    def reload(self) -> None:
        """Re-read voices.json from disk (used at startup and on demand)."""
        if not VOICES_JSON_PATH.exists():
            logger.error("Không tìm thấy voices.json tại %s", VOICES_JSON_PATH)
            self._voices = []
            return
        try:
            with open(VOICES_JSON_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            entries = raw.get("voices", raw) if isinstance(raw, dict) else raw
            voices = [Voice.from_dict(v) for v in entries]
            for v in voices:
                v.favorite = v.id in self._favorites
            self._voices = voices
            logger.info("Đã tải %d voice từ voices.json", len(voices))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Lỗi đọc voices.json: %s", exc)
            self._voices = []

    def all(self) -> list[Voice]:
        return list(self._voices)

    def get(self, voice_id: str) -> Optional[Voice]:
        return next((v for v in self._voices if v.id == voice_id), None)

    def all_categories(self) -> list[str]:
        """Union of every category tag across all voices, sorted."""
        cats: set[str] = set()
        for v in self._voices:
            cats.update(v.category)
        return sorted(cats)

    # ------------------------------------------------------------------ #
    def query(
        self,
        search_text: str = "",
        categories: Optional[list[str]] = None,
        sort_by: str = "A-Z",
        favorites_only: bool = False,
    ) -> list[Voice]:
        """Return voices matching the given search/filter/sort criteria."""
        results = list(self._voices)

        if search_text:
            needle = search_text.lower().strip()
            results = [
                v for v in results
                if needle in v.name.lower()
                or needle in v.style.lower()
                or needle in v.description.lower()
                or any(needle in c.lower() for c in v.category)
            ]

        if categories:
            wanted = set(categories)
            results = [v for v in results if wanted.intersection(v.category)]

        if favorites_only:
            results = [v for v in results if v.id in self._favorites]

        if sort_by == "A-Z":
            results.sort(key=lambda v: v.name.lower())
        elif sort_by == "Rating":
            results.sort(key=lambda v: v.rating, reverse=True)
        elif sort_by == "Favorite":
            results.sort(key=lambda v: (v.id not in self._favorites, v.name.lower()))
        elif sort_by == "Newest":
            # voices.json order is treated as insertion/newest-last order
            results = list(reversed(results))

        return results

    # ------------------------------------------------------------------ #
    def toggle_favorite(self, voice_id: str) -> bool:
        """Toggle favorite state for `voice_id`. Returns new state."""
        if voice_id in self._favorites:
            self._favorites.discard(voice_id)
            new_state = False
        else:
            self._favorites.add(voice_id)
            new_state = True
        voice = self.get(voice_id)
        if voice:
            voice.favorite = new_state
        return new_state

    def favorites_list(self) -> list[str]:
        """Return favorite voice IDs (to persist into AppSettings)."""
        return sorted(self._favorites)
