import { useState, useEffect } from "react";
import { initAuth } from "./api";
import PatientForm from "./components/PatientForm";
import RecordingPanel from "./components/RecordingPanel";
import TranscriptView from "./components/TranscriptView";
import AnalysisView from "./components/AnalysisView";
import type { Patient, TranscriptSegment, EncounterData } from "./types";
import "./App.css";

type Step = "patient" | "recording" | "transcript" | "analysis";

const STEP_ORDER: Step[] = ["patient", "recording", "transcript", "analysis"];
const STEP_LABELS: Record<Step, string> = {
  patient: "Patient",
  recording: "Record",
  transcript: "Transcript",
  analysis: "Analysis",
};

function App() {
  const [step, setStep] = useState<Step>("patient");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  const [patient, setPatient] = useState<Patient | null>(null);
  const [encounterId, setEncounterId] = useState("");
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [formattedTranscript, setFormattedTranscript] = useState("");
  const [encounterData, setEncounterData] = useState<EncounterData | null>(
    null
  );
  const [meetingStart, setMeetingStart] = useState<Date | null>(null);
  const [meetingEnd, setMeetingEnd] = useState<Date | null>(null);

  useEffect(() => {
    initAuth()
      .then(() => setReady(true))
      .catch((e) => setError(`Failed to connect to API server: ${e.message}`));
  }, []);

  if (error) {
    return (
      <div className="app">
        <div className="error-screen">
          <h2>Connection Error</h2>
          <p>{error}</p>
          <p>
            Make sure the API server is running:{" "}
            <code>uvicorn backend.main:app --port 8000</code>
          </p>
        </div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="app">
        <div className="loading-screen">
          <div className="spinner" />
          <p>Connecting to MediCode...</p>
        </div>
      </div>
    );
  }

  const currentIdx = STEP_ORDER.indexOf(step);

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="logo-icon">+</span>
          <h1>MediCode</h1>
        </div>
        <p className="subtitle">AI Medical Scribe</p>
      </header>

      <nav className="steps">
        {STEP_ORDER.map((s, i) => (
          <button
            key={s}
            className={`step-btn ${step === s ? "active" : ""} ${
              i < currentIdx ? "done" : ""
            }`}
            onClick={() => {
              if (i <= currentIdx) setStep(s);
            }}
          >
            <span className="step-num">{i + 1}</span>
            <span className="step-label">{STEP_LABELS[s]}</span>
          </button>
        ))}
      </nav>

      <main className="main">
        {step === "patient" && (
          <PatientForm
            onSubmit={(p, encId) => {
              setPatient(p);
              setEncounterId(encId);
              setStep("recording");
            }}
          />
        )}
        {step === "recording" && patient && (
          <RecordingPanel
            patient={patient}
            encounterId={encounterId}
            onTranscribed={(segs, formatted, start, end) => {
              setSegments(segs);
              setFormattedTranscript(formatted);
              setMeetingStart(start);
              setMeetingEnd(end);
              setStep("transcript");
            }}
          />
        )}
        {step === "transcript" && (
          <TranscriptView
            segments={segments}
            formattedTranscript={formattedTranscript}
            encounterId={encounterId}
            onAnalyzed={(data) => {
              setEncounterData(data);
              setStep("analysis");
            }}
          />
        )}
        {step === "analysis" && encounterData && patient && (
          <AnalysisView
            data={encounterData}
            patient={patient}
            meetingStart={meetingStart}
            meetingEnd={meetingEnd}
          />
        )}
      </main>
    </div>
  );
}

export default App;
