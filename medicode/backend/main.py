"""FastAPI app — reproduces the Jac server's REST surface for the React app.

Conventions mirrored from `jac serve`:
  * POST /user/register, /user/login  -> {"ok": true, "data": {"token": ...}}
  * POST /walker/<name>               -> {"ok": true, "data": {"reports": [...]}}
  * nodes serialize with a string `_jac_id`
Plus POST /api/transcribe for ElevenLabs audio (was the separate web/app.py).
"""

import os
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import select

from . import ai, fhir, stt
from .db import get_session, init_db
from .models import (
    Diagnosis,
    Encounter,
    EncounterStatus,
    ImagingOrder,
    LabOrder,
    ORDER_APPROVED,
    ORDER_SUBMITTED,
    Patient,
    Prescription,
    Referral,
    SOAPNote,
    Transcript,
    TranscriptChunk,
    to_node,
    to_nodes,
)


# --- .env loading (simple KEY=VALUE parser, like the old proxy) --------------

def _load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


_load_env()

app = FastAPI(title="MediCode API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


# --- Envelope helpers --------------------------------------------------------

def reports(*items) -> JSONResponse:
    return JSONResponse({"ok": True, "data": {"reports": list(items)}, "error": None})


def fail(message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        {"ok": False, "data": None, "error": message}, status_code=status
    )


def _now() -> str:
    from datetime import datetime

    return datetime.now().isoformat()


# --- Auth (frontend just needs a token string back) --------------------------

class Creds(BaseModel):
    username: str
    password: str


@app.post("/user/register")
def register(_: Creds):
    return JSONResponse({"ok": True, "data": {"token": "medicode-dev-token"}})


@app.post("/user/login")
def login(_: Creds):
    return JSONResponse({"ok": True, "data": {"token": "medicode-dev-token"}})


# --- Patient walkers ---------------------------------------------------------

class CreatePatientReq(BaseModel):
    first_name: str
    last_name: str
    dob: str
    mrn: str
    sex: str
    allergies: list[str] = []
    medications: list[str] = []
    conditions: list[str] = []


@app.post("/walker/create_patient")
def create_patient(req: CreatePatientReq):
    with get_session() as s:
        patient = Patient(**req.model_dump())
        s.add(patient)
        s.commit()
        s.refresh(patient)
        return reports(to_node(patient))


@app.post("/walker/get_patients")
def get_patients():
    with get_session() as s:
        patients = s.exec(select(Patient)).all()
        return reports(to_nodes(patients))


class MrnReq(BaseModel):
    mrn: str


@app.post("/walker/get_patient_by_mrn")
def get_patient_by_mrn(req: MrnReq):
    with get_session() as s:
        patient = s.exec(select(Patient).where(Patient.mrn == req.mrn)).first()
        if patient is None:
            return reports()
        return reports(to_node(patient))


# --- Encounter walkers -------------------------------------------------------

class StartEncounterReq(BaseModel):
    patient_mrn: str
    chief_complaint: str = ""


@app.post("/walker/start_encounter")
def start_encounter(req: StartEncounterReq):
    with get_session() as s:
        patient = s.exec(
            select(Patient).where(Patient.mrn == req.patient_mrn)
        ).first()
        if patient is None:
            return fail("Patient not found")
        now = _now()
        enc = Encounter(
            patient_id=patient.id,
            encounter_date=now,
            chief_complaint=req.chief_complaint,
            status=EncounterStatus.IN_PROGRESS,
            started_at=now,
        )
        s.add(enc)
        s.commit()
        s.refresh(enc)
        s.add(Transcript(encounter_id=enc.id))
        s.commit()
        return reports(to_node(enc))


class EncounterIdReq(BaseModel):
    encounter_id: str


def _get_encounter(s, encounter_id: str) -> Encounter | None:
    try:
        eid = int(encounter_id)
    except (TypeError, ValueError):
        return None
    return s.get(Encounter, eid)


@app.post("/walker/end_encounter")
def end_encounter(req: EncounterIdReq):
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        enc.ended_at = _now()
        enc.status = EncounterStatus.ANALYZING
        s.add(enc)
        s.commit()
        s.refresh(enc)
        return reports(to_node(enc))


@app.post("/walker/get_encounter")
def get_encounter(req: EncounterIdReq):
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        patient = s.get(Patient, enc.patient_id)
        transcript = s.exec(
            select(Transcript).where(Transcript.encounter_id == enc.id)
        ).first()
        eid = enc.id

        def kids(model):
            return s.exec(select(model).where(model.encounter_id == eid)).all()

        soap = s.exec(select(SOAPNote).where(SOAPNote.encounter_id == eid)).first()
        return reports({
            "encounter": to_node(enc),
            "patient": to_node(patient),
            "transcript": to_node(transcript),
            "diagnoses": to_nodes(kids(Diagnosis)),
            "prescriptions": to_nodes(kids(Prescription)),
            "lab_orders": to_nodes(kids(LabOrder)),
            "imaging_orders": to_nodes(kids(ImagingOrder)),
            "referrals": to_nodes(kids(Referral)),
            "soap_note": to_node(soap),
        })


class ListEncountersReq(BaseModel):
    patient_mrn: str


@app.post("/walker/list_encounters")
def list_encounters(req: ListEncountersReq):
    with get_session() as s:
        patient = s.exec(
            select(Patient).where(Patient.mrn == req.patient_mrn)
        ).first()
        if patient is None:
            return reports([])
        encs = s.exec(
            select(Encounter).where(Encounter.patient_id == patient.id)
        ).all()
        return reports(to_nodes(encs))


# --- Transcript walkers ------------------------------------------------------

class IngestChunkReq(BaseModel):
    encounter_id: str
    speaker: str
    text: str
    timestamp_start: float
    timestamp_end: float


@app.post("/walker/ingest_chunk")
def ingest_chunk(req: IngestChunkReq):
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        transcript = s.exec(
            select(Transcript).where(Transcript.encounter_id == enc.id)
        ).first()
        if transcript is None:
            return fail("Transcript not found")
        seq = len(s.exec(
            select(TranscriptChunk).where(
                TranscriptChunk.transcript_id == transcript.id
            )
        ).all())
        s.add(TranscriptChunk(
            transcript_id=transcript.id,
            speaker=req.speaker,
            text=req.text,
            timestamp_start=req.timestamp_start,
            timestamp_end=req.timestamp_end,
            sequence=seq,
        ))
        transcript.full_text += f"\n[{req.speaker}]: {req.text}"
        transcript.duration_seconds = int(req.timestamp_end)
        s.add(transcript)
        s.commit()
        return reports({"sequence": seq, "text": req.text})


class IngestFullReq(BaseModel):
    encounter_id: str
    full_text: str


@app.post("/walker/ingest_full_transcript")
def ingest_full_transcript(req: IngestFullReq):
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        transcript = s.exec(
            select(Transcript).where(Transcript.encounter_id == enc.id)
        ).first()
        if transcript is None:
            return fail("Transcript not found")
        transcript.full_text = req.full_text
        s.add(transcript)
        s.commit()
        return reports({"status": "transcript_ingested", "length": len(req.full_text)})


@app.post("/walker/get_transcript")
def get_transcript(req: EncounterIdReq):
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        transcript = s.exec(
            select(Transcript).where(Transcript.encounter_id == enc.id)
        ).first()
        if transcript is None:
            return fail("Transcript not found")
        chunks = s.exec(
            select(TranscriptChunk)
            .where(TranscriptChunk.transcript_id == transcript.id)
            .order_by(TranscriptChunk.sequence)
        ).all()
        return reports({
            "full_text": transcript.full_text,
            "duration_seconds": transcript.duration_seconds,
            "chunk_count": len(chunks),
            "chunks": to_nodes(chunks),
        })


# --- Analysis walker ---------------------------------------------------------

@app.post("/walker/run_analysis")
def run_analysis(req: EncounterIdReq):
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        patient = s.get(Patient, enc.patient_id)
        patient_context = (
            f"Name: {patient.first_name} {patient.last_name}, "
            f"DOB: {patient.dob}, Sex: {patient.sex}, "
            f"Allergies: {patient.allergies}, "
            f"Current Medications: {patient.medications}, "
            f"Active Conditions: {patient.conditions}"
        )

        transcript = s.exec(
            select(Transcript).where(Transcript.encounter_id == enc.id)
        ).first()
        if transcript is None or not transcript.full_text.strip():
            return reports({"error": "Transcript is empty"})

        enc.status = EncounterStatus.ANALYZING
        s.add(enc)
        s.commit()

        try:
            extraction = ai.analyze_transcript(
                transcript=transcript.full_text,
                patient_context=patient_context,
            )
        except Exception as e:
            return fail(f"AI analysis failed: {e}", status=502)

        enc.chief_complaint = extraction.chief_complaint

        for dx in extraction.diagnoses:
            s.add(Diagnosis(
                encounter_id=enc.id,
                description=dx.description,
                icd10_code=dx.icd10_code,
                is_primary=dx.is_primary,
                confidence=dx.confidence,
                reasoning=dx.reasoning,
            ))
        for rx in extraction.prescriptions:
            s.add(Prescription(
                encounter_id=enc.id,
                medication_name=rx.medication_name,
                dosage=rx.dosage,
                frequency=rx.frequency,
                route=rx.route,
                quantity=rx.quantity,
                refills=rx.refills,
                instructions=rx.instructions,
                is_new=rx.is_new,
                confidence=rx.confidence,
                rxnorm_code=rx.rxnorm_code,
            ))
        for lab in extraction.lab_orders:
            s.add(LabOrder(
                encounter_id=enc.id,
                test_name=lab.test_name,
                loinc_code=lab.loinc_code,
                urgency=lab.urgency,
                reason=lab.reason,
                special_instructions=lab.special_instructions,
                confidence=lab.confidence,
            ))
        for ref in extraction.referrals:
            s.add(Referral(
                encounter_id=enc.id,
                specialty=ref.specialty,
                reason=ref.reason,
                urgency=ref.urgency,
                confidence=ref.confidence,
            ))

        dx_summary = ", ".join(
            f"{d.description} ({d.icd10_code})" for d in extraction.diagnoses
        )
        try:
            soap = ai.generate_soap_note(
                transcript=transcript.full_text,
                patient_context=patient_context,
                diagnoses_summary=dx_summary,
            )
            s.add(SOAPNote(
                encounter_id=enc.id,
                subjective=soap.subjective,
                objective=soap.objective,
                assessment=soap.assessment,
                plan=soap.plan,
                generated_at=_now(),
            ))
        except Exception as e:
            return fail(f"SOAP generation failed: {e}", status=502)

        enc.status = EncounterStatus.REVIEW
        s.add(enc)
        s.commit()

        return reports({
            "status": "analysis_complete",
            "encounter_id": req.encounter_id,
            "chief_complaint": extraction.chief_complaint,
            "visit_type": extraction.visit_type,
            "diagnosis_count": len(extraction.diagnoses),
            "prescription_count": len(extraction.prescriptions),
            "lab_order_count": len(extraction.lab_orders),
            "referral_count": len(extraction.referrals),
            "one_liner": extraction.one_liner_summary,
            "items_needing_review": extraction.items_needing_review,
            "key_decisions": extraction.key_decisions,
            "ai_notes": [n.model_dump() for n in extraction.ai_notes],
        })


# --- Order walkers -----------------------------------------------------------

class ApproveOrderReq(BaseModel):
    encounter_id: str
    order_type: str
    order_index: int


@app.post("/walker/approve_order")
def approve_order(req: ApproveOrderReq):
    model_for = {
        "prescription": Prescription,
        "lab": LabOrder,
        "referral": Referral,
    }
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        model = model_for.get(req.order_type)
        if model is None:
            return reports({"error": f"Unknown order type: {req.order_type}"})
        orders = s.exec(select(model).where(model.encounter_id == enc.id)).all()
        if req.order_index >= len(orders):
            return reports({"error": "Order index out of range"})
        orders[req.order_index].order_status = ORDER_APPROVED
        s.add(orders[req.order_index])
        s.commit()
        return reports({
            "status": "approved",
            "order_type": req.order_type,
            "index": req.order_index,
        })


@app.post("/walker/approve_all_orders")
def approve_all_orders(req: EncounterIdReq):
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        count = 0
        for model in (Prescription, LabOrder, Referral):
            for order in s.exec(
                select(model).where(model.encounter_id == enc.id)
            ).all():
                order.order_status = ORDER_APPROVED
                s.add(order)
                count += 1
        s.commit()
        return reports({"status": "all_approved", "count": count})


@app.post("/walker/submit_orders")
def submit_orders(req: EncounterIdReq):
    with get_session() as s:
        enc = _get_encounter(s, req.encounter_id)
        if enc is None:
            return fail("Encounter not found")
        patient = s.get(Patient, enc.patient_id)
        pid = patient.fhir_id
        results = {"prescriptions": [], "labs": [], "referrals": []}

        for rx in s.exec(
            select(Prescription).where(Prescription.encounter_id == enc.id)
        ).all():
            if rx.order_status == ORDER_APPROVED:
                resp = fhir.submit_medication_request(
                    patient_id=pid,
                    medication=rx.medication_name,
                    dosage=rx.dosage,
                    frequency=rx.frequency,
                    route=rx.route,
                    rxnorm_code=rx.rxnorm_code,
                    quantity=rx.quantity,
                    refills=rx.refills,
                    instructions=rx.instructions,
                )
                rx.order_status = ORDER_SUBMITTED
                if "id" in resp:
                    rx.fhir_id = resp["id"]
                s.add(rx)
                results["prescriptions"].append(resp)

        for lab in s.exec(
            select(LabOrder).where(LabOrder.encounter_id == enc.id)
        ).all():
            if lab.order_status == ORDER_APPROVED:
                resp = fhir.submit_service_request(
                    patient_id=pid,
                    service=lab.test_name,
                    loinc=lab.loinc_code,
                    reason=lab.reason,
                    urgency=lab.urgency,
                )
                lab.order_status = ORDER_SUBMITTED
                if "id" in resp:
                    lab.fhir_id = resp["id"]
                s.add(lab)
                results["labs"].append(resp)

        for ref in s.exec(
            select(Referral).where(Referral.encounter_id == enc.id)
        ).all():
            if ref.order_status == ORDER_APPROVED:
                resp = fhir.submit_service_request(
                    patient_id=pid,
                    service=f"Referral to {ref.specialty}",
                    loinc="",
                    reason=ref.reason,
                    urgency=ref.urgency,
                )
                ref.order_status = ORDER_SUBMITTED
                if "id" in resp:
                    ref.fhir_id = resp["id"]
                s.add(ref)
                results["referrals"].append(resp)

        enc.status = EncounterStatus.SUBMITTED
        s.add(enc)
        s.commit()
        return reports(results)


# --- Audio transcription (was web/app.py) ------------------------------------

@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) < 1000:
            return JSONResponse({"error": "Recording too short."}, status_code=400)
        result = stt.transcribe_audio(audio_bytes, filename="recording.webm")
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
