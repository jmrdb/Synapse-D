/**
 * Longitudinal comparison chart component.
 *
 * Displays time-series data for brain metrics across multiple scan sessions,
 * showing how a patient's brain structure changes over time.
 * This is the core "Digital Twin" differentiator — temporal trajectory tracking.
 *
 * Metrics displayed:
 * - Brain volume (cm³) — atrophy tracking
 * - Hippocampal volume (mm³) — AD biomarker
 * - Cortical thickness (mm) — neurodegeneration
 * - Brain Age Gap (years) — accelerated aging
 *
 * Each chart includes change rate annotation and clinical interpretation.
 */

"use client";

import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid, Area, ComposedChart,
} from "recharts";
import { getLongitudinal, type LongitudinalData } from "@/lib/api";

interface LongitudinalChartProps {
  subjectId: string;
}

const METRIC_CONFIG: Record<string, {
  label: string;
  unit: string;
  color: string;
  decimals: number;
}> = {
  brain_volume: { label: "Brain Volume", unit: "cm³", color: "#4f9cf7", decimals: 1 },
  hippocampus: { label: "Hippocampal Volume", unit: "mm³", color: "#a78bfa", decimals: 0 },
  cortical_thickness: { label: "Cortical Thickness", unit: "mm", color: "#51cf66", decimals: 3 },
  brain_age_gap: { label: "Brain Age Gap", unit: "years", color: "#ffd43b", decimals: 1 },
};

function changeColor(pct: number): string {
  if (Math.abs(pct) < 0.5) return "#51cf66"; // stable
  if (Math.abs(pct) < 1.5) return "#ffd43b"; // mild
  return "#ff6b6b"; // significant
}

