"""Text-to-speech through Sarvam AI (Bulbul). The API key stays on the server; the browser only ever talks to our API.

Audio is cached by a hash of (language, voice, text), so listening to the same result again costs nothing.
"""
import base64
import hashlib
import logging
from typing import Protocol

import httpx

from app.config import settings
from app.services.storage import Storage

log = logging.getLogger("uvicorn.error")

# Our language codes -> Sarvam's BCP-47 codes
LANGUAGES = {"en": "en-IN", "hi": "hi-IN", "kn": "kn-IN", "ta": "ta-IN"}


class VoiceError(Exception):
    """`key` is a message key the frontend can translate."""

    def __init__(self, key: str, status: int = 502):
        super().__init__(key)
        self.key, self.status = key, status


class Synthesizer(Protocol):
    def synthesize(self, text: str, language: str) -> bytes: ...


class SarvamSynthesizer:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._transport = transport

    def synthesize(self, text: str, language: str) -> bytes:
        body = {"text": text, "language_code": LANGUAGES[language], "model": settings.sarvam_model,
                "speaker": settings.sarvam_speaker, "output_audio_codec": "mp3", "speech_sample_rate": 22050}
        try:
            with httpx.Client(timeout=30, transport=self._transport) as client:
                r = client.post(settings.sarvam_tts_url, json=body,
                                headers={"api-subscription-key": settings.sarvam_api_key})
        except httpx.HTTPError as e:
            log.error("Sarvam TTS: could not reach %s (%s: %s)", settings.sarvam_tts_url, type(e).__name__, e)
            raise VoiceError("voice.error")
        if r.status_code != 200:
            # the reason is for the developer's terminal, never shown to the farmer (and never includes the key)
            log.error("Sarvam TTS answered %s: %s", r.status_code, r.text[:300])
        if r.status_code == 429:
            raise VoiceError("voice.busy", 429)
        if r.status_code in (401, 403):
            raise VoiceError("voice.error")                      # wrong key or no credit: the farmer cannot fix it
        if r.status_code != 200:
            raise VoiceError("voice.error")
        audios = r.json().get("audios") or []
        if not audios:
            raise VoiceError("voice.error")
        return base64.b64decode(audios[0])


def voice_enabled() -> bool:
    return bool(settings.sarvam_api_key)


def get_synthesizer() -> Synthesizer:
    """FastAPI dependency (tests override it)."""
    return SarvamSynthesizer()


def speak(text: str, language: str, synth: Synthesizer, storage: Storage) -> bytes:
    voice = f"{settings.sarvam_model}/{settings.sarvam_speaker}"
    digest = hashlib.sha256(f"{language}|{voice}|{text}".encode("utf-8")).hexdigest()
    key = f"voice/{digest[:2]}/{digest}.mp3"
    if storage.exists(key):
        return storage.read(key)
    audio = synth.synthesize(text, language)
    storage.save(key, audio)
    return audio
