"""Cerner FHIR R4 integration client — port of integrations/fhir_client.jac."""

import base64
import os

import requests

FHIR_BASE = os.environ.get(
    "CERNER_FHIR_BASE",
    "https://fhir-ehr.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d",
)


def _fhir_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ.get('CERNER_BEARER_TOKEN', '')}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }


def submit_medication_request(
    patient_id: str,
    medication: str,
    dosage: str,
    frequency: str,
    route: str = "oral",
    rxnorm_code: str = "",
    quantity: int = 30,
    refills: int = 0,
    instructions: str = "",
) -> dict:
    med_coding = []
    if rxnorm_code:
        med_coding.append({
            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
            "code": rxnorm_code,
            "display": f"{medication} {dosage}",
        })

    resource = {
        "resourceType": "MedicationRequest",
        "status": "active",
        "intent": "order",
        "subject": {"reference": f"Patient/{patient_id}"},
        "medicationCodeableConcept": {
            "coding": med_coding,
            "text": f"{medication} {dosage}",
        },
        "dosageInstruction": [{
            "text": instructions or f"Take {dosage} {route} {frequency}",
            "timing": {"code": {"text": frequency}},
            "route": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "26643006",
                    "display": "Oral route",
                }]
            },
        }],
        "dispenseRequest": {
            "quantity": {"value": quantity, "unit": "tablets"},
            "numberOfRepeatsAllowed": refills,
        },
    }

    try:
        resp = requests.post(
            f"{FHIR_BASE}/MedicationRequest",
            headers=_fhir_headers(),
            json=resource,
            timeout=30,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def submit_service_request(
    patient_id: str,
    service: str,
    loinc: str = "",
    reason: str = "",
    urgency: str = "routine",
) -> dict:
    coding = []
    if loinc:
        coding.append({
            "system": "http://loinc.org",
            "code": loinc,
            "display": service,
        })

    resource = {
        "resourceType": "ServiceRequest",
        "status": "active",
        "intent": "order",
        "subject": {"reference": f"Patient/{patient_id}"},
        "code": {"coding": coding, "text": service},
        "priority": urgency,
    }
    if reason:
        resource["reasonCode"] = [{"text": reason}]

    try:
        resp = requests.post(
            f"{FHIR_BASE}/ServiceRequest",
            headers=_fhir_headers(),
            json=resource,
            timeout=30,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def submit_clinical_note(
    patient_id: str,
    practitioner_id: str,
    encounter_id: str,
    subjective: str,
    objective: str,
    assessment: str,
    plan: str,
) -> dict:
    note_text = (
        f"SUBJECTIVE:\n{subjective}\n\n"
        f"OBJECTIVE:\n{objective}\n\n"
        f"ASSESSMENT:\n{assessment}\n\n"
        f"PLAN:\n{plan}"
    )

    resource = {
        "resourceType": "DocumentReference",
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "11506-3",
                "display": "Progress note",
            }]
        },
        "author": [{"reference": f"Practitioner/{practitioner_id}"}],
        "subject": {"reference": f"Patient/{patient_id}"},
        "context": {"encounter": [{"reference": f"Encounter/{encounter_id}"}]},
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": base64.b64encode(note_text.encode()).decode(),
            }
        }],
    }

    try:
        resp = requests.post(
            f"{FHIR_BASE}/DocumentReference",
            headers=_fhir_headers(),
            json=resource,
            timeout=30,
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}
