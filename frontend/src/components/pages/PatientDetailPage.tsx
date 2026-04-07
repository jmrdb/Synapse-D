/**
 * Patient detail page — tabbed view of all analysis results.
 */

"use client";

import { useEffect, useState } from "react";
import { getLongitudinal, type LongitudinalData, type AnalysisResult } from "@/lib/api";
import BrainViewer from "@/components/BrainViewer";
import MorphometryCharts from "@/components/MorphometryCharts";
import LongitudinalChart from "@/components/LongitudinalChart";
import ConnectomeView from "@/components/ConnectomeView";
import ADRiskCard, { type ADRiskData } from "@/components/ADRiskCard";

interface PatientDetailPageProps {
  subjectId: string;
}

type Tab = "overview" | "morphometry" | "wmh" | "cmb" | "connectome" | "longitudinal";

export default function PatientDetailPage({ subjectId }: PatientDetailPageProps) {
  const [tab, setTab] = useState<Tab>("overview");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [longitudinal, setLongitudinal] = useState<LongitudinalData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load longitudinal data (which contains the latest analysis)
    getLongitudinal(subjectId)
      .then((data) => {
        setLongitudinal(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [subjectId]);

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>;
  }

  const TABS: Array<{ id: Tab; label: string; icon: string }> = [
    { id: "overview", label: "Overview", icon: "📋" },
    { id: "morphometry", label: "Morphometry", icon: "🧠" },
    { id: "wmh", label: "WMH", icon: "⚪" },
    { id: "cmb", label: "Microbleeds", icon: "🔴" },
    { id: "connectome", label: "Connectome", icon: "🔗" },
    { id: "longitudinal", label: "Longitudinal", icon: "📈" },
  ];

  return (
    <div className="space-y-4">
      {/* Subject Header */}
      <div className="card flex items-center justify-between">
        <div>
          <div className="text-xs text-gray-500 uppercase">Subject</div>
          <div className="text-xl font-mono font-bold text-brand-400">{subjectId}</div>
        </div>
        <div className="flex gap-2">
          {longitudinal && longitudinal.timepoint_count > 0 && (
            <span className="badge badge-green">
              {longitudinal.timepoint_count} timepoint{longitudinal.timepoint_count > 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-surface-border">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`tab ${tab === t.id ? "tab-active" : "tab-inactive"}`}
          >
            <span className="mr-1">{t.icon}</span>
            <span className="hidden sm:inline">{t.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {tab === "overview" && (
          <OverviewTab subjectId={subjectId} longitudinal={longitudinal} />
        )}
        {tab === "morphometry" && result && (
          <MorphometryCharts result={result} />
        )}
        {tab === "wmh" && <WMHTab />}
        {tab === "cmb" && <CMBTab />}
        {tab === "connectome" && <ConnectomeTab />}
        {tab === "longitudinal" && (
          <LongitudinalChart subjectId={subjectId} />
        )}

        {/* Placeholder for tabs without data */}
        {(tab === "morphometry" && !result) && (
          <EmptyState message="형태계측 데이터를 로드하려면 분석을 먼저 실행하세요" />
        )}
        {tab === "wmh" && <EmptyState message="FLAIR 분석 결과가 종단 데이터에 포함됩니다" />}
        {tab === "cmb" && <EmptyState message="SWI 분석 결과가 종단 데이터에 포함됩니다" />}
        {tab === "connectome" && <EmptyState message="연결체 시각화 — dMRI 분석 후 표시" />}
      </div>
    </div>
  );
}

function OverviewTab({
  subjectId,
  longitudinal,
}: {
  subjectId: string;
  longitudinal: LongitudinalData | null;
}) {
  const summary = longitudinal?.summary;

  return (
    <div className="space-y-4">
      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <QuickStat
          label="Timepoints"
          value={String(longitudinal?.timepoint_count || 0)}
          color="text-brand-400"
        />
        <QuickStat
          label="Baseline"
          value={summary?.baseline_date || "—"}
          color="text-gray-300"
        />
        <QuickStat
          label="Latest"
          value={summary?.latest_date || "—"}
          color="text-gray-300"
        />
        <QuickStat
          label="Interval"
          value={summary?.interval_years ? `${summary.interval_years.toFixed(1)} yr` : "—"}
          color="text-purple-400"
        />
      </div>

      {/* Overall Assessment */}
      {summary?.overall_assessment && (
        <div className={`card border-l-4 ${
          summary.overall_assessment.includes("accelerated") ? "border-red-500" :
          summary.overall_assessment.includes("concerning") ? "border-yellow-500" :
          "border-green-500"
        }`}>
          <div className="text-xs text-gray-500 uppercase mb-1">Overall Assessment</div>
          <div className="text-sm text-white">{summary.overall_assessment}</div>
        </div>
      )}

      {/* Change Summary */}
      {summary?.changes && summary.changes.length > 0 && (
        <div className="card">
          <div className="text-xs text-gray-500 uppercase mb-3">Changes</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {summary.changes.map((c: any) => (
              <div key={c.metric} className="bg-surface rounded-lg p-3">
                <div className="text-xs text-gray-500 capitalize">{c.metric.replace(/_/g, " ")}</div>
                <div className={`text-lg font-bold ${
                  Math.abs(c.annualized_change) < 0.5 ? "text-green-400" :
                  Math.abs(c.annualized_change) < 1.5 ? "text-yellow-400" : "text-red-400"
                }`}>
                  {c.annualized_change > 0 ? "+" : ""}{c.annualized_change.toFixed(2)}%/yr
                </div>
                <div className="text-[10px] text-gray-600">{c.interpretation}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!summary && (
        <EmptyState message="분석 데이터가 없습니다. New Analysis에서 MRI를 업로드하세요." />
      )}
    </div>
  );
}

function QuickStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="card">
      <div className="card-label">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
    </div>
  );
}

function WMHTab() { return null; }
function CMBTab() { return null; }
function ConnectomeTab() { return null; }

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-16">
      <div className="text-4xl mb-3 opacity-20">📭</div>
      <div className="text-sm text-gray-500">{message}</div>
    </div>
  );
}
