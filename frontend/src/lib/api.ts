/**
 * Synapse-D API client.
 * Communicates with the FastAPI backend for MRI analysis.
 */

const API_BASE = "/api/v1";

export interface UploadResponse {
  subject_id: string;
  modality: string;
  filename: string;
  size_mb: number;
}

export type JobStatus = "pending" | "processing" | "submitted" | "completed" | "failed";

export interface AnalysisResult {
  job_id: string;
  status: JobStatus;
  result?: {
    subject_id?: string;
    preprocessing: {
      success: boolean;
      brain_extracted_url?: string;
      registered_url?: string;
      segmentation_url?: string;
      used_fallback?: boolean;
      resolution?: {
        tier: "full" | "standard" | "basic";
        max_voxel_dim_mm: number;
        is_isotropic: boolean;
        modality: string;
        available_features: string[];
        blocked_features: string[];
        warnings: string[];
      };
      morphometrics: {
        total_brain_volume_cm3?: number;
        hippocampus_total_mm3?: number;
        ventricle_total_mm3?: number;
        mean_cortical_thickness_mm?: number;
        subcortical_volumes?: Record<string, number>;
        cortical_thickness_by_region?: Record<string, number>;
        source?: string;
      };
      errors: string[];
    };
    brain_age?: {
      predicted_age: number;
      confidence: number;
      brain_age_gap: number | null;
    } | {
      blocked: true;
      reason: string;
    } | {
      error: string;
    };
    normative?: {
      scores?: Array<{
        metric: string;
        value: number;
        expected: number;
        z_score: number;
        interpretation: string;
      }>;
      overall_z_mean?: number;
    };
    wmh?: {
      wmh_volume_mm3: number;
      wmh_volume_ml: number;
      wmh_count: number;
      fazekas_grade: number;
      fazekas_description: string;
      regional_distribution: Record<string, number>;
      success: boolean;
      used_fallback: boolean;
      errors: string[];
    };
  };
  error?: string;
  detail?: string;
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
): Promise<AnalysisResult> {
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

export interface LongitudinalData {
  subject_id: string;
  timepoint_count: number;
  summary: {
    timepoint_count: number;
    baseline_date?: string;
    latest_date?: string;
    interval_years?: number;
    message?: string;
    overall_assessment?: string;
    series?: Record<string, Array<{ date: string; age: number; value: number }>>;
    changes?: Array<{
      metric: string;
      baseline_value: number;
      latest_value: number;
      absolute_change: number;
      percent_change: number;
      annualized_change: number;
      interval_years: number;
      interpretation: string;
    }>;
  };
}

export async function getLongitudinal(subjectId: string): Promise<LongitudinalData> {
  const res = await fetch(`${API_BASE}/longitudinal/${subjectId}`);
  if (!res.ok) throw new Error(`Longitudinal data fetch failed: ${res.statusText}`);
  return res.json();
}

export async function healthCheck(): Promise<{ status: string; version: string }> {
  const res = await fetch("/health");
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}
