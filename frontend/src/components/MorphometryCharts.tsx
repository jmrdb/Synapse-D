/**
 * Morphometry visualization charts.
 * Displays subcortical volumes (bar chart), normative z-scores (bar chart),
 * and cortical thickness by region (radar-style horizontal bar).
 */

"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, ReferenceLine,
} from "recharts";
import type { AnalysisResult } from "@/lib/api";

interface MorphometryChartsProps {
  result: AnalysisResult;
}

const COLORS = {
  normal: "#4f9cf7",
  warning: "#ffd43b",
  danger: "#ff6b6b",
  positive: "#51cf66",
};

function zColor(z: number): string {
  const abs = Math.abs(z);
  if (abs < 1) return COLORS.normal;
  if (abs < 2) return COLORS.warning;
  return COLORS.danger;
}

/** Subcortical region volumes bar chart */
function SubcorticalChart({ volumes }: { volumes: Record<string, number> }) {
  const data = Object.entries(volumes).map(([name, vol]) => ({
    name: name.replace("Left-", "L-").replace("Right-", "R-"),
    volume: Math.round(vol),
  }));

  return (
    <div style={sectionStyle}>
      <h3 style={titleStyle}>Subcortical Volumes (mm³)</h3>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} layout="vertical" margin={{ left: 100, right: 20 }}>
          <XAxis type="number" tick={{ fill: "#888", fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fill: "#ccc", fontSize: 11 }} width={100} />
          <Tooltip
            contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 6 }}
            labelStyle={{ color: "#ccc" }}
          />
          <Bar dataKey="volume" fill={COLORS.normal} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Normative z-score comparison chart */
function NormativeChart({ scores }: { scores: Array<{ metric: string; z_score: number; interpretation: string }> }) {
  const data = scores.map((s) => ({
    name: s.metric.replace(/_/g, " "),
    z: s.z_score,
    interpretation: s.interpretation,
  }));

  return (
    <div style={sectionStyle}>
      <h3 style={titleStyle}>Normative Comparison (z-score)</h3>
      <p style={{ fontSize: 11, color: "#666", margin: "0 0 8px 0" }}>
        0 = age/sex average | -2 to +2 = normal range
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} layout="vertical" margin={{ left: 120, right: 20 }}>
          <XAxis type="number" domain={[-3, 3]} tick={{ fill: "#888", fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fill: "#ccc", fontSize: 11 }} width={120} />
          <Tooltip
            contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 6 }}
            formatter={(value: number, _name: string, props: any) => [
              `z = ${value}`,
              props.payload.interpretation,
            ]}
          />
          <ReferenceLine x={0} stroke="#555" />
          <ReferenceLine x={-2} stroke="#ff6b6b33" strokeDasharray="3 3" />
          <ReferenceLine x={2} stroke="#ff6b6b33" strokeDasharray="3 3" />
          <Bar dataKey="z" radius={[0, 4, 4, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={zColor(entry.z)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Cortical thickness by region (horizontal bar) */
function ThicknessChart({ regions }: { regions: Record<string, number> }) {
  const data = Object.entries(regions).map(([name, val]) => ({
    name: name.replace("lh_", "L ").replace("rh_", "R "),
    thickness: val,
  })).sort((a, b) => b.thickness - a.thickness);

  return (
    <div style={sectionStyle}>
      <h3 style={titleStyle}>Cortical Thickness (mm)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} layout="vertical" margin={{ left: 120, right: 20 }}>
          <XAxis type="number" domain={[0, 3.5]} tick={{ fill: "#888", fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fill: "#ccc", fontSize: 11 }} width={120} />
          <Tooltip
            contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 6 }}
          />
          <Bar dataKey="thickness" fill="#a78bfa" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function MorphometryCharts({ result }: MorphometryChartsProps) {
  const morpho = result.result?.preprocessing?.morphometrics;
  const normative = result.result?.normative;

  if (!morpho) return null;

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      {/* Normative z-scores */}
      {normative?.scores && normative.scores.length > 0 && (
        <NormativeChart scores={normative.scores} />
      )}

      {/* Subcortical volumes */}
      {morpho.subcortical_volumes && (
        <SubcorticalChart volumes={morpho.subcortical_volumes} />
      )}

      {/* Cortical thickness */}
      {morpho.cortical_thickness_by_region && (
        <ThicknessChart regions={morpho.cortical_thickness_by_region} />
      )}
    </div>
  );
}

const sectionStyle: React.CSSProperties = {
  background: "#1a1a2e",
  borderRadius: "12px",
  padding: "16px 12px",
  border: "1px solid #2a2a3e",
};

const titleStyle: React.CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#ccc",
  margin: "0 0 12px 0",
  textTransform: "uppercase" as const,
  letterSpacing: "0.5px",
};
