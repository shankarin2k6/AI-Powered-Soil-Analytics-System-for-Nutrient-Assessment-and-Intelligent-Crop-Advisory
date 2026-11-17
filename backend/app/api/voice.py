"""Read a result aloud. The frontend writes the sentences in the farmer's language (it already has the
translations) and this endpoint turns them into speech with Sarvam AI."""
import time
from collections import defaultdict, deque
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.config import settings
from app.ingestion.validate import IngestError
from app.models_db import Farmer
from app.services.auth import get_current_farmer
from app.services.storage import Storage, get_storage
from app.services.voice import Synthesizer, VoiceError, get_synthesizer, speak, voice_enabled

router = APIRouter(prefix="/voice", tags=["voice"])

_recent: dict[int, deque] = defaultdict(deque)       # farmer id -> times of recent requests (a simple per-farmer limit)
LIMIT, WINDOW = 12, 60.0


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=2500)
    language: Literal["en", "hi", "kn", "ta"]


@router.get("/status")
def status(_: Farmer = Depends(get_current_farmer)):
    return {"enabled": voice_enabled(), "model": settings.sarvam_model if voice_enabled() else None}


@router.post("/speak")
def speak_endpoint(body: SpeakIn, farmer: Farmer = Depends(get_current_farmer), synth: Synthesizer = Depends(get_synthesizer),
                   storage: Storage = Depends(get_storage)):
    if not voice_enabled():
        raise IngestError(503, "voice.unavailable", "Voice is not switched on.")
    text = " ".join(body.text.split())
    if len(text) > settings.voice_max_chars:
        raise IngestError(422, "voice.too_long", "The text is too long to read aloud.")
    now = time.monotonic()
    q = _recent[farmer.id]
    while q and now - q[0] > WINDOW:
        q.popleft()
    if len(q) >= LIMIT:
        raise IngestError(429, "voice.busy", "Too many requests. Wait a minute.")
    q.append(now)
    try:
        audio = speak(text, body.language, synth, storage)
    except VoiceError as e:
        raise IngestError(e.status, e.key, "The voice service could not read this aloud.")
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})
