# MediCode — AI Medical Scribe

Python (FastAPI) backend + React/TypeScript frontend.

- `backend/` — FastAPI app, SQLModel/SQLite data layer, Anthropic-powered
  clinical analysis, ElevenLabs STT, and Cerner FHIR integration.
- `frontend/` — Vite + React UI.

## Setup

```bash
cd medicode
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

## Run

Backend (port 8000):

```bash
cd medicode
./venv/bin/uvicorn backend.main:app --port 8000 --reload
```

Frontend (port 3000, proxies /walker, /user, /api to the backend):

```bash
cd medicode/frontend
npm install
npm run dev
```

Open http://localhost:3000.

## API (mirrors the original Jac server)

- `POST /user/register`, `POST /user/login` → `{ ok, data: { token } }`
- `POST /walker/<name>` → `{ ok, data: { reports: [...] } }`
- `POST /api/transcribe` (multipart audio) → labeled transcript segments

Data persists to `medicode.db` (SQLite), created automatically on startup.
