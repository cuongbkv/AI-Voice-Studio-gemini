"""
history_repository.py
======================
Persists and retrieves generation history (history.json), used by the
History page and the Dashboard's "recent activity" panel.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict

from config import HISTORY_JSON_PATH
from api.models import HistoryEntry

logger = logging.getLogger("AI Voice Studio")

MAX_HISTORY_ENTRIES = 1000


class HistoryRepository:
    """Simple JSON-backed list of HistoryEntry, newest first."""

    def __init__(self) -> None:
        self._entries: list[HistoryEntry] = self._load()

    def _load(self) -> list[HistoryEntry]:
        if not HISTORY_JSON_PATH.exists():
            return []
        try:
            with open(HISTORY_JSON_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return [HistoryEntry(**item) for item in raw]
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning("Không thể đọc history.json: %s", exc)
            return []

    def _save(self) -> None:
        try:
            with open(HISTORY_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(e) for e in self._entries], f,
                    ensure_ascii=False, indent=2,
                )
        except OSError as exc:
            logger.error("Không thể lưu history.json: %s", exc)

    def add(self, entry: HistoryEntry) -> None:
        """Add a new entry at the top and persist to disk."""
        self._entries.insert(0, entry)
        self._entries = self._entries[:MAX_HISTORY_ENTRIES]
        self._save()

    def all(self) -> list[HistoryEntry]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries = []
        self._save()
