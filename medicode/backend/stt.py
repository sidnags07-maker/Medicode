"""ElevenLabs speech-to-text with speaker diarization + role labeling.

Merges integrations/elevenlabs_stt.jac and the old web/app.py proxy: calls
ElevenLabs, groups words into speaker segments, and labels the most
medical-sounding speaker as the Doctor. Returns the exact shape the React
RecordingPanel expects: {transcript, formatted_transcript, full_text,
speaker_count}.
"""

import os

import requests

ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"

_MEDICAL_TERMS = [
    "diagnos", "prescri", "medicat", "symptom", "blood", "test", "order",
    "referr", "follow", "dosage", "mg", "daily", "exam", "history", "allerg",
]


def _group_segments(words: list[dict]) -> list[dict]:
    """Group consecutive same-speaker words into segments."""
    segments: list[dict] = []
    current_speaker = ""
    current_text = ""
    current_start = 0.0

    for word in words:
        if word.get("type") != "word":
            continue
        speaker = word.get("speaker_id", "unknown")
        word_text = word.get("text", "")
        word_start = word.get("start", 0.0)

        if speaker != current_speaker and current_text:
            segments.append({
                "speaker": current_speaker,
                "text": current_text.strip(),
                "start": current_start,
            })
            current_text = ""
            current_start = word_start

        if not current_text:
            current_start = word_start
        current_speaker = speaker
        current_text += " " + word_text

    if current_text:
        segments.append({
            "speaker": current_speaker,
            "text": current_text.strip(),
            "start": current_start,
        })
    return segments


def _label_speakers(segments: list[dict]) -> dict[str, str]:
    """Heuristic: the speaker using the most medical terminology is the Doctor."""
    speaker_ids = list({s["speaker"] for s in segments})
    speaker_map: dict[str, str] = {}

    if len(speaker_ids) >= 2:
        score: dict[str, int] = {}
        for seg in segments:
            text = seg["text"].lower()
            hits = sum(1 for term in _MEDICAL_TERMS if term in text)
            score[seg["speaker"]] = score.get(seg["speaker"], 0) + hits
        ordered = sorted(speaker_ids, key=lambda s: score.get(s, 0), reverse=True)
        speaker_map[ordered[0]] = "Doctor"
        for sp in ordered[1:]:
            speaker_map[sp] = "Patient"
    elif len(speaker_ids) == 1:
        speaker_map[speaker_ids[0]] = "Speaker"

    return speaker_map


def transcribe_audio(audio_bytes: bytes, filename: str = "recording.webm") -> dict:
    """Transcribe audio and return labeled segments. Raises on API error so the
    caller can return an {error: ...} envelope."""
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    resp = requests.post(
        ELEVENLABS_STT_URL,
        headers={"xi-api-key": api_key},
        files={"file": (filename, audio_bytes, "audio/webm")},
        data={
            "model_id": "scribe_v2",
            "diarize": "true",
            "num_speakers": "2",
            "language_code": "eng",
            "timestamps_granularity": "word",
            "tag_audio_events": "true",
        },
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs API error: {resp.status_code} - {resp.text}"
        )

    result = resp.json()
    words = result.get("words", [])
    full_text = result.get("text", "")

    segments = _group_segments(words)
    speaker_map = _label_speakers(segments)
    speaker_count = len({s["speaker"] for s in segments})

    labeled = [
        {
            "speaker": speaker_map.get(seg["speaker"], seg["speaker"]),
            "text": seg["text"],
            "start": seg["start"],
        }
        for seg in segments
    ]
    formatted = "\n\n".join(f"[{s['speaker']}]: {s['text']}" for s in labeled)

    return {
        "transcript": labeled,
        "formatted_transcript": formatted,
        "full_text": full_text,
        "speaker_count": speaker_count,
    }
