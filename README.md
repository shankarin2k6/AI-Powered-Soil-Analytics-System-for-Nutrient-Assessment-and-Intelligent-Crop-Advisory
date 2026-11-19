<div align="center">

<img src="docs/assets/m3-hero.svg" alt="Soil Analytics, Milestone 3: advisory, voice, offline PWA and deployment" width="100%"/>

# 🌱 AI-Powered Soil Analytics System
### Nutrient assessment and intelligent crop advisory for farmers
*Infosys Springboard Internship 7.0 · Team C*

<a href="https://ai-powered-soil-analytics-system-for.onrender.com"><img src="https://img.shields.io/badge/%F0%9F%9A%80%20Live%20demo-Open%20the%20app-16a34a?style=for-the-badge" alt="Open the live app"/></a>

> 💤 **First visit after a quiet period:** the free server sleeps when nobody is using it, so the page can take about a minute to wake up. After that it is fast.

> **A farmer uploads a soil photo and enters lab values. The app finds the soil type, scores soil health, ranks crops, gives a step-by-step fertiliser plan, and speaks the result in the farmer's own language, even with weak internet.**

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-16a34a?style=for-the-badge)
![ONNX](https://img.shields.io/badge/ONNX%20Runtime-005CED?style=for-the-badge&logo=onnx&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Render](https://img.shields.io/badge/Render-Free%20hosting-46E3B7?style=for-the-badge&logo=render&logoColor=black)
![Neon](https://img.shields.io/badge/Neon-Serverless%20Postgres-00E599?style=for-the-badge&logo=neon&logoColor=black)
![PWA](https://img.shields.io/badge/PWA-Offline%20ready-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)
![Tests](https://img.shields.io/badge/Backend%20tests-213%20passing-22c55e?style=for-the-badge)

<img src="docs/assets/divider.svg" alt="" width="100%"/>

**[🚀 Live demo](#-live-demo) · [✨ Features](#-features) · [🗺️ How it works](#️-how-it-works) · [🧭 Milestones](#-milestones) · [🚀 Quick start](#-quick-start) · [🔌 API](#-api) · [☁️ Deployment](#️-deployment) · [⚠️ Limits](#️-known-limitations)**

</div>

## 🚀 Live demo

| | |
| --- | --- |
| 🌐 **App** | **<https://ai-powered-soil-analytics-system-for.onrender.com>** |
| 📱 **On a phone** | Open the link in Chrome (Android) or Safari (iPhone) and install it: Chrome menu > *Install app*, or Safari Share > *Add to Home Screen* |
| 🔑 **Try it** | Sign up with any name, a phone number and a password, add a field, upload a soil photo and open the analysis |
| 🌍 **Languages** | Switch between English, हिन्दी, ಕನ್ನಡ and தமிழ் from the top bar |

> Hosted on free tiers (Render for the app, Neon for the database), so please use test data only.

## ✨ Features

| | Feature | What the farmer gets |
| :-: | --- | --- |
| 📷 | **Soil photo analysis** | Soil type from EfficientNet-B0, with a Grad-CAM heat map showing what the model looked at |
| 🧪 | **Health score** | Low / medium / high ratings for N, P, K, pH and organic matter, plus a 0 to 100 score |
| 🌾 | **Crop ranking** | Crops scored for this soil: 40% pH fit, 35% nutrient fit, 25% soil type |
| 📈 | **Health trend** | Improving, steady or declining, with a 90-day estimate (needs 3 or more tests over 14 days) |
| 🧑‍🌾 | **Fertiliser plan** | Step-by-step doses (DAP, urea, MOP, manure, lime) by growth stage, scaled to the field size |
| 📄 | **PDF report** | One-click printable report, including the plan, in all four languages |
| 🔊 | **Listen** | The result read aloud with Sarvam AI voices |
| 📲 | **Installable PWA** | Install from the browser, open saved records offline |
| 🌐 | **4 languages** | English, हिन्दी, ಕನ್ನಡ, தமிழ் on every page |
| 🚀 | **Production ready** | Docker, HTTPS, light ONNX model for small servers, photos in S3, Google Cloud or the database, backup script |

<img src="docs/assets/divider.svg" alt="" width="100%"/>

## 🗺️ How it works

<div align="center">
<img src="docs/assets/m3-flow.svg" alt="Animated Milestone 3 system flow" width="100%"/>
</div>

### 🔬 From soil to advice

```mermaid
flowchart LR
    A([📷 Soil photo]) --> B[EfficientNet-B0]
    B --> C{Confident?}
    C -- yes --> D[Soil type + Grad-CAM]
    C -- no --> E[Ask farmer to confirm or retake]
    F([🧪 Lab values]) --> G[Rating tables]
    G --> H[Health score + ratings]
    D --> I[[Decision-level fusion]]
    E --> I
    H --> I
    I --> J[XGBoost fertiliser suggestion]
    I --> K[🌾 Crop ranking]
    I --> L[📈 Health trend]
    K --> M[🧑‍🌾 Fertiliser plan]
    M --> N[📄 PDF report]
    M --> O[🔊 Listen]
    style A fill:#fef3c7,stroke:#d97706
    style F fill:#fef3c7,stroke:#d97706
    style M fill:#dcfce7,stroke:#16a34a
    style N fill:#dbeafe,stroke:#2563eb
    style O fill:#dbeafe,stroke:#2563eb
```

<details>
<summary><b>🧑‍🌾 How the fertiliser plan is worked out</b> (click to open)</summary>

```mermaid
flowchart TD
    A[Chosen crop] --> B[Base dose in kg per hectare]
    S[Soil test: N, P, K level] --> C{Level?}
    C -- low --> D[x 1.25]
    C -- medium --> E[x 1.00]
    C -- high --> F[x 0.75]
    B --> G[Adjusted N, P, K]
    D --> G
    E --> G
    F --> G
    G --> H[DAP gives P and some N]
    H --> I[MOP gives K]
    I --> J[Urea gives the remaining N]
    J --> K[Add FYM, lime or gypsum if soil needs it]
    K --> L[Split into stages: before sowing, early, middle, late]
    L --> M[Scale per acre to field size]
```

- **Manure:** 2,000 kg per acre, or 4,000 kg when organic matter is low.
- **Lime:** 200 kg per acre for acidic soil, 400 kg for strongly acidic soil. **Gypsum** 500 kg per hectare for groundnut.
- Each step is marked **done, now or later**. Coffee and tea use rounds instead of stages.

</details>

<details>
<summary><b>🔊 How Listen works</b> (click to open)</summary>

```mermaid
sequenceDiagram
    participant F as Farmer
    participant W as Web app
    participant B as FastAPI
    participant S as Storage
    participant V as Sarvam AI
    F->>W: Press Listen
    W->>B: POST /voice/speak (text, language)
    B->>S: Is this text already saved?
    alt saved
        S-->>B: MP3
    else new
        B->>V: Text to speech (bulbul:v3)
        V-->>B: MP3
        B->>S: Save by hash
    end
    B-->>W: MP3
    W-->>F: Plays the result aloud
```

The Sarvam key stays on the server. Text is limited to 2,500 characters and 12 requests per minute per farmer.

</details>

<details>
<summary><b>📲 How offline use works</b> (click to open)</summary>

```mermaid
flowchart LR
    A[Farmer opens a record online] --> B[Service worker saves it]
    B --> C[(Offline cache)]
    D[Network goes off] --> E{Record saved?}
    E -- yes --> F[Opens from cache ✅]
    E -- no --> G[Rebuilt from saved history and list]
    G --> F
    H[Logout or session expiry] --> I[Cache cleared 🧹]
```

Saving new tests, login and Listen still need internet; the app shows an offline banner. The service worker only runs in a production build (`npm run build && npm start`).

</details>

<details>
<summary><b>🖼️ Full architecture diagram</b> (click to open)</summary>

<img src="docs/assets/Milestone3_System_Architecture.jpg" alt="Milestone 3 architecture" width="100%"/>

</details>

<img src="docs/assets/divider.svg" alt="" width="100%"/>

## 🧭 Milestones

```mermaid
timeline
    title Project journey
    Milestone 1 : Ingestion pipeline
                : Login, photo upload, lab forms
                : PostgreSQL storage
    Milestone 2 : ML analysis engine
                : EfficientNet-B0 and Grad-CAM
                : XGBoost fertiliser model
                : Health score and ratings
    Milestone 3 : Crop ranking, trend, fertiliser plan
                : PDF report and Sarvam voice
                : Offline PWA, 4 languages
                : Docker deployment with HTTPS
```

| Milestone | Notes |
| --- | --- |
| 1. Ingestion | Signup and login, photo upload and camera capture, image checks, OpenCV preprocessing, lab forms, PostgreSQL |
| 2. ML analysis | [MILESTONE2.md](MILESTONE2.md) |
| 3. Advisory and product | [MILESTONE3.md](MILESTONE3.md) · [Fertiliser plan](MILESTONE3_PLAN.md) · [Voice](MILESTONE3_VOICE.md) · [PWA and offline](MILESTONE3_PWA.md) · [Deployment](DEPLOYMENT.md) |

## 🧰 Tech stack

| Layer | Tools |
| --- | --- |
| **Backend** | FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, argon2 + JWT cookie login |
| **ML** | EfficientNet-B0 trained in PyTorch and served with **ONNX Runtime**, XGBoost, OpenCV, Grad-CAM, SHAP |
| **Frontend** | Next.js 16 (app router), React 19, TypeScript, service worker PWA |
| **Voice** | Sarvam AI text to speech (`bulbul:v3`) |
| **Deployment** | Docker, Caddy, **Render** (free web service) + **Neon** (free PostgreSQL); or Docker Compose on any server; photos in the database / local disk / Amazon S3 / Google Cloud Storage |

## 📁 Project structure

```text
soil-analytics/
├── backend/      FastAPI app, ML services, Alembic migrations, tests
├── frontend/     Next.js PWA
├── ml/           Notebooks and evaluation reports
├── deploy/       Caddyfile and backup script
├── docs/assets/  Images and animations used in the docs
├── docker-compose.yml        PostgreSQL for development
└── docker-compose.prod.yml   Full production stack
```

<img src="docs/assets/divider.svg" alt="" width="100%"/>

## 🚀 Quick start

> You need **Python 3.11+**, **Node.js 20+** and **Docker** (for PostgreSQL).

<table>
<tr>
<td width="50%" valign="top">

### 1️⃣ Backend

```bash
docker compose up -d
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

API at <http://localhost:8000>

</td>
<td width="50%" valign="top">

### 2️⃣ Frontend

```bash
cd frontend
npm install
npm run dev
```

App at <http://localhost:3000>

**Install and offline test:**

```bash
npm run build
npm start
```

</td>
</tr>
</table>

> 📦 **Model files are not in Git** (they are large). Put `soil_cnn_D_hard_negatives.pt`, `fert_model.joblib` and `inference_config.json` in `backend/models/`, then check <http://localhost:8000/api/v1/analysis/status>.
>
> 🔊 To enable Listen, set `SARVAM_API_KEY` in `backend/.env`.

**Tests**

```bash
cd backend && pytest                 # backend tests
cd frontend && npx tsc --noEmit      # type check
```

<details>
<summary><b>⚙️ Configuration</b> (click to open)</summary>

Copy `backend/.env.example` to `backend/.env`. **Never commit `.env` files.**

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection |
| `SECRET_KEY` | Signs login cookies (at least 32 characters in production) |
| `COOKIE_SECURE` | `true` when served over HTTPS |
| `STORAGE_BACKEND` | `local`, `s3` or `gcs` |
| `SARVAM_API_KEY` | Text to speech (optional) |

</details>

## 🔌 API

All routes are under `/api/v1`. Login sets a signed `soil_session` cookie.

<details>
<summary><b>Show all endpoints</b> (click to open)</summary>

| Path | Method | Purpose |
| --- | :-: | --- |
| `/auth/signup`, `/auth/login`, `/auth/logout` | POST | Account and session |
| `/auth/me`, `/auth/me/language` | GET, PATCH, PUT | Profile and language |
| `/fields` | GET, POST | The farmer's fields |
| `/fields/{id}/soil-tests` | GET, POST | Lab values |
| `/fields/{id}/images` | GET, POST | Soil photos |
| `/fields/{id}/analyze` | POST | Run the models and save the analysis |
| `/analyses/{id}` | GET | One analysis |
| `/analyses/{id}/gradcam` | GET | Grad-CAM heat map |
| `/fields/{id}/history` | GET | Past analyses |
| `/fields/{id}/trend` | GET | Health trend and 90-day estimate |
| `/fertilizer-plan/crops` | GET | Crops available for a plan |
| `/analyses/{id}/fertilizer-plan` | GET | Step-by-step plan |
| `/voice/status`, `/voice/speak` | GET, POST | Speech |
| `/analysis/status`, `/health` | GET | Model and service health |

</details>

## ☁️ Deployment

The live app runs for free with **no card**: one Docker container on **Render** (API, web app and a small Caddy front door) and a **Neon** PostgreSQL database.

```mermaid
flowchart LR
    U["📱 Phone or browser"] -->|HTTPS| R
    subgraph R["Render free web service (one Docker container, 512 MB)"]
        C["Caddy<br/>:10000"] -->|"/api/*"| A["FastAPI + ONNX Runtime"]
        C -->|"everything else"| W["Next.js app"]
    end
    A -->|"records and photos"| N[("Neon PostgreSQL")]
```

| Part | Choice | Why |
| --- | --- | --- |
| Image model | **ONNX Runtime** instead of PyTorch | The API needs about 300 MB instead of over 1 GB, so it fits a 512 MB free server. Predictions match the PyTorch model (probabilities within 0.00004). Convert once with `backend/scripts/export_onnx.py` |
| Photos | `STORAGE_BACKEND=db` | The free server's disk is wiped on restart, so photos are kept in PostgreSQL |
| Database | Neon free tier | No card, pauses when idle and wakes on the next request |
| Front door | Caddy inside the container | Routes `/api/*` to the API and the rest to the web app, so login cookies stay on one address |

**Deploy your own copy:** [DEPLOY_RENDER.md](DEPLOY_RENDER.md) (Render + Neon, no card). Other options: [DEPLOY_FREE.md](DEPLOY_FREE.md) (free servers and a laptop demo) and [DEPLOYMENT.md](DEPLOYMENT.md) (full details: HTTPS, S3 or Google Cloud storage, backups).

On your own server with Docker Compose:

```bash
cp .env.prod.example .env.prod       # fill in the values
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Four services start: database, backend, frontend and **Caddy**, which gets an HTTPS certificate automatically. Start-up checks refuse weak settings (short `SECRET_KEY`, insecure cookies, missing bucket).

<img src="docs/assets/divider.svg" alt="" width="100%"/>

## ⚠️ Known limitations

- 🧑‍🔬 Rating thresholds, crop ranges and fertiliser doses are **provisional** and need confirmation by an agriculture expert.
- 🗣️ Hindi, Kannada and Tamil text needs native-speaker review.
- 🧮 The fertiliser plan is rule-based and separate from the XGBoost suggestion.
- 💤 The free server sleeps after about 15 minutes without visitors, and the free CPU is small, so the first load and a photo analysis can take from several seconds to about a minute.
- 💾 Photos are stored in the free database (about 1 GB in total), so this setup suits demos, not many users.
- 🔊 Voice (Sarvam) is paid, so the Listen button stays hidden unless an API key is set.
- ☁️ Free tiers can change their terms. The Docker setup in this repository can be moved to any server.

## 👥 Team

**Team C**, Infosys Springboard Internship 7.0 (Batch 4).

<div align="center">

<img src="docs/assets/divider.svg" alt="" width="100%"/>

*Made with 💚 for farmers*

</div>
