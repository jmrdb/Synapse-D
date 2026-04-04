/**
 * Brain Age Dashboard - main analysis results view.
 * Displays Brain Age prediction, morphometrics, and 3D visualization.
 */

"use client";

import { useState } from "react";
import BrainViewer from "./BrainViewer";
import MRIUploader from "./MRIUploader";
import type { AnalysisResult } from "@/lib/api";

export default function Dashboard() {
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const brainAge = result?.result?.brain_age;
  const morpho = result?.result?.preprocessing?.morphometrics;
  // NIfTI URL from backend (already sanitized as relative URL)
  const niftiUrl = result?.result?.preprocessing?.brain_extracted_url;

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
        <MRIUploader onAnalysisComplete={setResult} />

        {/* Results Cards */}
        {result?.result && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px" }}>
            {/* Brain Age Card */}
            {brainAge && (
              <div style={cardStyle}>
                <div style={cardLabelStyle}>Predicted Brain Age</div>
                <div style={cardValueStyle}>{brainAge.predicted_age} <span style={{ fontSize: "14px" }}>years</span></div>
                <div style={{ fontSize: "12px", color: "#666" }}>
                  confidence: {(brainAge.confidence * 100).toFixed(1)}%
                </div>
              </div>
            )}

            {/* Brain Age Gap Card */}
            {brainAge?.brain_age_gap !== null && brainAge?.brain_age_gap !== undefined && (
              <div style={cardStyle}>
                <div style={cardLabelStyle}>Brain Age Gap</div>
                <div style={{
                  ...cardValueStyle,
                  color: brainAge.brain_age_gap > 3 ? "#ff6b6b" : brainAge.brain_age_gap < -3 ? "#51cf66" : "#ffd43b",
                }}>
                  {brainAge.brain_age_gap > 0 ? "+" : ""}{brainAge.brain_age_gap} <span style={{ fontSize: "14px" }}>years</span>
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>
                  {brainAge.brain_age_gap > 3 ? "accelerated aging" : brainAge.brain_age_gap < -3 ? "resilient brain" : "normal range"}
                </div>
              </div>
            )}

            {/* Brain Volume Card */}
            {morpho?.total_brain_volume_cm3 && (
              <div style={cardStyle}>
                <div style={cardLabelStyle}>Brain Volume</div>
                <div style={cardValueStyle}>
                  {morpho.total_brain_volume_cm3.toFixed(0)} <span style={{ fontSize: "14px" }}>cm³</span>
                </div>
                <div style={{ fontSize: "12px", color: "#666" }}>total intracranial</div>
              </div>
            )}
          </div>
        )}

        {/* Pipeline Errors */}
        {result?.result?.preprocessing?.errors && result.result.preprocessing.errors.length > 0 && (
          <div style={{ background: "rgba(255,107,107,0.1)", border: "1px solid #ff6b6b33", borderRadius: "8px", padding: "12px" }}>
            <div style={{ fontSize: "12px", color: "#ff6b6b", marginBottom: "4px" }}>Pipeline Warnings</div>
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
