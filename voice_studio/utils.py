"""
utils.py
========
Small stateless helper functions used across the app: text statistics,
filename generation, and ffmpeg-based audio format conversion.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("AI Voice Studio")

# Average speaking rate used to estimate duration before generation happens.
AVERAGE_WORDS_PER_MINUTE = 150


def count_characters(text: str) -> int:
    """Return the number of characters in `text`."""
    return len(text)


def count_words(text: str) -> int:
    """Return the number of whitespace-separated words in `text`."""
    return len(text.split())


def count_sentences(text: str) -> int:
    """Rough sentence count based on '.', '!', '?', and Vietnamese variants."""
    sentences = re.split(r"[.!?…]+", text)
    return len([s for s in sentences if s.strip()])


def estimate_duration_seconds(text: str, speed: float = 1.0) -> float:
    """Estimate spoken duration in seconds given a speaking speed multiplier."""
    words = max(count_words(text), 1)
    minutes = words / AVERAGE_WORDS_PER_MINUTE
    seconds = (minutes * 60) / max(speed, 0.1)
    return round(seconds, 1)


def format_duration(seconds: float) -> str:
    """Format seconds as m:ss for display."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def generate_output_filename(extension: str) -> str:
    """Generate a timestamped filename, e.g. 20260726_143210.wav."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}.{extension.lstrip('.')}"


def ffmpeg_available() -> bool:
    """Check whether ffmpeg is installed and reachable on PATH."""
    return shutil.which("ffmpeg") is not None


def convert_audio(
    source_wav_path: str,
    target_path: str,
    target_format: str,
) -> bool:
    """
    Convert a WAV file to mp3/flac/aac using ffmpeg.

    Args:
        source_wav_path: Path to the source .wav file.
        target_path: Desired output path (extension should match target_format).
        target_format: One of "mp3", "flac", "aac" ("wav" is a no-op, handled by caller).

    Returns:
        True on success, False otherwise (details are logged).
    """
    if not ffmpeg_available():
        logger.error("ffmpeg không được cài đặt hoặc không có trong PATH.")
        return False

    codec_map = {"mp3": "libmp3lame", "flac": "flac", "aac": "aac"}
    codec = codec_map.get(target_format)
    if codec is None:
        logger.error("Định dạng xuất không được hỗ trợ: %s", target_format)
        return False

    cmd = [
        "ffmpeg", "-y",
        "-i", source_wav_path,
        "-acodec", codec,
        target_path,
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, check=False
        )
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg quá thời gian chờ khi chuyển đổi %s", source_wav_path)
        return False

    if result.returncode != 0:
        logger.error("ffmpeg lỗi: %s", result.stderr[-500:])
        return False
    return True


def ensure_directory(path: str) -> None:
    """Create `path` (and parents) if it doesn't already exist."""
    Path(path).mkdir(parents=True, exist_ok=True)


def truncate_text(text: str, max_len: int = 60) -> str:
    """Truncate text for compact table/history display."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"
