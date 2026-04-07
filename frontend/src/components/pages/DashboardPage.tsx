/**
 * Dashboard — overview page with summary stats and recent analyses.
 */

"use client";

import { useEffect, useState } from "react";

interface DashboardPageProps {
  onSelectPatient: (subjectId: string) => void;
}

interface SubjectInfo {
  subject_id: string;
  has_t1: boolean;
}

export default function DashboardPage({ onSelectPatient }: DashboardPageProps) {
  const [subjects, setSubjects] = useState<SubjectInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/v1/subjects")
      .then((r) => r.json())
      .then((data) => {
        setSubjects(data.subjects || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const stats = [
    { label: "Total Subjects", value: subjects.length, icon: "👤", color: "text-brand-400" },
    { label: "With T1 Data", value: subjects.filter((s) => s.has_t1).length, icon: "🧠", color: "text-green-400" },
    { label: "Modalities", value: "6", icon: "📁", color: "text-purple-400" },
    { label: "System Status", value: "Online", icon: "⚡", color: "text-green-400" },
  ];

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div className="card bg-gradient-to-r from-brand-900/50 to-surface-card">
        <h2 className="text-xl font-bold text-white mb-1">Synapse-D Brain Digital Twin</h2>
        <p className="text-sm text-gray-400">
          구조적 MRI 기반 뇌 발달 및 퇴행 예측 플랫폼 — Research Use Only
        </p>
        <div className="flex gap-2 mt-4">
          <span className="badge badge-blue">T1w</span>
          <span className="badge badge-blue">FLAIR</span>
          <span className="badge badge-blue">SWI</span>
          <span className="badge badge-blue">dMRI</span>
          <span className="badge badge-blue">Brain Age</span>
          <span className="badge badge-blue">AD Risk</span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="card">
            <div className="flex items-center justify-between">
              <div>
                <div className="card-label">{s.label}</div>
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
              </div>
              <div className="text-3xl opacity-50">{s.icon}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent Subjects */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
            Recent Subjects
          </h3>
          <span className="text-xs text-gray-500">{subjects.length} total</span>
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : subjects.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-4xl mb-2 opacity-30">🧠</div>
            <div className="text-gray-500 text-sm">아직 분석된 데이터가 없습니다</div>
            <div className="text-gray-600 text-xs mt-1">New Analysis에서 MRI를 업로드하세요</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs uppercase border-b border-surface-border">
                  <th className="text-left py-2 px-3">Subject ID</th>
                  <th className="text-left py-2 px-3">T1 Data</th>
                  <th className="text-left py-2 px-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {subjects.slice(0, 10).map((s) => (
                  <tr
                    key={s.subject_id}
                    className="border-b border-surface-border/50 hover:bg-surface-hover
                               transition-colors cursor-pointer"
                    onClick={() => onSelectPatient(s.subject_id)}
                  >
                    <td className="py-3 px-3 font-mono text-brand-400">{s.subject_id}</td>
                    <td className="py-3 px-3">
                      {s.has_t1 ? (
                        <span className="badge badge-green">Available</span>
                      ) : (
                        <span className="badge badge-yellow">Missing</span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      <button className="text-xs text-brand-400 hover:text-brand-300">
                        View Detail →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Platform Capabilities */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          {
            title: "Structural Analysis",
            desc: "T1w MRI → Brain Age, Cortical Thickness, Volumetry, ICV Normalization",
            badges: ["Brain Age", "Morphometry", "Normative"],
          },
          {
            title: "Vascular Assessment",
            desc: "FLAIR → WMH + SWI → Microbleeds = 종합 뇌소혈관질환 평가",
            badges: ["WMH", "Fazekas", "CMB", "MARS"],
          },
          {
            title: "Connectivity & Risk",
            desc: "dMRI Tractography → Connectome + Multi-biomarker AD Risk Score",
            badges: ["Connectome", "AD Risk", "Longitudinal"],
          },
        ].map((cap) => (
          <div key={cap.title} className="card">
            <h4 className="text-sm font-semibold text-white mb-1">{cap.title}</h4>
            <p className="text-xs text-gray-500 mb-3">{cap.desc}</p>
            <div className="flex flex-wrap gap-1">
              {cap.badges.map((b) => (
                <span key={b} className="badge badge-blue">{b}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
