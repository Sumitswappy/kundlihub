# KundliHub

Full‑stack Vedic astrology app that generates a Kundli (birth chart) with:
- Lagna (D1) chart and Navamsa (D9) chart
- Planetary Positions table (sign, nakshatra, house, retro/combust, status)
- Vimshottari Dasha (Mahadasha → Antardasha → Pratyantardasha → Sookshmadasha) with on‑demand drill‑down
- Saved history (view/edit/delete) backed by a SQL database

## Project Structure

```
KundliHub/
	backend/
		requirements.txt
		.gitignore
		app/
			main.py         # FastAPI routes (/generate, /history, /calculate, /dasha/subperiods)
			astrology.py    # Swiss‑Ephemeris calculations + Vimshottari logic
			models.py       # SQLAlchemy models
			database.py     # SQLAlchemy engine/session (DATABASE_URL)
	frontend/
		package.json
		vite.config.js
		index.html
		src/
			App.vue
			main.js
			style.css
			components/
				InputForm.vue
				KundliChart.vue
				PlanetaryPositions.vue
				VimshottariDasha.vue
				BasicDetails.vue
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
- `POST /calculate` → calculate kundli without saving (used for legacy history items)
- `GET /history` → fetch saved records
- `DELETE /history/{id}` → delete a record
- `POST /dasha/subperiods` → fetch sub‑dashas on demand (keeps frontend lightweight)

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
	- `DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require`
- Option B: export as an environment variable.

Run the API:

```bash
uvicorn app.main:app --reload
```

Backend runs on `http://127.0.0.1:8000`.

### 2) Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on the URL shown by Vite (typically `http://localhost:5173`).

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
3. Ensure the frontend is configured to call the correct backend base URL (currently hardcoded to `http://localhost:8000` in components using Axios).

## Notes

- The Vimshottari sub‑dashas are fetched on demand to keep the initial payload small.
- Saved “View” uses stored JSON and does not create duplicate records.

