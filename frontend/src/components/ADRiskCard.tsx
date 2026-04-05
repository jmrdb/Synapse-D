/**
 * AD/MCI Risk Assessment card and biomarker contribution chart.
 * Displays risk score (0-100), risk level, classification probabilities,
 * and per-biomarker SHAP-like contribution breakdown.
 */

"use client";

import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie,
} from "recharts";

export interface ADRiskData {
  risk_score: number;
  risk_level: string;
  classification: string;
  probabilities: Record<string, number>;
  biomarker_contributions: Array<{
    biomarker: string;
    z_score: number;
    risk_contribution: number;
    weight: number;
    weighted_contribution: number;
  }>;
  recommendations: string[];
}

interface ADRiskCardProps {
  data: ADRiskData;
}

const LEVEL_COLORS: Record<string, string> = {
  low: "#51cf66",
  moderate: "#ffd43b",
  high: "#ff922b",
  very_high: "#ff6b6b",
};

const CLASS_COLORS: Record<string, string> = {
  NC: "#51cf66",
  MCI: "#ffd43b",
  AD: "#ff6b6b",
};

export default function ADRiskCard({ data }: ADRiskCardProps) {
  const levelColor = LEVEL_COLORS[data.risk_level] || "#888";

  // Pie chart data for class probabilities
  const pieData = Object.entries(data.probabilities).map(([name, value]) => ({
    name,
    value: Math.round(value * 100),
    fill: CLASS_COLORS[name] || "#888",
  }));

  // Bar chart data for biomarker contributions
  const barData = data.biomarker_contributions.map((c) => ({
    name: c.biomarker,
    contribution: c.weighted_contribution,
    z: c.z_score,
  }));

  return (
    <div style={{ display: "grid", gap: "16px" }}>
      {/* Risk Score + Classification */}
      <div style={{
        ...sectionStyle,
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "16px",
      }}>
        {/* Risk Score Gauge */}
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "12px", color: "#888", textTransform: "uppercase", marginBottom: "8px" }}>
            AD Risk Score
          </div>
          <div style={{
            fontSize: "48px",
            fontWeight: 800,
            color: levelColor,
            lineHeight: 1,
          }}>
            {data.risk_score.toFixed(0)}
          </div>
          <div style={{
            display: "inline-block",
            marginTop: "8px",
            padding: "4px 12px",
            borderRadius: "12px",
            fontSize: "12px",
            fontWeight: 600,
            background: `${levelColor}22`,
            color: levelColor,
            textTransform: "uppercase",
          }}>
            {data.risk_level.replace("_", " ")}
          </div>
        </div>

        {/* Class Probabilities Pie */}
        <div>
          <div style={{ fontSize: "12px", color: "#888", textTransform: "uppercase", marginBottom: "4px", textAlign: "center" }}>
            Classification
          </div>
          <ResponsiveContainer width="100%" height={120}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={45}
                innerRadius={25}
                paddingAngle={3}
                label={({ name, value }) => `${name} ${value}%`}
              >
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Biomarker Contributions (SHAP-like) */}
      {barData.length > 0 && (
        <div style={sectionStyle}>
          <h3 style={titleStyle}>Biomarker Contributions</h3>
          <p style={{ fontSize: "11px", color: "#666", margin: "0 0 8px 0" }}>
            각 바이오마커가 위험도 점수에 기여하는 정도
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData} layout="vertical" margin={{ left: 120, right: 20 }}>
              <XAxis type="number" tick={{ fill: "#888", fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: "#ccc", fontSize: 11 }} width={120} />
              <Tooltip
                contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 6 }}
                formatter={(value: number, _: string, props: any) => [
                  `${value.toFixed(1)}`,
                  `z-score: ${props.payload.z.toFixed(1)}`,
                ]}
              />
              <Bar dataKey="contribution" radius={[0, 4, 4, 0]}>
                {barData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={entry.contribution > 10 ? "#ff6b6b" : entry.contribution > 5 ? "#ffd43b" : "#51cf66"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <div style={{
          ...sectionStyle,
          borderColor: `${levelColor}33`,
        }}>
          <h3 style={titleStyle}>Recommendations</h3>
          {data.recommendations.map((rec, i) => (
            <div key={i} style={{
              fontSize: "13px",
              color: rec.startsWith("*") ? "#888" : rec.startsWith("  -") ? "#ff8787" : "#ccc",
              marginBottom: "4px",
              fontStyle: rec.startsWith("*") ? "italic" : "normal",
            }}>
              {rec}
            </div>
          ))}
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
  margin: "0 0 8px 0",
  textTransform: "uppercase" as const,
  letterSpacing: "0.5px",
};
