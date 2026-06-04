export interface Patient {
  first_name: string;
  last_name: string;
  dob: string;
  mrn: string;
  sex: string;
  allergies: string[];
  medications: string[];
  conditions: string[];
  _jac_id?: string;
}

export interface Encounter {
  _jac_id: string;
  encounter_date: string;
  chief_complaint: string;
  status: number;
  started_at: string;
  ended_at: string;
}

export interface TranscriptSegment {
  speaker: string;
  text: string;
  start: number;
}

export interface Diagnosis {
  description: string;
  icd10_code: string;
  is_primary: boolean;
  confidence: string;
  reasoning: string;
}

export interface Prescription {
  medication_name: string;
  dosage: string;
  frequency: string;
  route: string;
  quantity: number;
  refills: number;
  instructions: string;
  confidence: string;
}

export interface LabOrder {
  test_name: string;
  loinc_code: string;
  urgency: string;
  reason: string;
  special_instructions: string;
  confidence: string;
}

export interface Referral {
  specialty: string;
  reason: string;
  urgency: string;
  confidence: string;
}

export interface SOAPNote {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface EncounterData {
  encounter: Encounter;
  patient: Patient;
  diagnoses: Diagnosis[];
  prescriptions: Prescription[];
  lab_orders: LabOrder[];
  referrals: Referral[];
  soap_note: SOAPNote | null;
}
