"""
api/gemini.py
=============
Thin client around Google's Gemini TTS REST endpoint.

Design goals:
    - No UI code in here at all. This module only knows how to turn
      (text, voice_id, GenerationParams) into raw PCM/WAV bytes.
    - Every network call goes through `_post_with_retry` so timeout /
      rate-limit / quota / network errors are handled in exactly one place.
    - Swappable: a future `openai_tts.py` or `elevenlabs.py` module can expose
      the same `generate_speech()` signature and the rest of the app won't
      need to change.

Gemini TTS reference behaviour (as of the 2.5 preview TTS models):
    POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=API_KEY
    body.generationConfig.responseModalities = ["AUDIO"]
    body.generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName = <voice id>
    Response audio comes back as base64 PCM (16-bit signed LE, mono, 24000 Hz)
    inside candidates[0].content.parts[0].inlineData.data
"""

from __future__ import annotations

import base64
import time
import wave
import io
import logging
from dataclasses import dataclass

import requests

from api.models import GenerationParams

logger = logging.getLogger("AI Voice Studio")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
PCM_SAMPLE_RATE = 24000
PCM_SAMPLE_WIDTH = 2  # bytes (16-bit)
PCM_CHANNELS = 1

DEFAULT_TIMEOUT_SECONDS = 60
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0


class GeminiAPIError(Exception):
    """Base class for all Gemini TTS errors surfaced to the UI."""


class GeminiTimeoutError(GeminiAPIError):
    """Raised when the request timed out."""


class GeminiNetworkError(GeminiAPIError):
    """Raised on DNS / connection failures."""


class GeminiRateLimitError(GeminiAPIError):
    """Raised on HTTP 429."""


class GeminiQuotaError(GeminiAPIError):
    """Raised when the account has exhausted its quota (HTTP 403 quota reason)."""


class GeminiAuthError(GeminiAPIError):
    """Raised on HTTP 401/403 that are not quota related (bad API key)."""


@dataclass
class TTSStyleHint:
    """Translates GenerationParams into a short natural-language style prefix.

    Gemini's TTS models are steered by natural language instructions embedded
    in the prompt rather than raw numeric sliders, so we translate the sliders
    the user set in the UI into a short style instruction prepended to the
    text. This keeps the UI provider-agnostic (sliders are generic) while
    still giving Gemini something concrete to act on.
    """

    params: GenerationParams

    def as_instruction(self) -> str:
        speed_word = (
            "rất chậm" if self.params.speed < 0.75 else
            "chậm" if self.params.speed < 0.95 else
            "nhanh" if self.params.speed > 1.3 else
            "hơi nhanh" if self.params.speed > 1.05 else
            "tốc độ bình thường"
        )
        expressiveness_word = (
            "rất biểu cảm, giàu cảm xúc" if self.params.expressiveness > 0.7
            else "khá biểu cảm" if self.params.expressiveness > 0.4
            else "trầm tĩnh, ít biểu cảm"
        )
        pause_word = (
            "ngắt nghỉ rõ ràng giữa các câu" if self.params.pause_strength > 0.6
            else "ngắt nghỉ tự nhiên"
        )
        return (
            f"Hãy đọc với tông giọng '{self.params.emotion}', {speed_word}, "
            f"{expressiveness_word}, {pause_word}. "
            f"Nội dung cần đọc:"
        )


