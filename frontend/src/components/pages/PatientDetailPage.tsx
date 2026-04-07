/**
 * Patient detail page — analysis results with MRI viewer, charts, and metrics.
 */

"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { getLongitudinal, getSubjectResults, type LongitudinalData, type SubjectResults } from "@/lib/api";
import LongitudinalChart from "@/components/LongitudinalChart";
import MorphometryCharts from "@/components/MorphometryCharts";

// Dynamic import for Niivue (WebGL, client-only)
const BrainViewer = dynamic(() => import("@/components/BrainViewer"), { ssr: false });

interface PatientDetailPageProps {
  subjectId: string;
}

type Tab = "overview" | "imaging" | "vascular" | "risk" | "connectome" | "tracking";

export default function PatientDetailPage({ subjectId }: PatientDetailPageProps) {
  const [tab, setTab] = useState<Tab>("overview");
  const [results, setResults] = useState<SubjectResults | null>(null);
  const [longitudinal, setLongitudinal] = useState<LongitudinalData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getSubjectResults(subjectId).catch(() => null),
      getLongitudinal(subjectId).catch(() => null),
    ]).then(([r, l]) => {
      setResults(r);
      setLongitudinal(l);
      setLoading(false);
    });
  }, [subjectId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <div className="text-4xl animate-pulse mb-3">🧠</div>
          <div className="text-gray-400">Loading analysis results...</div>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="text-center py-20">
        <div className="text-5xl mb-4 opacity-20">📭</div>
        <div className="text-lg text-gray-300 mb-2">분석 결과 없음</div>
        <div className="text-sm text-gray-500">New Analysis에서 MRI를 업로드하세요.</div>
      </div>
    );
  }

  const TABS: Array<{ id: Tab; label: string; icon: string }> = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "imaging", label: "Brain Imaging", icon: "🧠" },
    { id: "vascular", label: "Vascular", icon: "🩸" },
    { id: "risk", label: "AD Risk", icon: "⚠️" },
    { id: "connectome", label: "Connectome", icon: "🔗" },
    { id: "tracking", label: "Tracking", icon: "📈" },
  ];

  return (
    <div className="space-y-4">
      {/* Subject Header */}
      <div className="card bg-gradient-to-r from-brand-900/30 to-surface-card">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider">Subject</div>
            <div className="text-2xl font-mono font-bold text-brand-400">{subjectId}</div>
            <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
              <span>📅 {results.scan_date}</span>
              {results.age_at_scan > 0 && <span>👤 {results.age_at_scan}세</span>}
              <span className={`badge ${results.tier === "full" ? "badge-green" : results.tier === "standard" ? "badge-yellow" : "badge-red"}`}>
                {results.tier?.toUpperCase()}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {results.brain_age && <span className="badge badge-blue">Brain Age</span>}
            {results.wmh?.success && <span className="badge badge-blue">WMH</span>}
            {results.microbleeds?.success && <span className="badge badge-blue">CMB</span>}
            {results.connectome?.success && <span className="badge badge-blue">Connectome</span>}
            {results.ad_risk && !("error" in results.ad_risk) && <span className="badge badge-blue">AD Risk</span>}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-surface-border overflow-x-auto pb-px">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`tab whitespace-nowrap ${tab === t.id ? "tab-active" : "tab-inactive"}`}
          >
            <span className="mr-1.5">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[500px]">
        {tab === "overview" && <OverviewTab results={results} longitudinal={longitudinal} />}
        {tab === "imaging" && <ImagingTab results={results} />}
        {tab === "vascular" && <VascularTab results={results} />}
        {tab === "risk" && <RiskTab results={results} />}
        {tab === "connectome" && <ConnectomeTab results={results} />}
        {tab === "tracking" && <LongitudinalChart subjectId={subjectId} />}
      </div>
    </div>
  );
}

/* ============================================================ */
/* Shared Components                                            */
/* ============================================================ */

function MetricCard({ label, value, unit, color, subtitle }: {
  label: string; value: string; unit: string; color: string; subtitle?: string;
}) {
  return (
    <div className="card">
      <div className="card-label">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-bold ${color}`}>{value}</span>
        {unit && <span className="text-sm text-gray-500">{unit}</span>}
      </div>
      {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
    </div>
  );
}

function GaugeBar({ value, max, color, label }: {
  value: number; max: number; color: string; label: string;
}) {
  const pct = Math.min(Math.abs(value) / max * 100, 100);
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-400">{label}</span>
        <span className={color}>{value > 0 ? "+" : ""}{value.toFixed(2)}</span>
      </div>
      <div className="h-2.5 bg-surface rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${color.replace("text-", "bg-")}`}
             style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">{children}</h3>;
}

