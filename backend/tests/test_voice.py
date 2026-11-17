"""Voice: the Sarvam call is faked, so no key and no internet are needed."""
import base64
import json

import httpx
import pytest

from app.config import settings
from app.main import app
from app.services import voice
from app.services.voice import SarvamSynthesizer, VoiceError, get_synthesizer

AUDIO = b"ID3-fake-mp3-bytes"


class Fake:
    def __init__(self):
        self.calls = []

    def synthesize(self, text, language):
        self.calls.append((text, language))
        return AUDIO


@pytest.fixture(autouse=True)
def _reset():
    from app.api import voice as voice_api
    voice_api._recent.clear()
    yield
    app.dependency_overrides.pop(get_synthesizer, None)


@pytest.fixture()
def fake(monkeypatch):
    f = Fake()
    monkeypatch.setattr(settings, "sarvam_api_key", "test-key")
    app.dependency_overrides[get_synthesizer] = lambda: f
    return f


def test_status_reflects_the_key(client, monkeypatch):
    monkeypatch.setattr(settings, "sarvam_api_key", "")
    assert client.get("/api/v1/voice/status").json()["enabled"] is False
    monkeypatch.setattr(settings, "sarvam_api_key", "k")
    assert client.get("/api/v1/voice/status").json()["enabled"] is True


def test_speak_returns_audio_and_caches_it(client, fake):
    body = {"text": "Your soil is healthy.", "language": "ta"}
    r = client.post("/api/v1/voice/speak", json=body)
    assert r.status_code == 200 and r.content == AUDIO and r.headers["content-type"] == "audio/mpeg"
    assert client.post("/api/v1/voice/speak", json=body).content == AUDIO
    assert len(fake.calls) == 1                                   # the second request came from the cache
    client.post("/api/v1/voice/speak", json={**body, "language": "hi"})
    assert len(fake.calls) == 2                                   # another language is a different audio


def test_needs_login_key_and_valid_input(client, anonymous, fake, monkeypatch):
    assert anonymous.post("/api/v1/voice/speak", json={"text": "x", "language": "en"}).status_code == 401
    assert client.post("/api/v1/voice/speak", json={"text": "", "language": "en"}).status_code == 422
    assert client.post("/api/v1/voice/speak", json={"text": "x", "language": "fr"}).status_code == 422
    assert client.post("/api/v1/voice/speak", json={"text": "x" * 2501, "language": "en"}).status_code == 422
    monkeypatch.setattr(settings, "sarvam_api_key", "")
    r = client.post("/api/v1/voice/speak", json={"text": "x", "language": "en"})
    assert r.status_code == 503 and r.json()["message_key"] == "voice.unavailable"


def test_per_farmer_limit(client, fake):
    codes = [client.post("/api/v1/voice/speak", json={"text": f"line {i}", "language": "en"}).status_code for i in range(14)]
    assert codes[:12] == [200] * 12 and codes[12:] == [429, 429]


def test_sarvam_request_and_response_shape(monkeypatch):
    monkeypatch.setattr(settings, "sarvam_api_key", "secret-key")
    seen = {}

    def handler(request: httpx.Request):
        seen["headers"], seen["body"] = request.headers, json.loads(request.content)
        return httpx.Response(200, json={"request_id": "r", "audios": [base64.b64encode(AUDIO).decode()]})

    out = SarvamSynthesizer(httpx.MockTransport(handler)).synthesize("வணக்கம்", "ta")
    assert out == AUDIO
    assert seen["headers"]["api-subscription-key"] == "secret-key"
    assert seen["body"]["language_code"] == "ta-IN" and seen["body"]["text"] == "வணக்கம்"
    assert seen["body"]["model"] == settings.sarvam_model and seen["body"]["speaker"] == settings.sarvam_speaker


@pytest.mark.parametrize("status,key", [(429, "voice.busy"), (401, "voice.error"), (500, "voice.error"), (200, "voice.error")])
def test_sarvam_errors_become_message_keys(status, key):
    payload = {"audios": []} if status == 200 else {}
    synth = SarvamSynthesizer(httpx.MockTransport(lambda r: httpx.Response(status, json=payload)))
    with pytest.raises(VoiceError) as e:
        synth.synthesize("x", "en")
    assert e.value.key == key


def test_error_reaches_the_client_as_a_key(client, monkeypatch):
    monkeypatch.setattr(settings, "sarvam_api_key", "k")
    app.dependency_overrides[get_synthesizer] = lambda: SarvamSynthesizer(httpx.MockTransport(lambda r: httpx.Response(500)))
    r = client.post("/api/v1/voice/speak", json={"text": "hello", "language": "en"})
    assert r.status_code == 502 and r.json()["message_key"] == "voice.error"
