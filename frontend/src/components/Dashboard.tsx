/**
 * Brain Age Dashboard - main analysis results view.
 * Displays Brain Age prediction, morphometrics, normative comparison,
 * and 3D brain visualization.
 */

"use client";

import { useState } from "react";
import BrainViewer from "./BrainViewer";
import LongitudinalChart from "./LongitudinalChart";
import MRIUploader from "./MRIUploader";
import MorphometryCharts from "./MorphometryCharts";
import type { AnalysisResult } from "@/lib/api";

export default function Dashboard() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [subjectId, setSubjectId] = useState<string | null>(null);
  const [longitudinalKey, setLongitudinalKey] = useState(0);

  const brainAge = result?.result?.brain_age;
  const morpho = result?.result?.preprocessing?.morphometrics;
  const wmh = result?.result?.wmh;
  const normative = result?.result?.normative;
  const niftiUrl = result?.result?.preprocessing?.brain_extracted_url;
  const usedFallback = result?.result?.preprocessing?.used_fallback;
  const resolution = result?.result?.preprocessing?.resolution;
  const tier = resolution?.tier as string | undefined;
  const blockedBrainAge = result?.result?.brain_age && "blocked" in result.result.brain_age;

  return (
    <div style={{ minHeight: "100vh", background: "#0f0f1a", color: "white", padding: "24px" }}>
      {/* Header */}
      <header style={{ textAlign: "center", marginBottom: "32px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: 700, letterSpacing: "-0.5px" }}>
          Synapse-D
        </h1>
        <p style={{ fontSize: "14px", color: "#666", marginTop: "4px" }}>
          Brain Digital Twin Platform
        </p>
      </header>

      <div style={{ maxWidth: "900px", margin: "0 auto", display: "grid", gap: "24px" }}>
        {/* 3D Brain Viewer */}
        <BrainViewer
          niftiUrl={niftiUrl}
          brainAge={brainAge?.predicted_age}
          confidence={brainAge?.confidence}
        />

        {/* Upload Section */}
        <MRIUploader onAnalysisComplete={(r) => {
          setResult(r);
          const sid = r.result?.subject_id;
          if (sid) {
            setSubjectId(sid);
            setLongitudinalKey((k) => k + 1);
          }
        }} />

        {/* Summary Cards */}
        {result?.result && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
            {/* Brain Age Card — only if not blocked */}
            {brainAge && !blockedBrainAge && "predicted_age" in brainAge && (
              <div style={cardStyle}>
                <div style={cardLabelStyle}>Predicted Brain Age</div>
                <div style={cardValueStyle}>
                  {brainAge.predicted_age} <span style={{ fontSize: "14px" }}>years</span>
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>
                  confidence: {(brainAge.confidence * 100).toFixed(1)}%
                </div>
              </div>
            )}

            {/* Brain Age Gap Card */}
            {brainAge && !blockedBrainAge && brainAge.brain_age_gap != null && (
              <div style={cardStyle}>
                <div style={cardLabelStyle}>Brain Age Gap</div>
                <div style={{
                  ...cardValueStyle,
                  color: brainAge.brain_age_gap > 3 ? "#ff6b6b"
                    : brainAge.brain_age_gap < -3 ? "#51cf66" : "#ffd43b",
                }}>
                  {brainAge.brain_age_gap > 0 ? "+" : ""}{brainAge.brain_age_gap}
                  <span style={{ fontSize: "14px" }}> years</span>
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>
                  {brainAge.brain_age_gap > 3 ? "accelerated aging"
                    : brainAge.brain_age_gap < -3 ? "resilient brain" : "normal range"}
                </div>
              </div>
            )}

            {/* Brain Volume Card */}
            {morpho?.total_brain_volume_cm3 && (
              <div style={cardStyle}>
                <div style={cardLabelStyle}>Brain Volume</div>
                <div style={cardValueStyle}>
                  {morpho.total_brain_volume_cm3.toFixed(0)}
                  <span style={{ fontSize: "14px" }}> cm³</span>
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>total intracranial</div>
              </div>
            )}

            {/* Normative Overall Card */}
            {normative?.overall_z_mean != null && (
              <div style={cardStyle}>
                <div style={cardLabelStyle}>Normative Score</div>
                <div style={{
                  ...cardValueStyle,
                  color: Math.abs(normative.overall_z_mean) < 1 ? "#51cf66"
                    : Math.abs(normative.overall_z_mean) < 2 ? "#ffd43b" : "#ff6b6b",
                }}>
                  {normative.overall_z_mean > 0 ? "+" : ""}
                  {normative.overall_z_mean.toFixed(1)}
                  <span style={{ fontSize: "14px" }}> z</span>
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>
                  mean deviation from age norm
                </div>
              </div>
            )}

            {/* WMH Card — show success or explicit failure */}
            {wmh && (
              <div style={cardStyle}>
                <div style={cardLabelStyle}>WMH Burden</div>
                {wmh.success ? (
                  <>
                    <div style={{
                      ...cardValueStyle,
                      color: wmh.fazekas_grade <= 1 ? "#51cf66"
                        : wmh.fazekas_grade === 2 ? "#ffd43b" : "#ff6b6b",
                    }}>
                      {wmh.wmh_volume_ml?.toFixed(1)}
                      <span style={{ fontSize: "14px" }}> mL</span>
                    </div>
                    <div style={{ fontSize: "12px", color: "#666" }}>
                      Fazekas {wmh.fazekas_grade} · {wmh.wmh_count} lesions
                    </div>
                  </>
                ) : (
                  <div style={{ marginTop: "8px" }}>
                    <div style={{ color: "#ff8787", fontSize: "14px" }}>
                      WMH 분석 실패
                    </div>
                    <div style={{ fontSize: "12px", color: "#888", marginTop: "4px" }}>
                      {wmh.errors?.[0] || "알 수 없는 오류"}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Resolution Tier Badge */}
        {tier && (
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            background: "#1a1a2e",
            borderRadius: "8px",
            padding: "12px 16px",
            border: `1px solid ${tier === "full" ? "#51cf6633" : tier === "standard" ? "#ffd43b33" : "#ff6b6b33"}`,
          }}>
            <span style={{
              padding: "4px 10px",
              borderRadius: "4px",
              fontSize: "11px",
              fontWeight: 700,
              textTransform: "uppercase",
              background: tier === "full" ? "#51cf66" : tier === "standard" ? "#ffd43b" : "#ff6b6b",
              color: "#000",
            }}>
              {tier}
            </span>
            <div>
              <span style={{ fontSize: "13px", color: "#ccc" }}>
                {resolution?.max_voxel_dim_mm?.toFixed(1)}mm
                {resolution?.is_isotropic ? " isotropic" : " anisotropic"}
                {" · "}
                {resolution?.modality}
              </span>
              {(resolution?.blocked_features?.length ?? 0) > 0 && (
                <div style={{ fontSize: "11px", color: "#ff8787", marginTop: "2px" }}>
                  차단: {resolution.blocked_features.join(", ")}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Blocked Brain Age notice */}
        {blockedBrainAge && (
          <div style={{
            background: "rgba(255,107,107,0.08)",
            border: "1px solid #ff6b6b22",
            borderRadius: "8px",
            padding: "12px",
          }}>
            <div style={{ fontSize: "13px", color: "#ff8787" }}>
              Brain Age 예측이 차단되었습니다: {(result?.result?.brain_age as any)?.reason}
            </div>
          </div>
        )}

        {/* Morphometry Charts */}
        {result && <MorphometryCharts result={result} />}

        {/* Longitudinal Tracking */}
        {subjectId && (
          <LongitudinalChart key={longitudinalKey} subjectId={subjectId} />
        )}

        {/* Fallback Warning */}
        {usedFallback && (
          <div style={{
            background: "rgba(255,215,0,0.1)",
            border: "1px solid #ffd43b33",
            borderRadius: "8px",
            padding: "12px",
          }}>
            <div style={{ fontSize: "12px", color: "#ffd43b", marginBottom: "4px" }}>
              Development Mode
            </div>
            <div style={{ fontSize: "13px", color: "#ffe066" }}>
              HD-BET 미설치로 근사 뇌 추출을 사용했습니다. 결과는 참고용이며 정확하지 않습니다.
            </div>
          </div>
        )}

        {/* Pipeline Errors */}
        {result?.result?.preprocessing?.errors && result.result.preprocessing.errors.length > 0 && (
          <div style={{
            background: "rgba(255,107,107,0.1)",
            border: "1px solid #ff6b6b33",
            borderRadius: "8px",
            padding: "12px",
          }}>
            <div style={{ fontSize: "12px", color: "#ff6b6b", marginBottom: "4px" }}>
              Pipeline Warnings
            </div>
            {result.result.preprocessing.errors.map((err, i) => (
              <div key={i} style={{ fontSize: "13px", color: "#ff8787" }}>{err}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: "#1a1a2e",
  borderRadius: "12px",
  padding: "20px",
  border: "1px solid #2a2a3e",
};

const cardLabelStyle: React.CSSProperties = {
  fontSize: "12px",
  color: "#666",
  marginBottom: "8px",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
};

const cardValueStyle: React.CSSProperties = {
  fontSize: "32px",
  fontWeight: 700,
  color: "#4f9cf7",
  marginBottom: "4px",
};
