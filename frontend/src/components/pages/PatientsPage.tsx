/**
 * Patients list page — search, sort, and manage patient records.
 */

"use client";

import { useEffect, useState } from "react";

interface PatientsPageProps {
  onSelectPatient: (subjectId: string) => void;
}

interface SubjectInfo {
  subject_id: string;
  has_t1: boolean;
}

export default function PatientsPage({ onSelectPatient }: PatientsPageProps) {
  const [subjects, setSubjects] = useState<SubjectInfo[]>([]);
  const [search, setSearch] = useState("");
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

  const filtered = subjects.filter((s) =>
    s.subject_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      {/* Search + Actions */}
      <div className="flex items-center gap-4">
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Subject ID 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
          <span className="absolute left-3 top-2.5 text-gray-500">🔍</span>
        </div>
        <span className="text-sm text-gray-500">{filtered.length}명</span>
      </div>

      {/* Patient Table */}
      <div className="card">
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-4xl mb-2 opacity-30">👤</div>
            <div className="text-gray-500 text-sm">
              {search ? "검색 결과가 없습니다" : "등록된 환자가 없습니다"}
            </div>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase border-b border-surface-border">
                <th className="text-left py-3 px-4">Subject ID</th>
                <th className="text-left py-3 px-4">T1w</th>
                <th className="text-left py-3 px-4">Status</th>
                <th className="text-right py-3 px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr
                  key={s.subject_id}
                  className="border-b border-surface-border/30 hover:bg-surface-hover
                             transition-colors cursor-pointer"
                  onClick={() => onSelectPatient(s.subject_id)}
                >
                  <td className="py-3 px-4">
                    <span className="font-mono text-brand-400 font-medium">
                      {s.subject_id}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    {s.has_t1 ? (
                      <span className="badge badge-green">✓</span>
                    ) : (
                      <span className="badge badge-yellow">—</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="badge badge-blue">Analyzed</span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button className="btn-secondary text-xs">View →</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
