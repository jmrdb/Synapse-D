/**
 * 3D Brain mesh viewer using React Three Fiber.
 * Displays a brain surface mesh with interactive rotation/zoom.
 * Placeholder for Phase 1 - will integrate real brain mesh from FastSurfer in Phase 2.
 */

"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Sphere } from "@react-three/drei";

interface BrainViewerProps {
  brainAge?: number;
  confidence?: number;
}

function BrainMesh() {
  return (
    <group>
      {/* Placeholder: ellipsoid approximation of brain shape */}
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
      {/* Midline fissure hint */}
      <mesh position={[0, 0.1, 0]} rotation={[0, 0, Math.PI / 2]}>
        <planeGeometry args={[3.2, 0.02]} />
        <meshBasicMaterial color="#c49498" />
      </mesh>
    </group>
  );
}

export default function BrainViewer({ brainAge, confidence }: BrainViewerProps) {
  return (
    <div style={{ width: "100%", height: "400px", background: "#1a1a2e", borderRadius: "12px", position: "relative" }}>
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} />
        <directionalLight position={[-3, -3, 2]} intensity={0.3} />
        <BrainMesh />
        <OrbitControls enablePan={false} minDistance={3} maxDistance={8} />
      </Canvas>

      {/* Brain Age overlay */}
      {brainAge !== undefined && (
        <div
          style={{
            position: "absolute",
            bottom: "16px",
            left: "16px",
            background: "rgba(0,0,0,0.7)",
            color: "white",
            padding: "12px 16px",
            borderRadius: "8px",
            fontFamily: "monospace",
          }}
        >
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
    </div>
  );
}
