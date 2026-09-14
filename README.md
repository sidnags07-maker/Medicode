# MediCode

**AI medical scribe that turns spoken or free-text clinical notes into standardized
ICD-10 and CPT billing codes, validated against live patient records.**

Built in 24 hours by a team of four at a hackathon.

## The problem

Clinicians spend a large share of every visit on documentation, and the codes that
documentation produces are what actually get billed. Assigning ICD-10 diagnosis codes
and CPT procedure codes by hand is slow, requires specialized training, and is easy to
get subtly wrong. A miscoded encounter is a rejected claim.

MediCode takes the note in whatever form the clinician produces it, including speech,
and proposes the codes, then checks them against the patient's real chart rather than
trusting the model's output on its own.

## How it works

```
audio ──► ElevenLabs STT ──► labeled transcript
                                   │
free-text note ────────────────────┼──► Claude analysis ──► proposed ICD-10 / CPT
                                   │                              │
                                   └──► Oracle Health (Cerner)    │
                                        FHIR R4 patient record ───┘
                                                  │
                                                  ▼
                                        validated coded report
```

The validation step is the point. An LLM will happily produce a plausible,
well-formatted code that does not match the patient's actual documented conditions,
so generated codes are cross-checked against conditions and encounters pulled from
the FHIR R4 API before they are shown as a report.

## Stack

| Layer | Built with |
| --- | --- |
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, SQLModel, SQLite |
| Coding model | Anthropic Claude API |
| Speech to text | ElevenLabs |
| Clinical records | Oracle Health (Cerner) FHIR R4 |

## Layout

```
medicode/
  backend/
    main.py      FastAPI app + routes
    ai.py        Claude-powered clinical analysis and code generation
    fhir.py      Oracle Health FHIR R4 client
    stt.py       ElevenLabs speech-to-text
    models.py    SQLModel schema
    db.py        SQLite session handling
  frontend/      Vite + React + TypeScript UI
```

## Running it

```bash
git clone https://github.com/sidnags07-maker/Medicode.git
cd Medicode/medicode

python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in your API keys
```

Backend on port 8000:

```bash
./venv/bin/uvicorn backend.main:app --port 8000 --reload
```

Frontend on port 3000 (proxies `/walker`, `/user`, `/api` to the backend):

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000. SQLite persists to `medicode.db`, created on startup.

## API

- `POST /user/register`, `POST /user/login` → `{ ok, data: { token } }`
- `POST /walker/<name>` → `{ ok, data: { reports: [...] } }`
- `POST /api/transcribe` (multipart audio) → labeled transcript segments

## Status

Hackathon prototype. It demonstrates the full path from audio to validated codes,
but it is not a clinical tool: no HIPAA controls, no audit logging, and no
clinician sign-off workflow. Do not use it with real patient data.
