# KundliHub

Full‑stack Vedic astrology app (FastAPI + Vue) to generate and explore a Kundli (birth chart) and related insights.

## What you can do

- **Generate a Kundli** (birth chart) from DOB/TOB/place (or lat/lon)
- **Charts**: Lagna (D1) and Navamsa (D9)
- **Planetary positions**: sign/rashi, nakshatra + pada, house, retro/combust
- **Panchang + Avakhada** details
- **Dosha checks** (computed from planets + avakhada)
- **Vimshottari Dasha** with on‑demand sub‑period drill‑down
- **Daily horoscope** (with simple remedies) for a selected date
- **Shani Sade Sati** phases + remedies for a selected date
- **Shani Sade Sati timeline (from birth)** stored in DB for fast table rendering
- **OTP email login** (request OTP → verify OTP → get JWT)
- **Saved history** persisted in a SQL database (list + view + delete)

## Project Structure

```
KundliHub/
	backend/
		requirements.txt
		.gitignore
		app/
			main.py         # FastAPI routes
			astrology.py    # Swiss‑Ephemeris calculations + core kundli/dasha data
			models.py       # SQLAlchemy models
			database.py     # SQLAlchemy engine/session (DATABASE_URL)
			dasha_logic.py
			dosha_logic.py
			horoscope_logic.py
			sadesati_logic.py
			panchang_logic.py
	frontend/
		package.json
		vite.config.js
		index.html
		src/
			App.vue
			main.js
			style.css
			api/
				client.js
			components/
				Header.vue
				Footer.vue
				InputForm.vue
				KundliChart.vue
				PlanetaryPositions.vue
				VimshottariDasha.vue
				BasicDetails.vue
				DailyHoroscope.vue
				Dosha.vue
				SadeSati.vue
				OtpLogin.vue
```

## Tech Stack (with versions)

### Frontend
- Vue: `^3.5.24`
- Vite: `^7.2.4`
- TailwindCSS: `^4.1.18`
- Axios: `^1.13.4`
- Pinia: `^3.0.4`
- Vue Router: `^4.6.4`

### Backend
The backend Python dependencies are listed in [backend/requirements.txt](backend/requirements.txt):
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- pyswisseph (Swiss Ephemeris)
- timezonefinder, tzdata
- python-dotenv
- psycopg2-binary (PostgreSQL)

### Database
- Configured via `DATABASE_URL` (see [backend/app/database.py](backend/app/database.py))
- Works with PostgreSQL (recommended for production) and SQLite (dev/testing)

## Features & Key Endpoints

Backend API:
- `POST /generate` → calculate kundli + save a new record
- `POST /generate` returns `record_id` so the frontend can fetch stored timelines
- `POST /calculate` → calculate kundli without saving (useful for “compute-only”)
- `GET /history?limit=25` → fetch saved records (default 25, max 200)
- `DELETE /history/{id}` → delete a record
- `GET /history/{id}/sade-sati-periods` → get (or lazily compute + persist) the Sade Sati timeline from birth
- `POST /dasha/subperiods` → fetch sub‑dashas on demand
- `POST /horoscope/daily` → daily horoscope (+ remedies)
- `POST /sade-sati` → sade sati phases (+ remedies)

Auth:
- `POST /auth/request-otp` → send login OTP to email
- `POST /auth/verify-otp` → verify OTP and return JWT access token
- `GET /auth/me` → return the logged-in user

Interactive API docs (Swagger) are available at:
- `http://127.0.0.1:8000/docs`

### Notes on coordinates (place vs lat/lon)

- Requests support either **lat/lon** or a **place** string.
- If lat/lon aren’t provided, the backend geocodes the place using OpenStreetMap Nominatim.
- If you see `Could not geocode place of birth`, pass explicit lat/lon (or use a more specific place).

### Database notes (normalization + best‑effort migration)

Recent versions store data in normalized tables (panchang/avakhada as 1:1 and planets/dasha as 1:N). On startup the backend attempts a best‑effort migration for older rows and (for Postgres) may drop legacy JSON columns.

## Running Locally (Fresh Machine)

### Prerequisites
- Node.js (Vite recommends Node `20.19+` or `22.12+`)
- Python `3.10+` (3.11 recommended)
- A database URL (`DATABASE_URL`) for backend

### 1) Backend Setup

From the repo root:

```bash
cd backend
python -m venv .venv
```

