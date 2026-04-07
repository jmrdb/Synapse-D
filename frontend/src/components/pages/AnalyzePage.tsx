/**
 * New Analysis page — upload MRI files and start analysis.
 * Supports multi-modality upload to the same subject.
 */

"use client";

import { useCallback, useState } from "react";
import { uploadMRI, startAnalysis, getResults, type AnalysisResult } from "@/lib/api";

interface AnalyzePageProps {
  onComplete: (subjectId: string) => void;
}

type Step = "upload" | "config" | "analyzing" | "done";

export default function AnalyzePage({ onComplete }: AnalyzePageProps) {
  const [step, setStep] = useState<Step>("upload");
  const [subjectId, setSubjectId] = useState<string>("");
  const [uploads, setUploads] = useState<Array<{ modality: string; filename: string; size: number }>>([]);
  const [modality, setModality] = useState("T1w");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("M");
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");

  const handleUpload = useCallback(async (file: File) => {
    if (!file.name.endsWith(".nii") && !file.name.endsWith(".nii.gz")) {
      setError("NIfTI (.nii / .nii.gz) 파일만 지원합니다.");
      return;
    }
    setError("");

    try {
      const result = await uploadMRI(file, modality, subjectId || undefined);
      setSubjectId(result.subject_id);
      setUploads((prev) => [...prev, {
        modality: result.modality,
        filename: result.filename,
        size: result.size_mb,
      }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "업로드 실패");
    }
  }, [modality, subjectId]);

  const handleAnalyze = useCallback(async () => {
    if (!subjectId) return;
    setStep("analyzing");
    setProgress("분석 제출 중...");

    try {
      const chronoAge = age ? parseFloat(age) : undefined;
      const job = await startAnalysis(subjectId, chronoAge, sex);

      if (job.status === "completed") {
        setStep("done");
        return;
      }

      // Poll
      setProgress("HD-BET 뇌 추출 처리 중... (CPU ~8분 소요)");
      const MAX_POLLS = 600;
      for (let i = 0; i < MAX_POLLS; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        try {
          const result = await getResults(job.job_id);
          if (result.status === "completed") {
            setStep("done");
            return;
          }
          if (result.status === "failed") {
            setError("분석 실패");
            setStep("upload");
            return;
          }
          if (result.status === "processing") {
            setProgress(`분석 진행 중... (${Math.round(i * 3 / 60)}분 경과)`);
          }
        } catch {
          // Network error — retry silently
        }
      }
      setError("분석 시간 초과");
      setStep("upload");
    } catch (e) {
      setError(e instanceof Error ? e.message : "분석 실패");
      setStep("upload");
    }
  }, [subjectId, age, sex]);

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Progress Steps */}
      <div className="flex items-center gap-2">
        {(["upload", "config", "analyzing", "done"] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold
              ${step === s ? "bg-brand-500 text-white" :
                (["upload", "config", "analyzing", "done"].indexOf(step) > i)
                  ? "bg-green-500/30 text-green-400" : "bg-surface-hover text-gray-500"}`}>
              {["upload", "config", "analyzing", "done"].indexOf(step) > i ? "✓" : i + 1}
            </div>
            {i < 3 && <div className={`w-12 h-0.5 ${
              ["upload", "config", "analyzing", "done"].indexOf(step) > i
                ? "bg-green-500/50" : "bg-surface-border"}`} />}
          </div>
        ))}
      </div>

      {/* Step 1: Upload */}
      {(step === "upload" || step === "config") && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">
            1. MRI 파일 업로드
          </h3>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">모달리티</label>
              <select value={modality} onChange={(e) => setModality(e.target.value)} className="select">
                <option value="T1w">T1w (구조)</option>
                <option value="FLAIR">FLAIR (백질 병변)</option>
                <option value="SWI">SWI (미세출혈)</option>
                <option value="T2w">T2w</option>
                <option value="DWI">DWI (뇌졸중)</option>
                <option value="dMRI">dMRI (트랙토그래피)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Subject</label>
              <input
                value={subjectId}
                readOnly
                placeholder="자동 생성"
                className="input text-gray-400"
              />
            </div>
          </div>

          {/* Drop zone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const file = e.dataTransfer.files[0];
              if (file) handleUpload(file);
            }}
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = ".nii,.nii.gz";
              input.onchange = (e) => {
                const file = (e.target as HTMLInputElement).files?.[0];
                if (file) handleUpload(file);
              };
              input.click();
            }}
            className="border-2 border-dashed border-surface-border rounded-xl p-8
                       text-center cursor-pointer hover:border-brand-400/50
                       hover:bg-brand-500/5 transition-all"
          >
            <div className="text-3xl mb-2 opacity-50">📁</div>
            <div className="text-sm text-gray-400">
              {modality} MRI 파일을 드래그하거나 클릭
            </div>
            <div className="text-xs text-gray-600 mt-1">
              .nii, .nii.gz
            </div>
          </div>

          {/* Uploaded files */}
          {uploads.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="text-xs text-gray-500 uppercase">업로드 완료</div>
              {uploads.map((u, i) => (
                <div key={i} className="flex items-center gap-3 bg-surface rounded-lg px-3 py-2">
                  <span className="badge badge-blue">{u.modality}</span>
                  <span className="text-sm text-gray-300 flex-1 truncate">{u.filename}</span>
                  <span className="text-xs text-gray-500">{u.size}MB</span>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="mt-3 text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          {uploads.length > 0 && (
            <button onClick={() => setStep("config")} className="btn-primary mt-4 w-full">
              다음: 분석 설정 →
            </button>
          )}
        </div>
      )}

      {/* Step 2: Config */}
      {step === "config" && (
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4">
            2. 분석 설정
          </h3>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">나이</label>
              <input
                type="number" min="0" max="150"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                placeholder="예: 65"
                className="input"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">성별</label>
              <select value={sex} onChange={(e) => setSex(e.target.value)} className="select">
                <option value="M">남성 (M)</option>
                <option value="F">여성 (F)</option>
              </select>
            </div>
          </div>

          <div className="mt-4 p-3 bg-surface rounded-lg text-xs text-gray-500">
            분석 항목: Brain Age, Morphometry, Normative Comparison
            {uploads.some((u) => u.modality === "FLAIR") && ", WMH Segmentation"}
            {uploads.some((u) => u.modality === "SWI") && ", Microbleed Detection"}
            {uploads.some((u) => u.modality === "dMRI") && ", Tractography Connectome"}
          </div>

          <button onClick={handleAnalyze} className="btn-primary mt-4 w-full">
            분석 시작 🚀
          </button>
        </div>
      )}

      {/* Step 3: Analyzing */}
      {step === "analyzing" && (
        <div className="card text-center py-12">
          <div className="text-5xl mb-4 animate-pulse">🧠</div>
          <h3 className="text-lg font-semibold text-white mb-2">분석 진행 중</h3>
          <p className="text-sm text-gray-400 mb-4">{progress}</p>
          <div className="w-64 mx-auto h-1.5 bg-surface-border rounded-full overflow-hidden">
            <div className="h-full bg-brand-400 rounded-full animate-pulse" style={{ width: "60%" }} />
          </div>
          <p className="text-xs text-gray-600 mt-4">
            HD-BET 뇌 추출은 CPU에서 약 8분 소요됩니다
          </p>
        </div>
      )}

      {/* Step 4: Done */}
      {step === "done" && (
        <div className="card text-center py-12">
          <div className="text-5xl mb-4">✅</div>
          <h3 className="text-lg font-semibold text-white mb-2">분석 완료</h3>
          <p className="text-sm text-gray-400 mb-6">
            Subject: <span className="font-mono text-brand-400">{subjectId}</span>
          </p>
          <button onClick={() => onComplete(subjectId)} className="btn-primary">
            결과 보기 →
          </button>
        </div>
      )}
    </div>
  );
}