/** Single metric time-series chart */
function MetricChart({
  metricKey,
  data,
  change,
}: {
  metricKey: string;
  data: Array<{ date: string; age: number; value: number }>;
  change?: {
    annualized_change: number;
    percent_change: number;
    interpretation: string;
    interval_years: number;
  };
}) {
  const cfg = METRIC_CONFIG[metricKey];
  if (!cfg || data.length === 0) return null;

  const chartData = data.map((d) => ({
    ...d,
    label: d.date.slice(0, 7), // YYYY-MM
  }));

  const values = data.map((d) => d.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const padding = (maxVal - minVal) * 0.2 || maxVal * 0.05;

  return (
    <div style={sectionStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
        <div>
          <h3 style={titleStyle}>{cfg.label}</h3>
          {data.length === 1 && (
            <span style={{ fontSize: "11px", color: "#666" }}>
              다음 스캔 후 변화 추이가 표시됩니다
            </span>
          )}
        </div>
        {change && (
          <div style={{ textAlign: "right" }}>
            <div style={{
              fontSize: "18px",
              fontWeight: 700,
              color: changeColor(change.annualized_change),
            }}>
              {change.annualized_change > 0 ? "+" : ""}
              {change.annualized_change.toFixed(2)}%
              <span style={{ fontSize: "11px", fontWeight: 400 }}>/year</span>
            </div>
            <div style={{ fontSize: "11px", color: "#888" }}>
              {change.interpretation}
            </div>
            <div style={{ fontSize: "10px", color: "#555" }}>
              {change.interval_years.toFixed(1)}년 간 {change.percent_change > 0 ? "+" : ""}
              {change.percent_change.toFixed(1)}%
            </div>
          </div>
        )}
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <ComposedChart data={chartData} margin={{ left: 10, right: 10, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
          <XAxis
            dataKey="label"
            tick={{ fill: "#888", fontSize: 11 }}
            axisLine={{ stroke: "#333" }}
          />
          <YAxis
            domain={[minVal - padding, maxVal + padding]}
            tick={{ fill: "#888", fontSize: 11 }}
            axisLine={{ stroke: "#333" }}
            tickFormatter={(v: number) => v.toFixed(cfg.decimals)}
          />
          <Tooltip
            contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 6, fontSize: 12 }}
            labelStyle={{ color: "#ccc" }}
            formatter={(value: number) => [`${value.toFixed(cfg.decimals)} ${cfg.unit}`, cfg.label]}
          />
          {metricKey === "brain_age_gap" && (
            <ReferenceLine y={0} stroke="#555" strokeDasharray="3 3" label={{ value: "age norm", fill: "#555", fontSize: 10 }} />
          )}
          <Area
            type="monotone"
            dataKey="value"
            fill={cfg.color}
            fillOpacity={0.08}
            stroke="none"
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={cfg.color}
            strokeWidth={2}
            dot={{ fill: cfg.color, r: 4, strokeWidth: 2, stroke: "#1a1a2e" }}
            activeDot={{ r: 6 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Change summary cards */
function ChangeSummary({ changes }: { changes: LongitudinalData["summary"]["changes"] }) {
  if (!changes || changes.length === 0) return null;

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
      gap: "12px",
      marginBottom: "16px",
    }}>
      {changes.map((c) => {
        const cfg = METRIC_CONFIG[c.metric];
        if (!cfg) return null;
        return (
          <div key={c.metric} style={{
            ...sectionStyle,
            padding: "14px",
          }}>
            <div style={{ fontSize: "11px", color: "#888", textTransform: "uppercase", marginBottom: "6px" }}>
              {cfg.label}
            </div>
            <div style={{
              fontSize: "22px",
              fontWeight: 700,
              color: changeColor(c.annualized_change),
            }}>
              {c.annualized_change > 0 ? "+" : ""}{c.annualized_change.toFixed(2)}%
              <span style={{ fontSize: "11px", fontWeight: 400, color: "#888" }}>/yr</span>
            </div>
            <div style={{ fontSize: "11px", color: "#666", marginTop: "4px" }}>
              {c.baseline_value.toFixed(cfg.decimals)} → {c.latest_value.toFixed(cfg.decimals)} {cfg.unit}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Main longitudinal chart component */
export default function LongitudinalChart({ subjectId }: LongitudinalChartProps) {
  const [data, setData] = useState<LongitudinalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await getLongitudinal(subjectId);
        setData(result);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load longitudinal data");
      } finally {
        setLoading(false);
      }
    }
    if (subjectId) fetchData();
  }, [subjectId]);

  if (loading) return <div style={{ color: "#666", textAlign: "center", padding: "20px" }}>Loading...</div>;
  if (error) return <div style={{ color: "#ff6b6b", textAlign: "center", padding: "20px" }}>{error}</div>;
  if (!data || data.timepoint_count === 0) return null;

  const { summary } = data;
  const series = summary.series || {};
  const changes = summary.changes || [];

  // Map changes by metric for easy lookup
  const changeMap = Object.fromEntries(changes.map((c) => [c.metric, c]));

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      {/* Header */}
      <div style={{
        ...sectionStyle,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        <div>
          <h2 style={{ fontSize: "16px", fontWeight: 700, color: "#ccc", margin: 0 }}>
            Longitudinal Tracking
          </h2>
          <div style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}>
            {data.timepoint_count} timepoints
            {summary.baseline_date && summary.latest_date && (
              <> · {summary.baseline_date} ~ {summary.latest_date} ({summary.interval_years?.toFixed(1)}yr)</>
            )}
          </div>
        </div>
        {summary.overall_assessment && (
          <div style={{
            padding: "6px 12px",
            borderRadius: "6px",
            fontSize: "12px",
            fontWeight: 600,
            background: summary.overall_assessment.includes("accelerated") ? "rgba(255,107,107,0.15)" :
                        summary.overall_assessment.includes("concerning") ? "rgba(255,212,59,0.15)" :
                        "rgba(81,207,102,0.15)",
            color: summary.overall_assessment.includes("accelerated") ? "#ff6b6b" :
                   summary.overall_assessment.includes("concerning") ? "#ffd43b" :
                   "#51cf66",
          }}>
            {summary.overall_assessment}
          </div>
        )}
      </div>

      {/* Change summary cards (only with 2+ timepoints) */}
      {changes.length > 0 && <ChangeSummary changes={changes} />}

      {/* Time-series charts */}
      {Object.entries(METRIC_CONFIG).map(([key]) => {
        const seriesData = series[key];
        if (!seriesData || seriesData.length === 0) return null;
        return (
          <MetricChart
            key={key}
            metricKey={key}
            data={seriesData}
            change={changeMap[key]}
          />
        );
      })}

      {/* Single timepoint message */}
      {data.timepoint_count === 1 && summary.message && (
        <div style={{ textAlign: "center", color: "#666", fontSize: "13px", padding: "12px" }}>
          {summary.message}
        </div>
      )}
    </div>
  );
}

const sectionStyle: React.CSSProperties = {
  background: "#1a1a2e",
  borderRadius: "12px",
  padding: "16px",
  border: "1px solid #2a2a3e",
};

const titleStyle: React.CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#ccc",
  margin: 0,
  textTransform: "uppercase" as const,
  letterSpacing: "0.5px",
};