Activate venv:
- Windows PowerShell: `./.venv/Scripts/Activate.ps1`
- Windows cmd: `.\.venv\Scripts\activate.bat`
- macOS/Linux: `source .venv/bin/activate`

Install deps:

```bash
pip install -r requirements.txt
```

Set `DATABASE_URL`:
- Option A (recommended): create `backend/.env` with:
	- `DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require`
- Option B: export as an environment variable.

`backend/.env` is loaded automatically at startup (see [backend/app/database.py](backend/app/database.py)).

Example `backend/.env` (safe defaults for local dev):

```env
# Database (quick local option)
DATABASE_URL=sqlite:///./kundlihub.db

# Required for OTP hashing + JWT auth
JWT_SECRET=change-me-in-prod

# Optional: Resend email (for real OTP delivery)
# RESEND_API_KEY=
# RESEND_FROM_EMAIL=

# Dev convenience: show OTP in server logs and skip sending email
DEV_OTP_ECHO=1
DEV_OTP_SKIP_SEND=1

# Optional tuning
OTP_TTL_MINUTES=10
OTP_MAX_ATTEMPTS=5
OTP_MAX_REQUESTS_PER_EMAIL=10
OTP_REQUEST_WINDOW_MINUTES=1440

# How far ahead to compute “Sade Sati from birth” timeline when first requested
SADE_SATI_TIMELINE_YEARS=100
```

Security note: never commit real credentials. If your `backend/.env` was ever committed, rotate that password.

Run the API:

```bash
uvicorn app.main:app --reload
```

Backend runs on `http://127.0.0.1:8000`.

#### Backend environment variables

Required:
- `DATABASE_URL`
- `JWT_SECRET` (required for JWT + OTP hashing)

Email (Resend) for OTP delivery:
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`

OTP behavior:
- `OTP_TTL_MINUTES` (default: `10`)
- `OTP_MAX_ATTEMPTS` (default: `5`) – max verify attempts per OTP
- `OTP_MAX_REQUESTS_PER_EMAIL` (default: `10`) – rate limit for OTP generation per email
- `OTP_REQUEST_WINDOW_MINUTES` (default: `1440`) – rate limit window (minutes)
- `OTP_PEPPER` (optional) – dedicated pepper for OTP hashing (falls back to `JWT_SECRET`)

Dev-only flags:
- `DEV_OTP_ECHO=1` – print OTP in backend logs
- `DEV_OTP_SKIP_SEND=1` – do not send emails (use with `DEV_OTP_ECHO`)

Sade Sati timeline storage:
- `SADE_SATI_TIMELINE_YEARS` (default: `100`) – how far from birth to compute and store the timeline

### 2) Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on the URL shown by Vite (typically `http://localhost:5173`).

#### Frontend API base URL

The Axios client is configured in [frontend/src/api/client.js](frontend/src/api/client.js).

- It uses `import.meta.env.VITE_API_BASE_URL` when set.
- It falls back to `http://localhost:8000` for local dev.

To configure it, copy [frontend/.env.example](frontend/.env.example) to `frontend/.env` and set:

- `VITE_API_BASE_URL=http://localhost:8000`

## Deploying to Another System

### Backend Deployment (production)

1. Provision a database (PostgreSQL recommended).
2. Set `DATABASE_URL` in the server environment.
3. Install Python deps in a virtualenv:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

4. Run with a production server (example using Uvicorn):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Notes:
- CORS is currently open (`allow_origins=["*"]`). Lock this down to your frontend domain for production.

### Frontend Deployment (production)

1. Build:

```bash
cd frontend
npm install
npm run build
```

2. Deploy the generated `frontend/dist/` to any static host (Nginx, Netlify, Vercel, S3, etc.).
3. Ensure the frontend is built with the correct API base URL:
	- Set `VITE_API_BASE_URL` in `frontend/.env` before running `npm run build`, or
	- Provide `VITE_API_BASE_URL` via your hosting provider’s build-time environment variables.

Note: Vite injects `VITE_*` variables at build time. If the backend URL changes, rebuild the frontend.

## Notes

- The Vimshottari sub‑dashas are fetched on demand to keep the initial payload small.
- Saved “View” uses stored JSON and does not create duplicate records.
- The Sade Sati “from birth” table is persisted per saved record; first fetch may take longer, subsequent fetches are fast.

### Timezone note

For consistency, calculations currently assume a fixed IST offset (`GMT+5:30`) instead of resolving a timezone from the place/coordinates.

