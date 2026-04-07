"use client";

import { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import DashboardPage from "@/components/pages/DashboardPage";
import PatientsPage from "@/components/pages/PatientsPage";
import AnalyzePage from "@/components/pages/AnalyzePage";
import PatientDetailPage from "@/components/pages/PatientDetailPage";

const PAGE_CONFIG: Record<string, { title: string; subtitle: string }> = {
  dashboard: { title: "Dashboard", subtitle: "전체 분석 현황 및 통계" },
  patients: { title: "Patients", subtitle: "환자 목록 및 관리" },
  analyze: { title: "New Analysis", subtitle: "MRI 업로드 및 분석" },
  detail: { title: "Patient Detail", subtitle: "분석 결과 상세 보기" },
};

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [collapsed, setCollapsed] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null);

  const handleNavigate = (p: string) => {
    setPage(p);
    if (p !== "detail") setSelectedSubject(null);
  };

  const handleSelectPatient = (subjectId: string) => {
    setSelectedSubject(subjectId);
    setPage("detail");
  };

  const config = PAGE_CONFIG[page] || PAGE_CONFIG.dashboard;

  return (
    <div className="min-h-screen bg-surface">
      <Sidebar
        currentPage={page}
        onNavigate={handleNavigate}
        collapsed={collapsed}
        onToggle={() => setCollapsed(!collapsed)}
      />

      <main className={`transition-all duration-300 ${collapsed ? "ml-16" : "ml-60"}`}>
        <Header title={config.title} subtitle={config.subtitle} />

        <div className="p-6">
          {page === "dashboard" && (
            <DashboardPage onSelectPatient={handleSelectPatient} />
          )}
          {page === "patients" && (
            <PatientsPage onSelectPatient={handleSelectPatient} />
          )}
          {page === "analyze" && (
            <AnalyzePage
              onComplete={(subjectId) => {
                setSelectedSubject(subjectId);
                setPage("detail");
              }}
            />
          )}
          {page === "detail" && selectedSubject && (
            <PatientDetailPage subjectId={selectedSubject} />
          )}
        </div>
      </main>
    </div>
  );
}
