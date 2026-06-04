import { useState } from "react";
import { createPatient, startEncounter } from "../api";
import type { Patient } from "../types";

interface Props {
  onSubmit: (patient: Patient, encounterId: string) => void;
}

export default function PatientForm({ onSubmit }: Props) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    dob: "",
    sex: "male",
    allergies: "",
    medications: "",
    conditions: "",
    chief_complaint: "",
  });

  const set = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const mrn = `MRN-${Date.now()}`;
      const patient = await createPatient({
        first_name: form.first_name,
        last_name: form.last_name,
        dob: form.dob,
        mrn,
        sex: form.sex,
        allergies: form.allergies
          ? form.allergies.split(",").map((s) => s.trim())
          : [],
        medications: form.medications
          ? form.medications.split(",").map((s) => s.trim())
          : [],
        conditions: form.conditions
          ? form.conditions.split(",").map((s) => s.trim())
          : [],
      });

      const encounter = await startEncounter(mrn, form.chief_complaint);
      onSubmit(patient, encounter._jac_id);
    } catch (err) {
      alert(`Error: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="step-layout">
      {/* Left - Context */}
      <div className="step-sidebar">
        <div className="sidebar-icon">+</div>
        <h2 className="sidebar-title">New Encounter</h2>
        <p className="sidebar-desc">
          Enter the patient's information to begin a new telehealth encounter.
          MediCode will use this context during AI analysis.
        </p>
        <div className="sidebar-steps">
          <div className="sidebar-step active">
            <span className="ss-num">1</span>
            <span>Patient Info</span>
          </div>
          <div className="sidebar-step">
            <span className="ss-num">2</span>
            <span>Record Session</span>
          </div>
          <div className="sidebar-step">
            <span className="ss-num">3</span>
            <span>Review Transcript</span>
          </div>
          <div className="sidebar-step">
            <span className="ss-num">4</span>
            <span>AI Analysis</span>
          </div>
        </div>
      </div>

      {/* Right - Form */}
      <div className="step-content">
        <form onSubmit={handleSubmit}>
          <div className="content-section">
            <h3 className="section-title">Patient Information</h3>
            <div className="form-grid">
              <div className="form-group">
                <label>First Name</label>
                <input
                  required
                  value={form.first_name}
                  onChange={(e) => set("first_name", e.target.value)}
                  placeholder="John"
                />
              </div>
              <div className="form-group">
                <label>Last Name</label>
                <input
                  required
                  value={form.last_name}
                  onChange={(e) => set("last_name", e.target.value)}
                  placeholder="Doe"
                />
              </div>
              <div className="form-group">
                <label>Date of Birth</label>
                <input
                  required
                  type="date"
                  value={form.dob}
                  onChange={(e) => set("dob", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Sex</label>
                <select
                  value={form.sex}
                  onChange={(e) => set("sex", e.target.value)}
                >
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>
            </div>
          </div>

          <div className="content-section">
            <h3 className="section-title">Medical History</h3>
            <div className="form-grid">
              <div className="form-group full-width">
                <label>Allergies</label>
                <input
                  value={form.allergies}
                  onChange={(e) => set("allergies", e.target.value)}
                  placeholder="Penicillin, Sulfa (comma-separated)"
                />
              </div>
              <div className="form-group full-width">
                <label>Current Medications</label>
                <input
                  value={form.medications}
                  onChange={(e) => set("medications", e.target.value)}
                  placeholder="Lisinopril 10mg, Metformin 500mg"
                />
              </div>
              <div className="form-group full-width">
                <label>Active Conditions</label>
                <input
                  value={form.conditions}
                  onChange={(e) => set("conditions", e.target.value)}
                  placeholder="Hypertension, Type 2 Diabetes"
                />
              </div>
            </div>
          </div>

          <div className="content-section">
            <h3 className="section-title">Visit Details</h3>
            <div className="form-group">
              <label>Chief Complaint</label>
              <input
                required
                value={form.chief_complaint}
                onChange={(e) => set("chief_complaint", e.target.value)}
                placeholder="Follow-up for blood pressure management"
              />
            </div>
          </div>

          <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
            {loading ? "Creating..." : "Start Encounter"}
          </button>
        </form>
      </div>
    </div>
  );
}
