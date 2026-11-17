# Voice (Sarvam AI) - read the result aloud

A **Listen** button on the analysis page reads the result aloud in the farmer's chosen language
(English, Hindi, Kannada or Tamil) using Sarvam AI's Bulbul text-to-speech.

## 1. Get a Sarvam API key

1. Open https://dashboard.sarvam.ai and sign up (email or Google). New accounts get free credits (₹100 at the time of writing).
2. In the dashboard, open the **API Keys** section and create a new key. Copy it straight away; it may not be shown again.
3. Open `backend/.env` (copy `backend/.env.example` if you do not have one) and add:

       SARVAM_API_KEY=paste-your-key-here

4. Restart the backend. The Listen button appears on the analysis page. With no key, the button stays hidden and nothing else changes.

Keep the key secret: never put it in the frontend, in Git, in a screenshot or in the report. If it leaks, delete it in the dashboard and create a new one.

## 2. How it works

    Browser (Listen) --text in chosen language--> our API /voice/speak --key--> Sarvam /text-to-speech
                     <---------- mp3 audio ---------      (cached on our server)  <---- base64 audio

- The frontend writes a short summary from the existing translations (health score, soil type, risk, what is missing,
  top fertiliser, top 3 crops, one-line disclaimer) and sends it to our server. Nothing new has to be translated by Sarvam.
- The key stays on the server. The browser never sees it.
- Audio is cached by (language, voice, text). Listening again to the same result costs no credit.
- Limits: 2,500 characters per request, 12 requests per farmer per minute.
- Settings (optional, in `.env`): `SARVAM_MODEL` (default `bulbul:v3`), `SARVAM_SPEAKER` (default `shubh`; the speaker must exist for the model).

## 3. Test status

- 10 new backend tests (cache, login required, limits, request shape, error mapping). They use a fake Sarvam, so they need no key.
- Browser check with a pretend Sarvam server: the button works in all four languages and sends the right text and language code.
- **Not tested against the real Sarvam service** (no key was available here). On first run, click Listen once in each language
  and check the voice. If Sarvam rejects a field (for example the speaker name), the backend log shows the status code.
