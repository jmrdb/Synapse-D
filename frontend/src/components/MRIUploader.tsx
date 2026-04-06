/**
 * MRI file upload component with drag-and-drop support.
 * Handles T1-weighted NIfTI file upload to the backend.
 */

"use client";

import { useCallback, useState } from "react";
import { uploadMRI, startAnalysis, getResults, type AnalysisResult } from "@/lib/api";

interface MRIUploaderProps {
  onAnalysisComplete: (result: AnalysisResult) => void;
}

export default function MRIUploader({ onAnalysisComplete }: MRIUploaderProps) {
  const [status, setStatus] = useState<"idle" | "uploading" | "analyzing" | "done" | "error">("idle");
  const [message, setMessage] = useState("");
  const [age, setAge] = useState<string>("");
  const [sex, setSex] = useState<string>("M");
  const [modality, setModality] = useState<string>("T1w");
  const [subjectId, setSubjectId] = useState<string>("");
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.endsWith(".nii") && !file.name.endsWith(".nii.gz")) {
      setStatus("error");
      setMessage("NIfTI (.nii / .nii.gz) 파일만 업로드 가능합니다.");
      return;
    }

    try {
      // Upload
      setStatus("uploading");
      setMessage(`업로드 중: ${file.name}`);
      const upload = await uploadMRI(file, modality, subjectId || undefined);
      setSubjectId(upload.subject_id);
      setMessage(`업로드 완료 (${upload.size_mb} MB, ${upload.modality}). 분석 시작...`);

      // Analyze (async — Celery worker processes in background)
      setStatus("analyzing");
      const chronoAge = age ? parseFloat(age) : undefined;
      const job = await startAnalysis(upload.subject_id, chronoAge, sex || undefined);

      // If already completed (sync fallback), skip polling
      if (job.status === "completed") {
        setStatus("done");
        setMessage("분석 완료");
        onAnalysisComplete(job as AnalysisResult);
        return;
      }

      // Poll for results (max 30 min, 3s interval)
      setMessage("전처리 파이프라인 실행 중...");
      const MAX_POLLS = 600; // 30 min / 3s
      let result: AnalysisResult | null = null;
      for (let i = 0; i < MAX_POLLS; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        try {
          result = await getResults(job.job_id);
        } catch {
          // Network error — retry silently
          continue;
        }
        if (result.status === "completed" || result.status === "failed") break;
        if (result.status === "processing") {
          setMessage("뇌 영상 분석 중...");
        }
      }

      if (!result || result.status !== "completed") {
        throw new Error(result?.status === "failed" ? "분석 실패" : "분석 시간 초과");
      }

      setStatus("done");
      setMessage("분석 완료");
      onAnalysisComplete(result);
    } catch (err) {
      setStatus("error");
      setMessage(`오류: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    }
  }, [age, sex, modality, subjectId, onAnalysisComplete]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div style={{ maxWidth: "500px", margin: "0 auto" }}>
      {/* Modality + Sex selection */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "12px" }}>
        <div>
          <label style={{ fontSize: "14px", color: "#888" }}>모달리티</label>
          <select
            value={modality}
            onChange={(e) => setModality(e.target.value)}
            style={inputStyle}
          >
            <option value="T1w">T1w</option>
            <option value="FLAIR">FLAIR</option>
            <option value="T2w">T2w</option>
            <option value="SWI">SWI</option>
            <option value="DWI">DWI</option>
          </select>
        </div>
        <div>
          <label style={{ fontSize: "14px", color: "#888" }}>성별</label>
          <select
            value={sex}
            onChange={(e) => setSex(e.target.value)}
            style={inputStyle}
          >
            <option value="M">남성 (M)</option>
            <option value="F">여성 (F)</option>
          </select>
        </div>
      </div>

      {/* Age input */}
      <div style={{ marginBottom: "12px" }}>
        <label style={{ fontSize: "14px", color: "#888" }}>
          실제 나이 (선택, Brain Age Gap 계산용)
        </label>
        <input
          type="number"
          value={age}
          onChange={(e) => setAge(e.target.value)}
          placeholder="예: 45"
          style={{
            width: "100%",
            padding: "8px 12px",
            marginTop: "4px",
            border: "1px solid #333",
            borderRadius: "6px",
            background: "#1a1a2e",
            color: "white",
            fontSize: "14px",
          }}
        />
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = ".nii,.nii.gz";
          input.onchange = (e) => {
            const file = (e.target as HTMLInputElement).files?.[0];
            if (file) handleFile(file);
          };
          input.click();
        }}
        style={{
          border: `2px dashed ${dragOver ? "#4f9cf7" : "#333"}`,
          borderRadius: "12px",
          padding: "40px 20px",
          textAlign: "center",
          cursor: "pointer",
          background: dragOver ? "rgba(79,156,247,0.1)" : "transparent",
          transition: "all 0.2s",
        }}
      >
        <div style={{ fontSize: "32px", marginBottom: "8px" }}>
          {status === "uploading" ? "..." : status === "analyzing" ? "..." : ""}
        </div>
        <div style={{ fontSize: "14px", color: "#888" }}>
          {status === "idle" && `${modality} MRI 파일을 드래그하거나 클릭하여 업로드`}
          {status === "uploading" && message}
          {status === "analyzing" && message}
          {status === "done" && message}
          {status === "error" && <span style={{ color: "#ff6b6b" }}>{message}</span>}
        </div>
        <div style={{ fontSize: "12px", color: "#555", marginTop: "8px" }}>
          지원 형식: .nii, .nii.gz (T1w / FLAIR / T2w / SWI / DWI)
        </div>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "8px 12px",
  marginTop: "4px",
  border: "1px solid #333",
  borderRadius: "6px",
  background: "#1a1a2e",
  color: "white",
  fontSize: "14px",
};
