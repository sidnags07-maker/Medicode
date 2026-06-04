"""AI analysis — replaces Jac's `by llm()` with the Anthropic SDK.

Each former `by llm()` function becomes a forced-tool-use call whose tool
schema is generated from a Pydantic model, so the model is required to return
structured JSON matching the schema. The big static instruction blocks are
sent as a cached system prompt (prompt caching) to cut cost/latency on repeat
calls within the 5-minute cache window.
"""

import json
import os

from anthropic import Anthropic
from pydantic import BaseModel, Field

# Model carried over from the old jac.toml ([plugins.byllm.model]).
MODEL = os.environ.get("MEDICODE_MODEL", "claude-sonnet-4-6")

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set (see .env)")
        _client = Anthropic(api_key=api_key)
    return _client


# --- Structured output schemas (ported from ai/analyze.jac obj defs) ---------


class DiagnosisExtract(BaseModel):
    description: str
    icd10_code: str
    is_primary: bool = False
    confidence: str = "high"
    reasoning: str = ""


class PrescriptionExtract(BaseModel):
    medication_name: str
    dosage: str
    frequency: str
    route: str = "oral"
    quantity: int = 30
    refills: int = 0
    instructions: str = ""
    is_new: bool = True
    rxnorm_code: str = ""
    confidence: str = "high"


class LabOrderExtract(BaseModel):
    test_name: str
    loinc_code: str = ""
    urgency: str = "routine"
    reason: str = ""
    special_instructions: str = ""
    confidence: str = "high"


class ReferralExtract(BaseModel):
    specialty: str
    reason: str = ""
    urgency: str = "routine"
    confidence: str = "high"


class AINote(BaseModel):
    timestamp_context: str
    observation: str
    clinical_flag: str = ""


class ClinicalExtraction(BaseModel):
    chief_complaint: str
    visit_type: str
    diagnoses: list[DiagnosisExtract] = Field(default_factory=list)
    prescriptions: list[PrescriptionExtract] = Field(default_factory=list)
    lab_orders: list[LabOrderExtract] = Field(default_factory=list)
    referrals: list[ReferralExtract] = Field(default_factory=list)
    ai_notes: list[AINote] = Field(default_factory=list)
    items_needing_review: list[str] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    one_liner_summary: str = ""


class SOAPNoteResult(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str


# --- Helpers -----------------------------------------------------------------


def _extract_structured(
    *,
    instructions: str,
    user_content: str,
    schema_model: type[BaseModel],
    tool_name: str,
    temperature: float,
):
    """Force the model to call a single tool whose input matches schema_model,
    then validate the returned JSON into that Pydantic model."""
    client = _get_client()
    tool = {
        "name": tool_name,
        "description": f"Return the result as structured {schema_model.__name__} data.",
        "input_schema": schema_model.model_json_schema(),
    }
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        temperature=temperature,
        system=[
            {
                "type": "text",
                "text": instructions,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": user_content}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == tool_name:
            return schema_model.model_validate(block.input)
    raise RuntimeError(f"Model did not return a {tool_name} tool call")


# --- Public functions (port of the `by llm()` defs) --------------------------

ANALYZE_INSTRUCTIONS = (
    "You are a clinical documentation AI. Analyze a complete telehealth "
    "encounter transcript and extract all clinical entities including "
    "diagnoses with ICD-10 codes, prescriptions with dosages, lab orders with "
    "LOINC codes, and referrals. Only include items the doctor EXPLICITLY "
    "ordered, not items merely discussed. Flag anything ambiguous in "
    "items_needing_review. Provide a concise one_liner_summary and list the "
    "key_decisions made during the visit."
)

SOAP_INSTRUCTIONS = (
    "You are a clinical documentation AI. Generate a professional SOAP note "
    "from a telehealth encounter transcript. Subjective: patient-reported "
    "symptoms, HPI, ROS. Objective: vitals, observations (note 'Virtual visit "
    "- limited physical exam' for telehealth). Assessment: clinical reasoning "
    "with ICD-10 codes and differentials. Plan: all treatments, labs, "
    "referrals, follow-up instructions."
)


def analyze_transcript(transcript: str, patient_context: str) -> ClinicalExtraction:
    user_content = (
        f"PATIENT CONTEXT:\n{patient_context}\n\n"
        f"ENCOUNTER TRANSCRIPT:\n{transcript}"
    )
    return _extract_structured(
        instructions=ANALYZE_INSTRUCTIONS,
        user_content=user_content,
        schema_model=ClinicalExtraction,
        tool_name="record_clinical_extraction",
        temperature=0.1,
    )


def generate_soap_note(
    transcript: str, patient_context: str, diagnoses_summary: str
) -> SOAPNoteResult:
    user_content = (
        f"PATIENT CONTEXT:\n{patient_context}\n\n"
        f"DIAGNOSES:\n{diagnoses_summary}\n\n"
        f"ENCOUNTER TRANSCRIPT:\n{transcript}"
    )
    return _extract_structured(
        instructions=SOAP_INSTRUCTIONS,
        user_content=user_content,
        schema_model=SOAPNoteResult,
        tool_name="record_soap_note",
        temperature=0.2,
    )
