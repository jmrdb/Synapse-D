/**
 * Synapse-D API client.
 * Communicates with the FastAPI backend for MRI analysis.
 */

const API_BASE = "/api/v1";

export interface UploadResponse {
  subject_id: string;
  filename: string;
  size_mb: number;
}

export interface AnalysisResult {
  job_id: string;
  status: string;
  result?: {
    preprocessing: {
      success: boolean;
      morphometrics: {
        total_brain_volume_cm3?: number;
      };
      errors: string[];
    };
    brain_age?: {
      predicted_age: number;
      confidence: number;
      brain_age_gap: number | null;
    };
  };
}

export async function uploadMRI(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

export async function startAnalysis(
  subjectId: string,
  age?: number
): Promise<{ job_id: string; status: string }> {
  const params = age ? `?chronological_age=${age}` : "";
  const res = await fetch(`${API_BASE}/analyze/${subjectId}${params}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`);
  return res.json();
}

export async function getResults(jobId: string): Promise<AnalysisResult> {
  const res = await fetch(`${API_BASE}/results/${jobId}`);
  if (!res.ok) throw new Error(`Results fetch failed: ${res.statusText}`);
  return res.json();
}

export async function healthCheck(): Promise<{ status: string; version: string }> {
  const res = await fetch("/health");
  return res.json();
}