/* ============================================================ */
/* Overview Tab                                                  */
/* ============================================================ */

function OverviewTab({ results, longitudinal }: { results: SubjectResults; longitudinal: LongitudinalData | null }) {
  return (
    <div className="space-y-6">
      {/* Hero Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <MetricCard
          label="Brain Volume"
          value={results.brain_volume_cm3?.toFixed(0) || "—"}
          unit="cm³"
          color="text-brand-400"
        />
        <MetricCard
          label="Brain Age"
          value={results.brain_age?.predicted_age?.toFixed(1) || "—"}
          unit="yr"
          color="text-purple-400"
        />
        <MetricCard
          label="Brain Age Gap"
          value={results.brain_age?.brain_age_gap != null
            ? `${results.brain_age.brain_age_gap > 0 ? "+" : ""}${results.brain_age.brain_age_gap.toFixed(1)}`
            : "—"}
          unit="yr"
          color={results.brain_age?.brain_age_gap != null
            ? (results.brain_age.brain_age_gap > 3 ? "text-red-400"
              : results.brain_age.brain_age_gap < -3 ? "text-green-400" : "text-yellow-400")
            : "text-gray-400"}
          subtitle={results.brain_age?.brain_age_gap != null
            ? (results.brain_age.brain_age_gap > 3 ? "accelerated aging"
              : results.brain_age.brain_age_gap < -3 ? "resilient brain" : "normal range")
            : undefined}
        />
        <MetricCard
          label="WMH Burden"
          value={results.wmh?.success ? results.wmh.wmh_volume_ml?.toFixed(1) : "—"}
          unit="mL"
          color={results.wmh?.success
            ? (results.wmh.fazekas_grade <= 1 ? "text-green-400"
              : results.wmh.fazekas_grade === 2 ? "text-yellow-400" : "text-red-400")
            : "text-gray-400"}
          subtitle={results.wmh?.success ? `Fazekas ${results.wmh.fazekas_grade}` : "FLAIR 필요"}
        />
        <MetricCard
          label="Microbleeds"
          value={results.microbleeds?.success ? String(results.microbleeds.cmb_count) : "—"}
          unit="CMBs"
          color={results.microbleeds?.success
            ? (results.microbleeds.cmb_count === 0 ? "text-green-400"
              : results.microbleeds.cmb_count <= 10 ? "text-yellow-400" : "text-red-400")
            : "text-gray-400"}
          subtitle={results.microbleeds?.success ? results.microbleeds.mars_category?.replace("_", " ") : "SWI 필요"}
        />
      </div>

      {/* Normative z-scores — visual bars */}
      {results.normative?.scores && results.normative.scores.length > 0 && (
        <div className="card">
          <SectionTitle>Normative Comparison</SectionTitle>
          <p className="text-xs text-gray-600 mb-4">0 = 동일 연령/성별 평균 · ±2 이내 = 정상 범위</p>
          <div className="space-y-3">
            {results.normative.scores.map((s: any, i: number) => (
              <GaugeBar
                key={i}
                value={s.z_score}
                max={4}
                label={s.metric.replace(/_/g, " ")}
                color={Math.abs(s.z_score) < 1 ? "text-green-400"
                  : Math.abs(s.z_score) < 2 ? "text-yellow-400" : "text-red-400"}
              />
            ))}
          </div>
        </div>
      )}

      {/* AD Risk Summary (if available) */}
      {results.ad_risk && results.ad_risk.risk_level && results.ad_risk.risk_level !== "insufficient_data" && (
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <SectionTitle>AD/MCI Risk Assessment</SectionTitle>
              <div className="flex items-baseline gap-3 mt-2">
                <span className={`text-4xl font-black ${
                  { low: "text-green-400", moderate: "text-yellow-400", high: "text-orange-400", very_high: "text-red-400" }
                    [results.ad_risk.risk_level as string] || "text-gray-400"
                }`}>{results.ad_risk.risk_score?.toFixed(0)}</span>
                <span className="text-sm text-gray-400 uppercase">{results.ad_risk.risk_level?.replace("_", " ")}</span>
              </div>
            </div>
            <div className="text-right text-xs text-gray-500">
              <div>NC {((results.ad_risk.probabilities?.NC || 0) * 100).toFixed(0)}%</div>
              <div>MCI {((results.ad_risk.probabilities?.MCI || 0) * 100).toFixed(0)}%</div>
              <div>AD {((results.ad_risk.probabilities?.AD || 0) * 100).toFixed(0)}%</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================================ */
/* Imaging Tab — MRI Viewer + Structure Metrics                  */
/* ============================================================ */

function ImagingTab({ results }: { results: SubjectResults }) {
  // Build NIfTI URL from metadata
  const brainUrl = results.metadata?.scanner ? `/files/${results.subject_id}/anat/${results.subject_id}_T1w_brain.nii.gz` : undefined;

  return (
    <div className="space-y-4">
      {/* 3D Brain Viewer */}
      <div className="card p-0 overflow-hidden">
        <BrainViewer
          niftiUrl={brainUrl}
          brainAge={results.brain_age?.predicted_age}
          confidence={undefined}
        />
      </div>

      {/* Structure Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard label="Brain Volume" value={results.brain_volume_cm3?.toFixed(0) || "—"} unit="cm³" color="text-brand-400" />
        <MetricCard label="Hippocampus" value={results.hippocampus_mm3?.toFixed(0) || "—"} unit="mm³" color="text-purple-400" />
        <MetricCard label="Cortical Thickness" value={results.cortical_thickness_mm?.toFixed(3) || "—"} unit="mm" color="text-green-400" />
      </div>

      {!results.brain_volume_cm3 && (
        <div className="text-center py-8 text-gray-500 text-sm">
          T1w MRI 분석 후 구조 데이터가 표시됩니다.
        </div>
      )}
    </div>
  );
}

/* ============================================================ */
/* Vascular Tab — WMH + CMB side by side                        */
/* ============================================================ */

function VascularTab({ results }: { results: SubjectResults }) {
  const wmh = results.wmh;
  const cmb = results.microbleeds;

  return (
    <div className="space-y-4">
      <SectionTitle>뇌소혈관질환 종합 평가 (CSVD)</SectionTitle>
      <p className="text-xs text-gray-600">FLAIR(백질 병변) + SWI(미세출혈) 통합 분석</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* WMH Card */}
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">⚪</span>
            <span className="text-sm font-semibold text-white">White Matter Hyperintensities</span>
          </div>
          {wmh?.success ? (
            <>
              <div className={`text-4xl font-black ${
                wmh.fazekas_grade <= 1 ? "text-green-400" : wmh.fazekas_grade === 2 ? "text-yellow-400" : "text-red-400"
              }`}>{wmh.wmh_volume_ml?.toFixed(1)} <span className="text-base font-normal text-gray-500">mL</span></div>
              <div className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-400">Fazekas Grade</span><span className="text-white">{wmh.fazekas_grade}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Lesion Count</span><span className="text-white">{wmh.wmh_count}</span></div>
              </div>
              {wmh.fazekas_description && (
                <div className="mt-3 p-2 bg-surface rounded text-xs text-gray-400">{wmh.fazekas_description}</div>
              )}
            </>
          ) : (
            <div className="py-6 text-center text-gray-500 text-sm">FLAIR 데이터를 업로드하세요</div>
          )}
        </div>

        {/* CMB Card */}
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">🔴</span>
            <span className="text-sm font-semibold text-white">Cerebral Microbleeds</span>
          </div>
          {cmb?.success ? (
            <>
              <div className={`text-4xl font-black ${
                cmb.cmb_count === 0 ? "text-green-400" : cmb.cmb_count <= 10 ? "text-yellow-400" : "text-red-400"
              }`}>{cmb.cmb_count} <span className="text-base font-normal text-gray-500">CMBs</span></div>
              <div className="mt-3 space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-400">MARS Classification</span><span className="text-white">{cmb.mars_category?.replace("_", " ")}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Lobar</span><span className="text-white">{cmb.regional_counts?.lobar || 0}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Deep</span><span className="text-white">{cmb.regional_counts?.deep || 0}</span></div>
                <div className="flex justify-between"><span className="text-gray-400">Infratentorial</span><span className="text-white">{cmb.regional_counts?.infratentorial || 0}</span></div>
              </div>
              {cmb.clinical_significance && (
                <div className="mt-3 p-2 bg-surface rounded text-xs text-gray-400">{cmb.clinical_significance}</div>
              )}
            </>
          ) : (
            <div className="py-6 text-center text-gray-500 text-sm">SWI 데이터를 업로드하세요</div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============================================================ */
/* Risk Tab — AD/MCI Assessment                                  */
/* ============================================================ */

function RiskTab({ results }: { results: SubjectResults }) {
  const ad = results.ad_risk;

  if (!ad || ad.risk_level === "insufficient_data" || "error" in ad) {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4 opacity-20">⚠️</div>
        <div className="text-lg text-gray-300">데이터 부족</div>
        <div className="text-sm text-gray-500 mt-2">AD 위험도 평가에 필요한 바이오마커가 충분하지 않습니다.</div>
        <div className="text-xs text-gray-600 mt-1">T1w 기반 구조 분석이 필요합니다.</div>
      </div>
    );
  }

  const levelColors: Record<string, string> = {
    low: "text-green-400", moderate: "text-yellow-400",
    high: "text-orange-400", very_high: "text-red-400",
  };
  const levelBgColors: Record<string, string> = {
    low: "bg-green-500/10", moderate: "bg-yellow-500/10",
    high: "bg-orange-500/10", very_high: "bg-red-500/10",
  };
  const color = levelColors[ad.risk_level as string] || "text-gray-400";
  const bgColor = levelBgColors[ad.risk_level as string] || "bg-surface";

  return (
    <div className="space-y-4">
      {/* Risk Score Hero */}
      <div className={`card text-center py-8 ${bgColor} border-none`}>
        <div className="card-label">AD/MCI Risk Score</div>
        <div className={`text-7xl font-black ${color}`}>{ad.risk_score?.toFixed(0)}</div>
        <div className={`text-lg font-bold mt-2 uppercase ${color}`}>{ad.risk_level?.replace("_", " ")}</div>
        <div className="flex justify-center gap-6 mt-4 text-sm">
          <span className="text-green-400">NC {((ad.probabilities?.NC || 0) * 100).toFixed(0)}%</span>
          <span className="text-yellow-400">MCI {((ad.probabilities?.MCI || 0) * 100).toFixed(0)}%</span>
          <span className="text-red-400">AD {((ad.probabilities?.AD || 0) * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Biomarker Contributions */}
      {ad.biomarker_contributions && ad.biomarker_contributions.length > 0 && (
        <div className="card">
          <SectionTitle>Biomarker Contributions</SectionTitle>
          <p className="text-xs text-gray-600 mb-4">각 바이오마커가 위험도 점수에 기여하는 정도</p>
          <div className="space-y-3">
            {ad.biomarker_contributions.map((c: any, i: number) => (
              <GaugeBar
                key={i}
                value={c.weighted_contribution}
                max={20}
                label={`${c.biomarker} (z=${c.z_score})`}
                color={c.weighted_contribution > 10 ? "text-red-400"
                  : c.weighted_contribution > 5 ? "text-yellow-400" : "text-green-400"}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {ad.recommendations && ad.recommendations.length > 0 && (
        <div className="card">
          <SectionTitle>Clinical Recommendations</SectionTitle>
          <div className="space-y-2 mt-3">
            {ad.recommendations.map((r: string, i: number) => (
              <div key={i} className={`text-sm ${
                r.startsWith("*") ? "text-gray-600 italic text-xs mt-3 pt-3 border-t border-surface-border" : "text-gray-300"
              }`}>{r}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================================ */
/* Connectome Tab                                                */
/* ============================================================ */

function ConnectomeTab({ results }: { results: SubjectResults }) {
  const conn = results.connectome;
  if (!conn?.success) {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4 opacity-20">🔗</div>
        <div className="text-lg text-gray-300">연결체 데이터 없음</div>
        <div className="text-sm text-gray-500 mt-2">dMRI 분석 후 표시됩니다.</div>
      </div>
    );
  }

  const m = conn.network_metrics;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard label="Method" value={conn.method} unit="" color="text-brand-400" />
        <MetricCard label="Edges" value={String(m?.n_edges || 0)} unit="" color="text-purple-400" />
        <MetricCard label="Density" value={m?.density?.toFixed(4) || "—"} unit="" color="text-green-400" />
        <MetricCard label="Clustering" value={m?.mean_clustering_coefficient?.toFixed(4) || "—"} unit="" color="text-yellow-400" />
      </div>

      {m?.hub_nodes && (
        <div className="card">
          <SectionTitle>Hub Regions (Top 5 by Degree)</SectionTitle>
          <div className="mt-3 space-y-2">
            {m.hub_nodes.map((h: any, i: number) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-4">{i + 1}</span>
                <span className="flex-1 text-sm font-mono text-gray-300">{h.region}</span>
                <div className="w-32 h-2 bg-surface rounded-full overflow-hidden">
                  <div className="h-full bg-brand-400 rounded-full"
                       style={{ width: `${(h.degree / (m.hub_nodes[0]?.degree || 1)) * 100}%` }} />
                </div>
                <span className="text-sm text-brand-400 w-8 text-right">{h.degree}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
