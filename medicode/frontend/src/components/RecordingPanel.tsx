import { useState, useRef, useEffect } from "react";
import { transcribeAudio } from "../api";
import type { Patient, TranscriptSegment } from "../types";

interface Props {
  patient: Patient;
  encounterId: string;
  onTranscribed: (
    segments: TranscriptSegment[],
    formatted: string,
    start: Date,
    end: Date
  ) => void;
}

export default function RecordingPanel({
  patient,
  onTranscribed,
}: Props) {
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);
  const startTimeRef = useRef<Date>(new Date());

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });

      chunks.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };

      recorder.start(1000);
      mediaRecorder.current = recorder;
      startTimeRef.current = new Date();
      setRecording(true);
      setElapsed(0);

      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      alert(`Microphone access denied: ${err}`);
    }
  };

  const stopRecording = () => {
    if (!mediaRecorder.current) return;

    const endTime = new Date();

    mediaRecorder.current.onstop = async () => {
      if (timerRef.current) clearInterval(timerRef.current);
      setRecording(false);
      setProcessing(true);

      const blob = new Blob(chunks.current, { type: "audio/webm" });

      try {
        const result = await transcribeAudio(blob);
        if (result.error) {
          alert(`Transcription error: ${result.error}`);
          setProcessing(false);
          return;
        }
        onTranscribed(
          result.transcript,
          result.formatted_transcript,
          startTimeRef.current,
          endTime
        );
      } catch (err) {
        alert(`Error: ${err}`);
        setProcessing(false);
      }
    };

    mediaRecorder.current.stop();
    mediaRecorder.current.stream.getTracks().forEach((t) => t.stop());
  };

  if (processing) {
    return (
      <div className="step-layout">
        <div className="step-sidebar">
          <div className="sidebar-icon-pulse" />
          <h2 className="sidebar-title">Transcribing</h2>
          <p className="sidebar-desc">
            Audio is being processed by ElevenLabs with speaker diarization.
            This usually takes 15-30 seconds.
          </p>
        </div>
        <div className="step-content">
          <div className="processing">
            <div className="spinner" />
            <h2>Processing Audio...</h2>
            <p>Transcribing with speaker diarization</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="step-layout">
      {/* Left - Patient context */}
      <div className="step-sidebar">
        <div className="patient-avatar-sm">
          {patient.first_name[0]}{patient.last_name[0]}
        </div>
        <h2 className="sidebar-title">
          {patient.first_name} {patient.last_name}
        </h2>
        <p className="sidebar-desc">
          {patient.sex === "male" ? "M" : "F"} &bull; DOB: {patient.dob}
        </p>

        {patient.allergies.length > 0 && (
          <div className="sidebar-info-block">
            <span className="sidebar-info-label">Allergies</span>
            <span className="sidebar-info-value danger-text">
              {patient.allergies.join(", ")}
            </span>
          </div>
        )}

        {patient.medications.length > 0 && (
          <div className="sidebar-info-block">
            <span className="sidebar-info-label">Medications</span>
            <span className="sidebar-info-value">
              {patient.medications.join(", ")}
            </span>
          </div>
        )}

        {patient.conditions.length > 0 && (
          <div className="sidebar-info-block">
            <span className="sidebar-info-label">Conditions</span>
            <span className="sidebar-info-value">
              {patient.conditions.join(", ")}
            </span>
          </div>
        )}
      </div>

      {/* Right - Recording */}
      <div className="step-content">
        <div className="content-section" style={{ textAlign: "center" }}>
          <h3 className="section-title" style={{ textAlign: "center" }}>
            Record Telehealth Session
          </h3>
          <p className="section-hint">
            Start your telehealth call, then click the microphone to begin
            recording. MediCode captures audio from your device microphone.
          </p>
        </div>

        <div className="recording-area">
          <button
            className={`record-btn ${recording ? "recording" : ""}`}
            onClick={recording ? stopRecording : startRecording}
          >
            <span className="mic-icon">
              {recording ? "\u23F9" : "\uD83C\uDF99"}
            </span>
          </button>

          <div className="timer">{formatTime(elapsed)}</div>

          <p className="recording-status">
            {recording
              ? "Recording in progress..."
              : "Click to start recording"}
          </p>

          {recording && (
            <button className="btn btn-danger" onClick={stopRecording}>
              Stop Recording
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