class GeminiTTSClient:
    """Client for Google Gemini's text-to-speech generateContent endpoint.
    Supports multi-key failover rotation when rate limits or quotas are hit.
    """

    def __init__(self, api_keys: list[str] | str, model: str) -> None:
        """
        Args:
            api_keys: Single API key string or list of API keys for failover.
            model: One of config.GEMINI_TTS_MODELS.
        """
        if isinstance(api_keys, str):
            api_keys = [api_keys] if api_keys.strip() else []
        self.api_keys: list[str] = [k.strip() for k in api_keys if k and k.strip()]
        self.limited_keys: set[str] = set()
        self.model = model
        self._session = requests.Session()

    @property
    def api_key(self) -> str:
        """Returns the currently active API key, or first configured key."""
        active = self.get_active_key()
        if active:
            return active
        return self.api_keys[0] if self.api_keys else ""

    def get_active_key(self) -> str | None:
        """Return the first API key that is not marked as limited."""
        for k in self.api_keys:
            if k not in self.limited_keys:
                return k
        return None

    def mark_key_limited(self, key: str, reason: str = "") -> None:
        """Mark a specific key as rate-limited/exhausted."""
        self.limited_keys.add(key)
        masked = f"...{key[-6:]}" if len(key) >= 6 else key
        logger.warning("API Key [%s] đã bị đánh dấu limit/quota: %s", masked, reason)

    def reset_key_limits(self) -> None:
        """Reset limited status for all configured keys."""
        self.limited_keys.clear()
        logger.info("Đã reset trạng thái limit của tất cả API Key.")

    def get_key_statuses(self) -> list[dict[str, str]]:
        """Return list of dicts describing status of each configured key."""
        statuses = []
        for k in self.api_keys:
            masked = f"...{k[-6:]}" if len(k) >= 6 else k
            status = "limited" if k in self.limited_keys else "active"
            statuses.append({"key": k, "masked": masked, "status": status})
        return statuses

    # ------------------------------------------------------------------ #
    def generate_speech(
        self,
        text: str,
        voice_id: str,
        params: GenerationParams,
    ) -> tuple[bytes, float]:
        """Generate speech audio for `text` using `voice_id`.
        Automatically fails over to next API key if current key hits rate/quota limit.

        Returns:
            (wav_bytes, api_time_seconds)

        Raises:
            GeminiAPIError subclasses on failure.
        """
        if not self.api_keys:
            raise GeminiAuthError("Chưa cấu hình Gemini API Key trong Settings.")

        instruction = TTSStyleHint(params).as_instruction()
        prompt_text = f"{instruction}\n{text}"
        body = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice_id}
                    }
                },
            },
        }

        start = time.time()
        last_exc: Exception | None = None

        while True:
            key = self.get_active_key()
            if not key:
                break

            masked_key = f"...{key[-6:]}" if len(key) >= 6 else key
            url = f"{GEMINI_API_BASE}/{self.model}:generateContent?key={key}"

            try:
                response_json = self._post_with_retry(url, body)
                elapsed = time.time() - start
                pcm_bytes = self._extract_pcm(response_json)
                wav_bytes = self._pcm_to_wav(pcm_bytes)
                return wav_bytes, elapsed
            except (GeminiRateLimitError, GeminiQuotaError, GeminiAuthError) as exc:
                last_exc = exc
                logger.warning(
                    "API Key [%s] bị lỗi (%s). Tích limit và chuyển key tiếp theo...",
                    masked_key, exc
                )
                self.mark_key_limited(key, str(exc))

        # All keys in list exhausted
        if last_exc:
            raise GeminiRateLimitError(
                f"Tất cả {len(self.api_keys)} API Key đều đã bị giới hạn (Limit/Quota). Lỗi cuối: {last_exc}"
            )
        raise GeminiRateLimitError(
            f"Tất cả {len(self.api_keys)} API Key đều đã bị giới hạn limit/quota."
        )

    # ------------------------------------------------------------------ #
    def _post_with_retry(self, url: str, body: dict) -> dict:
        """POST with retry/backoff, converting HTTP/network issues into
        the typed exceptions declared above."""
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._session.post(
                    url, json=body, timeout=DEFAULT_TIMEOUT_SECONDS
                )
            except requests.exceptions.Timeout as exc:
                last_exc = exc
                logger.warning("Gemini timeout (attempt %d/%d)", attempt, MAX_RETRIES)
            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
                logger.warning("Gemini network error (attempt %d/%d)", attempt, MAX_RETRIES)
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 429:
                    raise GeminiRateLimitError("Đã đạt giới hạn tốc độ (HTTP 429 Rate Limit).")
                elif resp.status_code in (401, 403):
                    text_lower = resp.text.lower()
                    if "quota" in text_lower:
                        raise GeminiQuotaError("Tài khoản đã hết quota Gemini API (HTTP 403 Quota).")
                    raise GeminiAuthError("API Key không hợp lệ hoặc không có quyền truy cập.")
                else:
                    last_exc = GeminiAPIError(
                        f"Gemini API trả về lỗi HTTP {resp.status_code}: {resp.text[:300]}"
                    )
                    logger.warning(
                        "Gemini HTTP %d (attempt %d/%d)", resp.status_code, attempt, MAX_RETRIES
                    )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        # Exhausted retries
        if isinstance(last_exc, requests.exceptions.Timeout):
            raise GeminiTimeoutError("Hết thời gian chờ phản hồi từ Gemini API.") from last_exc
        if isinstance(last_exc, requests.exceptions.ConnectionError):
            raise GeminiNetworkError("Không thể kết nối tới Gemini API (kiểm tra mạng).") from last_exc
        if isinstance(last_exc, GeminiAPIError):
            raise last_exc
        raise GeminiAPIError(f"Lỗi không xác định khi gọi Gemini API: {last_exc}")

    # ------------------------------------------------------------------ #
    @staticmethod
    def _extract_pcm(response_json: dict) -> bytes:
        """Pull base64 PCM audio bytes out of the generateContent response."""
        try:
            candidates = response_json["candidates"]
            parts = candidates[0]["content"]["parts"]
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
            raise KeyError("no inlineData part found")
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiAPIError(
                "Phản hồi từ Gemini API không chứa dữ liệu âm thanh hợp lệ."
            ) from exc

    @staticmethod
    def _pcm_to_wav(pcm_bytes: bytes) -> bytes:
        """Wrap raw 16-bit PCM mono 24kHz bytes in a proper WAV container."""
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(PCM_CHANNELS)
            wav_file.setsampwidth(PCM_SAMPLE_WIDTH)
            wav_file.setframerate(PCM_SAMPLE_RATE)
            wav_file.writeframes(pcm_bytes)
        return buffer.getvalue()

