# Soil Analytics: Milestone 1 (ingestion pipeline)

> Milestone 2 (ML analysis engine) is added: see [MILESTONE2.md](MILESTONE2.md).

Milestone 1 covers weeks 1 and 2 of the project plan: getting soil photos and lab values into the system,
checking them, preparing them, and saving them in PostgreSQL.

| Requirement in the plan | Where it is |
| --- | --- |
| Image upload (JPEG, PNG, direct camera capture) | `frontend/src/components/PhotoCapture.tsx` (phone: native camera; laptop: webcam via `CameraCapture.tsx`), `backend/app/api/images.py` |
| Login and signup (mobile number + password) | `backend/app/api/auth.py`, `backend/app/services/auth.py`, `frontend/src/components/AuthForm.tsx`, `AppShell.tsx` |
| Server-side validation, resizing, format normalisation | `backend/app/ingestion/validate.py`, `preprocess.py`, `pipeline.py` |
| Structured lab-test forms (N, P, K, pH, organic matter, moisture) | `frontend/src/components/SoilTestForm.tsx`, `backend/app/api/soil_tests.py` |
| OpenCV preprocessing: colour correction, background removal | `backend/app/ingestion/preprocess.py` (`color_correct`, `remove_background`) |
| Feature-preserving augmentation for training | `backend/app/ingestion/augment.py`, `backend/scripts/augment_dataset.py` |
| Labelled soil dataset | done earlier (Kaggle soil images, in `ml/`) |
| PostgreSQL: soil records, images, analysis history per field | `backend/app/models_db/tables.py`, `backend/alembic/` |

## Run it

You need Python 3.11+, Node.js 20+ and PostgreSQL.

**1. Database** (choose one)

```bash
docker compose up -d          # easiest: starts PostgreSQL 16 with the right user and database
```

or install PostgreSQL yourself and run in `psql`:

```sql
CREATE USER soil WITH PASSWORD 'soil';
CREATE DATABASE soil OWNER soil;
```

**2. Backend**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate     Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env         # Linux/macOS: cp .env.example .env
alembic upgrade head           # creates / updates the tables (run again after every update)
uvicorn app.main:app --reload  # http://localhost:8000/docs
```

**3. Frontend**

```bash
cd frontend
copy .env.local.example .env.local    # Linux/macOS: cp ...
npm install
npm run dev                           # http://localhost:3000
```

**4. Tests**

```bash
cd backend
pytest                          # 82 tests, no PostgreSQL needed (they use SQLite)
```

Camera note: on a phone the camera button opens the back camera app directly. On a laptop or desktop it opens a
live webcam view (browsers ignore `capture` on desktop and would show a file picker). Browsers only allow camera
access on `https://` pages or on `localhost`, and ask the user for permission once.

Testing on a real phone before deployment: the login cookie is `SameSite=Lax`, so the frontend and the API must be
on the same host name or IP. Open the app through your computer's address (for example `http://192.168.1.5:3000`),
set `NEXT_PUBLIC_API_URL=http://192.168.1.5:8000` in `frontend/.env.local`, add `http://192.168.1.5:3000` to
`CORS_ORIGINS` in `backend/.env`, and add that host to `allowedDevOrigins` in `frontend/next.config.mjs`.
For the phone camera over http, use a tunnel such as `ngrok` (https) instead.

## Look and feel

- One stylesheet, `frontend/src/app/globals.css`. The base rules are the phone layout (bottom navigation bar, single
  column); the block at the end, `@media (min-width: 900px)`, is the laptop layout (top navigation bar, two columns,
  split login screen). Colours and fonts are variables at the top of the file.
- Fonts (Bricolage Grotesque and Hind) come from npm packages, so they work offline: run `npm install` after updating.
- Icons are in `components/Icon.tsx`; add a new one with a single entry. The home-page picture is `SoilProfile.tsx`.
- Animations are plain CSS (`@keyframes` at the end of `globals.css`) and are switched off automatically for people
  who set "reduce motion" on their device.
- All home-page text is in `frontend/src/messages/en.json` (`home.*` keys).

## Login

- Sign up with name, 10-digit Indian mobile number and password (8 to 128 characters). `+91`, spaces and dashes in
  the number are accepted.
- Passwords are stored as argon2 hashes. The session is a signed token (7 days) kept in an httpOnly cookie
  `soil_session`; the API also accepts `Authorization: Bearer <token>` for other clients.
