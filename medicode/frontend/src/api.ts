let authToken = "";

async function jacFetch(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  const resp = await fetch(path, { ...options, headers });
  const data = await resp.json();
  if (!data.ok) {
    throw new Error(data.error || "API error");
  }
  return data.data;
}

export async function initAuth() {
  try {
    const regResp = await fetch("/user/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "medicode", password: "medicode123" }),
    });
    const regData = await regResp.json();
    if (regData.ok) {
      authToken = regData.data.token;
      return;
    }
  } catch {
    // Registration may fail if user exists
  }

  const loginResp = await fetch("/user/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "medicode", password: "medicode123" }),
  });
  const loginData = await loginResp.json();
  if (loginData.ok) {
    authToken = loginData.data.token;
  } else {
    throw new Error("Failed to authenticate with API server");
  }
}

export async function createPatient(patient: {
  first_name: string;
  last_name: string;
  dob: string;
  mrn: string;
  sex: string;
  allergies: string[];
  medications: string[];
  conditions: string[];
}) {
  const data = await jacFetch("/walker/create_patient", {
    method: "POST",
    body: JSON.stringify(patient),
  });
  return data.reports[0];
}

export async function startEncounter(
  patient_mrn: string,
  chief_complaint: string
) {
  const data = await jacFetch("/walker/start_encounter", {
    method: "POST",
    body: JSON.stringify({ patient_mrn, chief_complaint }),
  });
  return data.reports[0];
}

export async function ingestTranscript(
  encounter_id: string,
  full_text: string
) {
  const data = await jacFetch("/walker/ingest_full_transcript", {
    method: "POST",
    body: JSON.stringify({ encounter_id, full_text }),
  });
  return data.reports[0];
}

export async function runAnalysis(encounter_id: string) {
  const data = await jacFetch("/walker/run_analysis", {
    method: "POST",
    body: JSON.stringify({ encounter_id }),
  });
  return data.reports[0];
}

export async function getEncounter(encounter_id: string) {
  const data = await jacFetch("/walker/get_encounter", {
    method: "POST",
    body: JSON.stringify({ encounter_id }),
  });
  return data.reports[0];
}

export async function transcribeAudio(audioBlob: Blob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");

  const resp = await fetch("/api/transcribe", {
    method: "POST",
    body: formData,
  });
  return resp.json();
}
