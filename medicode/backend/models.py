"""SQLModel tables — direct port of the Jac graph nodes.

The Jac graph was: Root -> Patient -> Encounter -> {Transcript -> Chunk,
Diagnosis, Prescription, LabOrder, ImagingOrder, Referral, SOAPNote}.
Here that becomes foreign-key relationships on SQLite.

`to_node(obj)` reproduces Jac's node serialization: all `has` fields plus a
string `_jac_id` (the frontend reads `encounter._jac_id`, `patient.mrn`, etc).
"""

from enum import IntEnum
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class EncounterStatus(IntEnum):
    """Serializes to an int — the frontend's Encounter.status is a number."""

    SCHEDULED = 0
    IN_PROGRESS = 1
    ANALYZING = 2
    REVIEW = 3
    COMPLETED = 4
    SUBMITTED = 5


# Order status kept as plain strings (the frontend never reads it).
ORDER_DRAFT = "draft"
ORDER_APPROVED = "approved"
ORDER_SUBMITTED = "submitted"


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    dob: str
    mrn: str = Field(index=True)
    sex: str
    allergies: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    medications: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    conditions: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    fhir_id: str = ""


class Encounter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id", index=True)
    encounter_date: str
    chief_complaint: str = ""
    status: int = Field(default=EncounterStatus.SCHEDULED)
    started_at: str = ""
    ended_at: str = ""
    encounter_type: str = "telehealth"
    fhir_id: str = ""


class Transcript(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    encounter_id: int = Field(foreign_key="encounter.id", index=True)
    full_text: str = ""
    language: str = "en"
    duration_seconds: int = 0


class TranscriptChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transcript_id: int = Field(foreign_key="transcript.id", index=True)
    speaker: str
    text: str
    timestamp_start: float
    timestamp_end: float
    sequence: int


class Diagnosis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    encounter_id: int = Field(foreign_key="encounter.id", index=True)
    description: str
    icd10_code: str
    status: str = "active"
    is_primary: bool = False
    confidence: str = "high"
    reasoning: str = ""


class Prescription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    encounter_id: int = Field(foreign_key="encounter.id", index=True)
    medication_name: str
    dosage: str
    frequency: str
    route: str = "oral"
    quantity: int = 30
    refills: int = 0
    instructions: str = ""
    is_new: bool = True
    is_change: bool = False
    discontinued: bool = False
    confidence: str = "high"
    order_status: str = ORDER_DRAFT
    fhir_id: str = ""
    rxnorm_code: str = ""


class LabOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    encounter_id: int = Field(foreign_key="encounter.id", index=True)
    test_name: str
    loinc_code: str = ""
    urgency: str = "routine"
    reason: str = ""
    special_instructions: str = ""
    confidence: str = "high"
    order_status: str = ORDER_DRAFT
    fhir_id: str = ""


class ImagingOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    encounter_id: int = Field(foreign_key="encounter.id", index=True)
    study_name: str
    cpt_code: str = ""
    reason: str = ""
    urgency: str = "routine"
    confidence: str = "high"
    order_status: str = ORDER_DRAFT
    fhir_id: str = ""


class Referral(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    encounter_id: int = Field(foreign_key="encounter.id", index=True)
    specialty: str
    reason: str = ""
    urgency: str = "routine"
    confidence: str = "high"
    order_status: str = ORDER_DRAFT
    fhir_id: str = ""


class SOAPNote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    encounter_id: int = Field(foreign_key="encounter.id", index=True)
    subjective: str
    objective: str
    assessment: str
    plan: str
    generated_at: str = ""


def to_node(obj: Optional[SQLModel]) -> Optional[dict]:
    """Serialize a row the way the Jac server serialized a node: every field
    plus a string `_jac_id`. Returns None for None (mirrors optional reports)."""
    if obj is None:
        return None
    data = obj.model_dump()
    data["_jac_id"] = str(data.get("id", ""))
    return data


def to_nodes(objs) -> list[dict]:
    return [to_node(o) for o in objs]
