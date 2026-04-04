/**
 * Brain viewer component with two modes:
 * 1. NiivueViewer: Renders actual NIfTI files using Niivue (after analysis)
 * 2. PlaceholderViewer: Three.js brain mesh (before analysis)
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

type ViewMode = "3d" | "axial" | "sagittal" | "coronal";

interface BrainViewerProps {
  niftiUrl?: string;
  brainAge?: number;
  confidence?: number;
}

/** Actual NIfTI renderer using Niivue (WebGL2 volume rendering) */
function NiivueViewer({ niftiUrl, viewMode }: { niftiUrl: string; viewMode: ViewMode }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nvRef = useRef<any>(null);

  // Initialize Niivue on mount or niftiUrl change
  useEffect(() => {
    let mounted = true;

    async function initNiivue() {
      const { Niivue } = await import("@niivue/niivue");

      if (!mounted || !canvasRef.current) return;

      // Dispose previous instance to prevent WebGL context leak
      if (nvRef.current) {
        nvRef.current.dispose?.();
        nvRef.current = null;
      }

      const nv = new Niivue({
        backColor: [0.1, 0.1, 0.15, 1],
        show3Dcrosshair: false,
        isOrientCube: true,
      });
      nv.attachToCanvas(canvasRef.current);
      await nv.loadVolumes([{ url: niftiUrl, colormap: "gray" }]);
      nv.setSliceType(nv.sliceTypeRender);

      nvRef.current = nv;
    }

    initNiivue();

    return () => {
      mounted = false;
      if (nvRef.current) {
        nvRef.current.dispose?.();
        nvRef.current = null;
      }
    };
  }, [niftiUrl]);

  // Update slice type when viewMode changes
  useEffect(() => {
    const nv = nvRef.current;
    if (!nv) return;

    const modeMap: Record<ViewMode, number> = {
      "3d": nv.sliceTypeRender,
      axial: nv.sliceTypeAxial,
      sagittal: nv.sliceTypeSagittal,
      coronal: nv.sliceTypeCoronal,
    };
    nv.setSliceType(modeMap[viewMode] ?? nv.sliceTypeRender);
  }, [viewMode]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: "100%", height: "100%", borderRadius: "12px" }}
    />
  );
}

/** Placeholder 3D brain for when no NIfTI is loaded yet */
function PlaceholderBrain() {
  return (
    <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={0.8} />
      <directionalLight position={[-3, -3, 2]} intensity={0.3} />
      <mesh scale={[1.2, 1.0, 1.3]}>
        <sphereGeometry args={[1.5, 64, 64]} />
        <meshStandardMaterial
          color="#e8b4b8"
          roughness={0.6}
          metalness={0.1}
          transparent
          opacity={0.85}
        />
      </mesh>
      <OrbitControls enablePan={false} minDistance={3} maxDistance={8} />
    </Canvas>
  );
}

export default function BrainViewer({ niftiUrl, brainAge, confidence }: BrainViewerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("3d");

  return (
    <div style={{
      width: "100%",
      height: "450px",
      background: "#1a1a2e",
      borderRadius: "12px",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* View mode buttons */}
      {niftiUrl && (
        <div style={{
          position: "absolute",
          top: "12px",
          right: "12px",
          zIndex: 10,
          display: "flex",
          gap: "4px",
        }}>
          {(["3d", "axial", "sagittal", "coronal"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              style={{
                padding: "4px 10px",
                fontSize: "11px",
                border: "1px solid #444",
                borderRadius: "4px",
                background: viewMode === mode ? "#4f9cf7" : "rgba(0,0,0,0.5)",
                color: "white",
                cursor: "pointer",
                textTransform: "uppercase",
              }}
            >
              {mode}
            </button>
          ))}
        </div>
      )}

      {niftiUrl ? (
        <NiivueViewer niftiUrl={niftiUrl} viewMode={viewMode} />
      ) : (
        <PlaceholderBrain />
      )}

      {/* Brain Age overlay */}
      {brainAge !== undefined && (
        <div style={{
          position: "absolute",
          bottom: "16px",
          left: "16px",
          background: "rgba(0,0,0,0.7)",
          color: "white",
          padding: "12px 16px",
          borderRadius: "8px",
          fontFamily: "monospace",
        }}>
          <div style={{ fontSize: "12px", opacity: 0.7 }}>Predicted Brain Age</div>
          <div style={{ fontSize: "28px", fontWeight: "bold" }}>
            {brainAge.toFixed(1)} <span style={{ fontSize: "14px" }}>years</span>
          </div>
          {confidence !== undefined && (
            <div style={{ fontSize: "11px", opacity: 0.5 }}>
              confidence: {(confidence * 100).toFixed(1)}%
            </div>
          )}
        </div>
      )}

      {!niftiUrl && !brainAge && (
        <div style={{
          position: "absolute",
          bottom: "16px",
          left: "50%",
          transform: "translateX(-50%)",
          fontSize: "12px",
          color: "#555",
        }}>
          MRI 업로드 후 실제 뇌 구조가 렌더링됩니다
        </div>
      )}
    </div>
  );
}