- Every endpoint except `/auth/signup` and `/auth/login` needs a login. A farmer only sees their own fields, photos
  and tests (other people's ids return 404).
- Before deploying set `SECRET_KEY`, `ENVIRONMENT=production`, `COOKIE_SECURE=true` (see `backend/.env.example`).
- Not built yet: password reset (needs an SMS/OTP provider) and a limit on wrong-password attempts.
- Rows saved before login existed have no mobile number or password, so nobody can log in to them.

## How the pipeline works

```
phone photo --(browser shrinks it to 1600 px)--> POST /api/v1/fields/{id}/images
    validate (type, size, readable, EXIF rotation, minimum size)
      -> normalized.jpg   original colours, longest side 1600 px   <- what the models will use
      -> quality check    blur / brightness / resolution warnings (advice only, never blocks)
      -> corrected.jpg    white balance + contrast (OpenCV)
      -> foreground.png   background removed (GrabCut), skipped when the photo is all soil
    files saved through services/storage.py, one row saved in soil_images
```

Important design choices

- **The models get the normalized image, not the colour-corrected one.** The CNN was trained on unmodified colours,
  and soil colour separates red, yellow and black soils. The corrected and foreground versions are saved for
  display and experiments. Compare accuracy before switching the model to them.
- **Quality problems are warnings, not errors.** A farmer can still save a dark photo; the app tells them to retake it.
- **Quality thresholds are not tuned yet.** `BLUR_MIN`, `DARK_MEAN_MAX` and `BRIGHT_MEAN_MIN` at the top of
  `preprocess.py` are starting values tested on generated pictures only. Upload 15 to 20 real phone photos
  (good and bad) and adjust them.
- **One field per farmer for now.** After login the app uses the farmer's first field, or creates "My field"
  (`frontend/src/lib/session.ts`). Multiple fields later only changes that file and adds a field picker.

## API (all under `/api/v1`, live docs at `/docs`)

| Method and path | Purpose |
| --- | --- |
| `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | account and session |
| `GET /fields`, `POST /fields`, `GET /fields/{id}` | the signed-in farmer's fields |
| `POST /fields/{id}/images` (form field `file`) | upload a soil photo |
| `GET /fields/{id}/images`, `GET /images/{id}` | list / read image records |
| `GET /images/{id}/file?variant=normalized\|original\|corrected\|foreground` | the picture files |
| `POST /fields/{id}/soil-tests`, `GET /fields/{id}/soil-tests`, `GET /soil-tests/{id}` | lab values |
| `GET /fields/{id}/history` | photos, tests and (later) analyses, newest first |

Upload errors return `{"detail": "...", "message_key": "image.not_readable"}`. The frontend translates the key.
Quality warnings come back in `quality.warnings`, for example `["image.blurry"]`.

## Where Milestones 2 and 3 plug in

**Milestone 2 (analysis engine)**

1. Move the model code from `backend/ml_legacy/soil_api.py` into `backend/app/ml/` and put the model files in `backend/models/`.
2. Add `backend/app/api/analysis.py` (`POST /fields/{id}/analyze`): load the latest image and soil test, call the models
   on `normalized`, save the result as a row in `analyses`, return it. Then add one `include_router` line in `app/main.py`.
3. `history.py` and the `analyses` table already exist, so past results appear in `/history` automatically.
   Replace the placeholder card for `analysis` items in `frontend/src/app/history/page.tsx`.

**Milestone 3 (recommendations, PWA, languages, reports)**

- Rules and tables go in `backend/app/services/` and `backend/app/data/`.
- Languages: replace `frontend/src/lib/i18n.ts` with next-i18next and add `hi` and `kn` copies of
  `frontend/src/messages/en.json`. All screens already call `t("key")`, and the API's message keys use the same file.
- PWA: wrap `next.config.mjs` with the PWA plugin (a manifest and icons are already in `frontend/public/`).
- Image storage in the cloud: add an `S3Storage` class in `backend/app/services/storage.py` with the same three methods.

## Training augmentation

```bash
cd backend
python -m scripts.augment_dataset --src ../ml/data/train --dst ../ml/data/train_aug --copies 3
```

Only augment the training split. The augmentations avoid hue and saturation changes on purpose.

## Folder map

```
backend/app/config.py          settings from environment variables
backend/app/db.py              database connection
backend/app/models_db/         tables
backend/app/schemas/           request and response shapes
backend/app/api/               endpoints (one file per topic)
backend/app/ingestion/         validate -> preprocess -> pipeline, augment
backend/app/services/          storage, auth (later: recommendations, trends, PDF)
backend/alembic/               database migrations
frontend/src/app/              pages (home, login, signup, capture, soil-test, history)
frontend/src/components/       app shell (login gate), main nav, icons, soil picture, auth form, camera capture, lab form
frontend/src/lib/              api client, auth state, session, image shrinking, t()
```
