import { useState } from "react";
import { ingestTranscript, runAnalysis, getEncounter } from "../api";
import type { TranscriptSegment, EncounterData } from "../types";

interface Props {
  segments: TranscriptSegment[];
  formattedTranscript: string;
  encounterId: string;
  onAnalyzed: (data: EncounterData) => void;
}

export default function TranscriptView({
  segments,
  formattedTranscript,
  encounterId,
  onAnalyzed,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      setStatus("Ingesting transcript into graph...");
      await ingestTranscript(encounterId, formattedTranscript);

      setStatus("Running AI analysis (this may take 30-60 seconds)...");
      await runAnalysis(encounterId);

      setStatus("Loading results...");
      const data = await getEncounter(encounterId);
      onAnalyzed(data);
    } catch (err) {
      alert(`Analysis error: ${err}`);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="step-layout">
        <div className="step-sidebar">
          <div className="sidebar-icon-pulse" />
          <h2 className="sidebar-title">Analyzing</h2>
          <p className="sidebar-desc">
            Claude AI is extracting clinical data from the transcript.
          </p>
          <div className="sidebar-steps">
            <div className="sidebar-step done">
              <span className="ss-num ss-done">&#10003;</span>
              <span>Transcript ingested</span>
            </div>
            <div className="sidebar-step active">
              <span className="ss-num">2</span>
              <span>AI extraction</span>
            </div>
            <div className="sidebar-step">
              <span className="ss-num">3</span>
              <span>Generate SOAP note</span>
            </div>
          </div>
        </div>
        <div className="step-content">
          <div className="processing">
            <div className="spinner" />
            <h2>Analyzing Encounter</h2>
            <p>{status}</p>
            <p className="section-hint">
              Extracting diagnoses, prescriptions, lab orders, and generating SOAP note
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Count speakers
  const doctorCount = segments.filter(
    (s) => s.speaker.toLowerCase() === "doctor"
  ).length;
  const patientCount = segments.filter(
    (s) => s.speaker.toLowerCase() === "patient"
  ).length;

  return (
    <div className="step-layout">
      {/* Left - Stats */}
      <div className="step-sidebar">
        <h2 className="sidebar-title">Transcript</h2>
        <p className="sidebar-desc">
          Review the transcription before running AI analysis.
        </p>

        <div className="sidebar-info-block">
          <span className="sidebar-info-label">Segments</span>
          <span className="sidebar-info-value">{segments.length}</span>
        </div>
        <div className="sidebar-info-block">
          <span className="sidebar-info-label">Doctor turns</span>
          <span className="sidebar-info-value accent-text">{doctorCount}</span>
        </div>
        <div className="sidebar-info-block">
          <span className="sidebar-info-label">Patient turns</span>
          <span className="sidebar-info-value success-text">{patientCount}</span>
        </div>

        <div style={{ marginTop: 24 }}>
          <button
            className="btn btn-primary btn-lg"
            onClick={handleAnalyze}
            style={{ width: "100%" }}
          >
            Run AI Analysis
          </button>
        </div>
      </div>

      {/* Right - Transcript */}
      <div className="step-content">
        <div className="content-section">
          <h3 className="section-title">
            Conversation ({segments.length} segments)
          </h3>
        </div>
        <div className="transcript-container">
          {segments.map((seg, i) => (
            <div
              key={i}
              className={`segment ${
                seg.speaker.toLowerCase() === "doctor" ? "doctor" : "patient"
              }`}
            >
              <div className="segment-speaker">
                {seg.speaker}
                <span className="segment-time">
                  {Math.floor(seg.start / 60)}:
                  {String(Math.floor(seg.start % 60)).padStart(2, "0")}
                </span>
              </div>
              <div className="segment-text">{seg.text}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
