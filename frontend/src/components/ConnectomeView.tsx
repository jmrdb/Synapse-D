/**
 * Structural connectome visualization.
 * Displays brain connectivity as a heatmap matrix and network metrics summary.
 */

"use client";

import { useMemo } from "react";

interface ConnectomeData {
  n_regions: number;
  connectivity_matrix: number[][];
  network_metrics: {
    n_edges: number;
    density: number;
    mean_degree: number;
    mean_clustering_coefficient: number;
    hub_nodes: Array<{ region: string; degree: number }>;
  };
  method: string;
}

interface ConnectomeViewProps {
  data: ConnectomeData;
}

/** Render connectivity matrix as a canvas-based heatmap */
function MatrixHeatmap({ matrix }: { matrix: number[][] }) {
  const size = matrix.length;
  const canvasSize = 300;

  const canvasRef = useMemo(() => {
    if (typeof document === "undefined") return null;
    const canvas = document.createElement("canvas");
    canvas.width = canvasSize;
    canvas.height = canvasSize;
    const ctx = canvas.getContext("2d");
    if (!ctx) return canvas;

    const cellSize = canvasSize / size;
    for (let i = 0; i < size; i++) {
      for (let j = 0; j < size; j++) {
        const val = matrix[i][j];
        // Blue-to-red colormap
        const r = Math.round(val * 255);
        const b = Math.round((1 - val) * 100);
        ctx.fillStyle = `rgb(${r}, ${Math.round(val * 50)}, ${b})`;
        ctx.fillRect(j * cellSize, i * cellSize, cellSize + 0.5, cellSize + 0.5);
      }
    }
    return canvas;
  }, [matrix, size]);

  if (!canvasRef) return null;

  return (
    <div style={{ display: "flex", justifyContent: "center" }}>
      <img
        src={canvasRef.toDataURL()}
        alt="Connectivity Matrix"
        style={{ width: "280px", height: "280px", borderRadius: "8px" }}
      />
    </div>
  );
}

export default function ConnectomeView({ data }: ConnectomeViewProps) {
  const metrics = data.network_metrics;

  return (
    <div style={sectionStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h3 style={titleStyle}>Structural Connectome</h3>
        <span style={{
          fontSize: "10px",
          padding: "2px 8px",
          borderRadius: "4px",
          background: data.method === "tractography" ? "#51cf6622" : "#ffd43b22",
          color: data.method === "tractography" ? "#51cf66" : "#ffd43b",
        }}>
          {data.method === "tractography" ? "dMRI tractography" : "synthetic (demo)"}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
        {/* Heatmap */}
        <div>
          <div style={{ fontSize: "11px", color: "#888", marginBottom: "8px", textAlign: "center" }}>
            {data.n_regions}x{data.n_regions} Connectivity Matrix
          </div>
          <MatrixHeatmap matrix={data.connectivity_matrix} />
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "10px",
            color: "#666",
            marginTop: "4px",
            padding: "0 10px",
          }}>
            <span>Weak</span>
            <div style={{
              width: "100px",
              height: "8px",
              background: "linear-gradient(to right, rgb(0,0,100), rgb(128,25,50), rgb(255,50,0))",
              borderRadius: "4px",
            }} />
            <span>Strong</span>
          </div>
        </div>

        {/* Network Metrics */}
        <div>
          <div style={{ fontSize: "11px", color: "#888", marginBottom: "12px" }}>
            Network Metrics
          </div>
          <div style={{ display: "grid", gap: "8px" }}>
            <MetricRow label="Edges" value={metrics.n_edges.toString()} />
            <MetricRow label="Density" value={metrics.density.toFixed(3)} />
            <MetricRow label="Mean Degree" value={metrics.mean_degree.toFixed(1)} />
            <MetricRow label="Clustering" value={metrics.mean_clustering_coefficient.toFixed(3)} />
          </div>

          {/* Hub Nodes */}
          <div style={{ fontSize: "11px", color: "#888", marginTop: "16px", marginBottom: "8px" }}>
            Hub Regions
          </div>
          {metrics.hub_nodes.map((hub, i) => (
            <div key={i} style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "11px",
              color: "#ccc",
              padding: "2px 0",
            }}>
              <span>{hub.region}</span>
              <span style={{ color: "#4f9cf7" }}>{hub.degree}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      display: "flex",
      justifyContent: "space-between",
      fontSize: "13px",
    }}>
      <span style={{ color: "#888" }}>{label}</span>
      <span style={{ color: "#ccc", fontWeight: 600 }}>{value}</span>
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
