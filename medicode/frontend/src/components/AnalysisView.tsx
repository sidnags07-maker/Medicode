import { useState } from "react";
import type { EncounterData, Patient } from "../types";

interface Props {
  data: EncounterData;
  patient: Patient;
  meetingStart: Date | null;
  meetingEnd: Date | null;
}

type Tab = "summary" | "meds" | "labs" | "codes" | "soap";

export default function AnalysisView({
  data,
  patient,
  meetingStart,
  meetingEnd,
}: Props) {
  const [tab, setTab] = useState<Tab>("summary");
  const { diagnoses, prescriptions, lab_orders, referrals, soap_note } = data;

  const formatTime = (d: Date) =>
    d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

  const formatDate = (d: Date) =>
    d.toLocaleDateString("en-US", { month: "2-digit", day: "2-digit", year: "numeric" });

  const duration =
    meetingStart && meetingEnd
      ? Math.round((meetingEnd.getTime() - meetingStart.getTime()) / 60000)
      : 0;

  // Calculate age from DOB
  const calcAge = () => {
    if (!patient.dob) return "";
    const dob = new Date(patient.dob);
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) age--;
    return String(age);
  };

  const age = calcAge();
  const sexLabel = patient.sex === "male" ? "M" : patient.sex === "female" ? "F" : patient.sex;

  return (
    <div className="analysis-layout">
      {/* LEFT PANEL — Patient + Summary */}
      <div className="analysis-left">
        {/* Patient Header Card */}
        <div className="patient-header-card">
          <div className="patient-avatar">
            {patient.first_name[0]}{patient.last_name[0]}
          </div>
          <h2 className="patient-name">
            {patient.first_name} {patient.last_name}
          </h2>
          <p className="patient-demo">
            {age} &bull; {sexLabel} &bull; {patient.dob}
          </p>
          <p className="patient-mrn">MRN {patient.mrn}</p>

          {/* Quick nav icons */}
          <div className="patient-quick-nav">
            <button className="qnav-btn" onClick={() => setTab("summary")}>
              <span className="qnav-icon">&#9776;</span>
              <span>Summary</span>
            </button>
            <button className="qnav-btn" onClick={() => setTab("meds")}>
              <span className="qnav-icon">&#8853;</span>
              <span>Meds</span>
            </button>
            <button className="qnav-btn" onClick={() => setTab("labs")}>
              <span className="qnav-icon">&#9651;</span>
              <span>Labs</span>
            </button>
            <button className="qnav-btn" onClick={() => setTab("codes")}>
              <span className="qnav-icon">&#10070;</span>
              <span>Codes</span>
            </button>
            <button className="qnav-btn" onClick={() => setTab("soap")}>
              <span className="qnav-icon">&rarr;</span>
              <span>SOAP</span>
            </button>
          </div>
        </div>

        {/* Summary Card */}
        <div className="summary-card">
          <div className="summary-header">
            <strong>Summary</strong>
            <span className="summary-time">
              {meetingStart ? formatTime(meetingStart) : ""}
            </span>
          </div>
          <p className="summary-text">
            {data.encounter.chief_complaint && (
              <>
                During the telehealth visit, the patient presented with{" "}
                {data.encounter.chief_complaint.toLowerCase()}.{" "}
              </>
            )}
            {diagnoses.length > 0 && (
              <>
                {diagnoses.length === 1
                  ? `Assessment indicates ${diagnoses[0].description.toLowerCase()}`
                  : `Assessments include ${diagnoses.map((d) => d.description.toLowerCase()).join(", ")}`}
                .{" "}
              </>
            )}
            {prescriptions.length > 0 && (
              <>
                {prescriptions.map((rx) => `${rx.medication_name} ${rx.dosage} ${rx.frequency}`).join("; ")}
                {prescriptions.length === 1 ? " was prescribed" : " were prescribed"}.{" "}
              </>
            )}
            {lab_orders.length > 0 && (
              <>
                Lab orders placed: {lab_orders.map((l) => l.test_name).join(", ")}.{" "}
              </>
            )}
            {referrals.length > 0 && (
              <>
                Referrals: {referrals.map((r) => r.specialty).join(", ")}.
              </>
            )}
          </p>
        </div>

        {/* Patient Details */}
        <div className="patient-details-card">
          <h3>Patient Details</h3>
          <div className="detail-row">
            <span className="detail-label">Allergies</span>
            <span className="detail-value">
              {patient.allergies.length > 0 ? patient.allergies.join(", ") : "None reported"}
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Medications</span>
            <span className="detail-value">
              {patient.medications.length > 0 ? patient.medications.join(", ") : "None reported"}
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Conditions</span>
            <span className="detail-value">
              {patient.conditions.length > 0 ? patient.conditions.join(", ") : "None reported"}
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Visit Date</span>
            <span className="detail-value">
              {meetingStart ? formatDate(meetingStart) : "N/A"}
            </span>
          </div>
          <div className="detail-row">
            <span className="detail-label">Duration</span>
            <span className="detail-value">
              {duration > 0 ? `${duration} min` : "N/A"}
            </span>
          </div>
        </div>
      </div>

      {/* RIGHT PANEL — Assistant Tabs */}
      <div className="analysis-right">
        <div className="assistant-header">
          <h2>Assistant</h2>
        </div>

        {/* Tabs */}
        <div className="assistant-tabs">
          {(
            [
              ["summary", "Summary"],
              ["meds", "Meds"],
              ["labs", "Labs"],
              ["codes", "Codes"],
              ["soap", "SOAP"],
            ] as [Tab, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              className={`atab ${tab === key ? "active" : ""}`}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="assistant-content">
          {/* SUMMARY TAB */}
          {tab === "summary" && (
            <>
              <div className="asection">
                <h4>About this visit</h4>
                <p>{data.encounter.chief_complaint || "Consult"}</p>
              </div>

              <div className="asection">
                <h4>Patient summary</h4>
                <p>
                  Patient is {age ? `a ${age}-year-old` : "a"} {patient.sex} with{" "}
                  {patient.conditions.length > 0
                    ? patient.conditions.join(", ").toLowerCase()
                    : "no documented conditions"}
                  .
                </p>
              </div>

              {diagnoses.length > 0 && (
                <div className="asection">
                  <h4>Diagnoses</h4>
                  {diagnoses.map((dx, i) => (
                    <div key={i} className="a-diagnosis">
                      <div className="a-dx-row">
                        <span className="a-dx-name">{dx.description}</span>
                        {dx.is_primary && <span className="a-primary-badge">PRIMARY</span>}
                      </div>
                      <span className="a-dx-code">{dx.icd10_code}</span>
                      {dx.reasoning && (
                        <p className="a-dx-reasoning">{dx.reasoning}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {referrals.length > 0 && (
                <div className="asection">
                  <h4>Referrals</h4>
                  {referrals.map((ref, i) => (
                    <div key={i} className="a-referral">
                      <strong>{ref.specialty}</strong>
                      <span className="a-urgency">{ref.urgency}</span>
                      {ref.reason && <p className="a-ref-reason">{ref.reason}</p>}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* MEDS TAB */}
          {tab === "meds" && (
            <>
              <div className="asection">
                <h4>Prescribed Medications ({prescriptions.length})</h4>
                {prescriptions.map((rx, i) => (
                  <div key={i} className="a-med-item">
                    <div className="a-med-header">
                      <strong>{rx.medication_name}</strong>
                      <span className={`confidence-badge ${rx.confidence}`}>
                        {rx.confidence}
                      </span>
                    </div>
                    <p className="a-med-detail">
                      {rx.dosage} &middot; {rx.frequency} &middot; {rx.route}
                    </p>
                    <p className="a-med-qty">
                      Qty: {rx.quantity} &bull; Refills: {rx.refills}
                    </p>
                    {rx.instructions && (
                      <p className="a-med-instructions">{rx.instructions}</p>
                    )}
                  </div>
                ))}
                {prescriptions.length === 0 && (
                  <p className="a-empty">No medications prescribed this visit</p>
                )}
              </div>

              {patient.medications.length > 0 && (
                <div className="asection">
                  <h4>Current Medications</h4>
                  {patient.medications.map((med, i) => (
                    <div key={i} className="a-current-med">{med}</div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* LABS TAB */}
          {tab === "labs" && (
            <div className="asection">
              <h4>Lab Orders ({lab_orders.length})</h4>
              {lab_orders.map((lab, i) => (
                <div key={i} className="a-lab-item">
                  <div className="a-lab-header">
                    <strong>{lab.test_name}</strong>
                    {lab.loinc_code && (
                      <span className="a-lab-code">{lab.loinc_code}</span>
                    )}
                  </div>
                  <p className="a-lab-detail">
                    Urgency: {lab.urgency}
                  </p>
                  {lab.reason && <p className="a-lab-reason">{lab.reason}</p>}
                  {lab.special_instructions && (
                    <p className="a-lab-special">{lab.special_instructions}</p>
                  )}
                </div>
              ))}
              {lab_orders.length === 0 && (
                <p className="a-empty">No lab orders placed this visit</p>
              )}
            </div>
          )}

          {/* CODES TAB */}
          {tab === "codes" && (
            <>
              <div className="asection">
                <h4>ICD-10 Diagnosis Codes</h4>
                <div className="codes-list">
                  {diagnoses.map((dx, i) => (
                    <div key={i} className="code-row">
                      <span className="code-value">{dx.icd10_code}</span>
                      <span className="code-desc">{dx.description}</span>
                      {dx.is_primary && <span className="a-primary-badge">Primary</span>}
                    </div>
                  ))}
                  {diagnoses.length === 0 && (
                    <p className="a-empty">No diagnosis codes</p>
                  )}
                </div>
              </div>

              {prescriptions.length > 0 && (
                <div className="asection">
                  <h4>Medication Codes</h4>
                  <div className="codes-list">
                    {prescriptions.map((rx, i) => (
                      <div key={i} className="code-row">
                        <span className="code-value">Rx</span>
                        <span className="code-desc">
                          {rx.medication_name} {rx.dosage} {rx.frequency}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {lab_orders.length > 0 && (
                <div className="asection">
                  <h4>LOINC Lab Codes</h4>
                  <div className="codes-list">
                    {lab_orders.map((lab, i) => (
                      <div key={i} className="code-row">
                        <span className="code-value">{lab.loinc_code || "---"}</span>
                        <span className="code-desc">{lab.test_name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="asection">
                <button className="btn btn-submit-ehr">
                  Submit to EHR
                </button>
                <p className="submit-hint">
                  Send codes, prescriptions, and lab orders to Cerner FHIR
                </p>
              </div>
            </>
          )}

          {/* SOAP TAB */}
          {tab === "soap" && soap_note && (
            <div className="asection">
              <div className="soap-block">
                <h4>Subjective</h4>
                <p>{soap_note.subjective}</p>
              </div>
              <div className="soap-block">
                <h4>Objective</h4>
                <p>{soap_note.objective}</p>
              </div>
              <div className="soap-block">
                <h4>Assessment</h4>
                <p>{soap_note.assessment}</p>
              </div>
              <div className="soap-block">
                <h4>Plan</h4>
                <p>{soap_note.plan}</p>
              </div>
            </div>
          )}
          {tab === "soap" && !soap_note && (
            <p className="a-empty">No SOAP note generated</p>
          )}
        </div>
      </div>
    </div>
  );
}
