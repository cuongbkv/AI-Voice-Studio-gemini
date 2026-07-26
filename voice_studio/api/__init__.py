"""API provider package. Currently contains the Gemini TTS client.

Future providers (OpenAI TTS, ElevenLabs, Azure Speech) should be added as
sibling modules (e.g. `openai_tts.py`) that implement the same
`generate_speech(text, voice_id, params) -> bytes` contract as
`GeminiTTSClient`, so the UI layer never needs to change.
"""
