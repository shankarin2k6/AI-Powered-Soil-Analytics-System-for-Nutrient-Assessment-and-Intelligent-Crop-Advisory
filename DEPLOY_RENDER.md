# Deploy for free with no card: Render + Neon (one container)

Everything runs in **one Docker container** on Render's free web service: the API, the web app and a small front door (Caddy).
The database is a free **Neon** PostgreSQL. Photos are kept **inside that database** (`STORAGE_BACKEND=db`) because Render's
free disk is wiped whenever the app restarts.

> **Status: not yet run on Render.** What I checked in a sandbox: the API (with the ONNX model), the database photo storage and the
> web app all work together, and the API used about 306 MB and the web app about 96 MB. Caddy adds a little more, so the container
> needs roughly 430 MB of the 512 MB free limit. That is tight. I could not run Docker itself, so the first build on Render is the
> real test. If it shows "out of memory", see *If it runs out of memory* below.

## What you get, and the catches (checked 18 Nov 2026, confirm on each site)
| | |
|---|---|
| Render free web service | No card. 512 MB RAM, 0.1 CPU. **Sleeps after 15 minutes without visitors; the first visit then takes about a minute.** 750 free hours a month, enough for one app running all month. |
| Neon free database | No card. About 1 GB storage. It also pauses after 5 idle minutes and wakes on the next request (a second or two). |
| Photos | Stored in the database: about 0.5 MB per photo, so roughly 1,000+ photos. |
| Voice | Sarvam is paid. Leave `SARVAM_API_KEY` empty and the Listen button is hidden. |
| Slow | 0.1 CPU is slow: a photo analysis may take 10 to 30 seconds. |

## Step 1. Put the code on GitHub (with the small model files)
The server needs these four files in `backend/models/` **inside the repository** (the `.gitignore` already allows them):
`soil_cnn.onnx`, `soil_cnn_head.npz`, `fert_model.joblib`, `inference_config.json`.
```bash
cd ~/soil-analytics
ls backend/models                      # check all four are there
git add backend/models deploy DEPLOY_RENDER.md .dockerignore
git status                             # the .pt file should NOT be listed
git commit -m "Free deployment: ONNX model, database photo storage, Render setup"
git push
```

## Step 2. Create the database (Neon)
1. Go to <https://neon.com>, sign up with GitHub or Google (no card).
2. Create a project (region: Singapore or the closest one). Copy the **connection string** (it starts with `postgresql://`).
   Keep it secret: it contains the password.

## Step 3. Create the web service (Render)
1. Go to <https://render.com>, sign up with GitHub.
2. **New > Web Service** > choose your repository and the branch (`Team-C--milestone-3`).
3. Settings:
   - **Language / Runtime:** Docker
   - **Dockerfile Path:** `deploy/render/Dockerfile`
   - **Docker Build Context Directory:** `.` (the repository root)
   - **Instance Type:** Free
   - **Health Check Path:** `/api/v1/health`
4. **Environment variables** (Add each):

| Name | Value |
|---|---|
| `DATABASE_URL` | the Neon connection string |
| `SECRET_KEY` | a long random text: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ENVIRONMENT` | `production` |
| `COOKIE_SECURE` | `true` |
| `STORAGE_BACKEND` | `db` |
| `CORS_ORIGINS` | `https://YOUR-SERVICE-NAME.onrender.com` (you see the name after creating; edit it then) |
| `SARVAM_API_KEY` | leave out for now |

5. **Create Web Service.** The first build takes several minutes. When the log says the service is live, open
   `https://YOUR-SERVICE-NAME.onrender.com`, sign up and test: log in, add a field, upload a soil photo, run an analysis.
   Also open `/api/v1/analysis/status`: both models should say `true`.

## Step 4 (optional). Keep it awake for the demo
A free uptime monitor such as UptimeRobot can open your address every 5 minutes so the app does not sleep. Check its current free
terms. One always-awake service fits inside Render's 750 free hours.

## Updating later
Push to GitHub. Render rebuilds automatically (or use *Manual Deploy*). Database changes are applied by the app at start-up.

## If it runs out of memory (the service keeps restarting)
Render's log will mention "out of memory" or exit code 137. Options, easiest first:
1. Upgrade that one service to the smallest paid instance (needs a card, so only if you get one).
2. Host the web app separately (a second free service or a static host) so the API has the whole 512 MB. Ask me and I will make that
   version; it needs the web app to forward `/api` to the API so login cookies keep working.
3. Use the laptop demo (Path C in DEPLOY_FREE.md).

## Troubleshooting
- **Login works but you are logged out at once:** `COOKIE_SECURE` must be `true` and you must open the `https://` address.
- **"Network error" on the page:** `CORS_ORIGINS` must be exactly your `https://...onrender.com` address, with no slash at the end.
- **First page is very slow:** the service or the database was asleep. Wait a minute.
- **Photos missing after a restart:** check `STORAGE_BACKEND` is `db` (the `local` setting loses them).
