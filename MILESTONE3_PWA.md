# Installable app and offline use (PWA)

## What the farmer gets
- **Install**: Chrome on Android shows an "Install app" bar; on iPhone it shows how to use Share > Add to Home Screen. The app then opens full screen with its own icon.
- **Offline**: pages and results the farmer opened before still open without a signal, with a banner saying so. New photos, lab tests and voice need internet.
- **Privacy**: saved results are deleted on logout, on login and when the session expires, so the next person on a shared phone sees nothing.

## How to test (the service worker only runs in the production build)
    cd frontend
    npm run build
    npm start                      # http://localhost:3000

1. Log in and open a result, History and Home once (this saves them).
2. Chrome DevTools > Application > Service Workers: it should say "activated and running".
3. DevTools > Network > tick "Offline" and reload. The saved pages and results still open and the offline banner shows.
4. Log out: Application > Cache Storage no longer lists `soil-data-v1`.
5. For install on a real phone the site must be served over **HTTPS** (localhost is the only exception). This is part of the deployment step.

## Notes
- Service worker: `frontend/public/sw.js`. Change `VERSION` in it whenever you change the file.
- Saved: app files and pages; read-only API results (profile, fields, analyses, history, trend). Never saved: uploads, login, logout, voice audio.
- A page never opened before, while offline, shows `offline.html` (English, Hindi, Kannada, Tamil).
