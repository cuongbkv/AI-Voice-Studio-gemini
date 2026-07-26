"""
api/models.py
=============
Plain data structures shared between the API layer and the UI layer.

Keeping these separate from provider-specific code (gemini.py) means a future
OpenAI / ElevenLabs / Azure backend can reuse the exact same shapes, so the UI
never has to change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Voice:
    """A single TTS voice entry, as loaded from voices.json."""

    id: str
    name: str
    gender: str
    style: str
    category: list[str]
    description: str
    language: str = "vi"
    recommended_prompt: str = ""
    rating: int = 5
    favorite: bool = False
    recommended_pitch: str = "Trung bình"
    recommended_speed: str = "1.0x"
    recommended_emotion: str = "Trung tính"
    tags: list[str] = field(default_factory=list)
    example_usage: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Voice":
        """Build a Voice from a raw dict, tolerating missing optional keys."""
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def to_dict(self) -> dict:
        """Serialize back to a plain dict (for saving favorites, etc.)."""
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender,
            "style": self.style,
            "category": self.category,
            "description": self.description,
            "language": self.language,
            "recommended_prompt": self.recommended_prompt,
            "rating": self.rating,
            "favorite": self.favorite,
            "recommended_pitch": self.recommended_pitch,
            "recommended_speed": self.recommended_speed,
            "recommended_emotion": self.recommended_emotion,
            "tags": self.tags,
            "example_usage": self.example_usage,
        }


@dataclass
class GenerationParams:
    """User-adjustable voice parameters for one generation request.

    Not every provider supports every field. Fields unsupported by the current
    provider are simply ignored by that provider's client, but are still saved
    so they can be reused once a provider that supports them is added.
    """

    speed: float = 1.0          # 0.5 - 2.0
    pitch: float = 0.0          # -20 - +20 semitone-ish scale
    volume: float = 1.0         # 0.0 - 2.0 (gain multiplier)
    emotion: str = "Trung tính"
    expressiveness: float = 0.5     # 0.0 - 1.0
    pause_strength: float = 0.5     # 0.0 - 1.0
    randomness: float = 0.3         # 0.0 - 1.0 (a.k.a temperature)
    stability: float = 0.7          # 0.0 - 1.0


@dataclass
class GenerationRequest:
    """Everything needed to run one TTS generation."""

    text: str
    voice_id: str
    params: GenerationParams
    output_format: str = "wav"
    output_folder: str = ""


@dataclass
class GenerationResult:
    """Result of a completed generation."""

    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    api_time_seconds: float = 0.0
    from_cache: bool = False


@dataclass
class HistoryEntry:
    """One row in History page / history.json."""

    date: str
    voice_id: str
    voice_name: str
    prompt_template: str
    text: str
    duration_seconds: float
    output_path: str
    api_time_seconds: float

    @classmethod
    def now(
        cls,
        voice_id: str,
        voice_name: str,
        prompt_template: str,
        text: str,
        duration_seconds: float,
        output_path: str,
        api_time_seconds: float,
    ) -> "HistoryEntry":
        return cls(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            voice_id=voice_id,
            voice_name=voice_name,
            prompt_template=prompt_template,
            text=text,
            duration_seconds=duration_seconds,
            output_path=output_path,
            api_time_seconds=api_time_seconds,
        )
