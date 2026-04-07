/**
 * Patient detail page — tabbed view of all analysis results.
 */

"use client";

import { useEffect, useState } from "react";
import { getLongitudinal, getSubjectResults, type LongitudinalData, type SubjectResults } from "@/lib/api";
import LongitudinalChart from "@/components/LongitudinalChart";

interface PatientDetailPageProps {
  subjectId: string;
}

type Tab = "overview" | "morphometry" | "vascular" | "risk" | "connectome" | "longitudinal";

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
    return <div className="text-center py-12 text-gray-500 animate-pulse">Loading analysis results...</div>;
  }

  if (!results) {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4 opacity-20">📭</div>
        <div className="text-gray-400">이 Subject에 대한 분석 결과가 없습니다.</div>
        <div className="text-gray-600 text-sm mt-1">New Analysis에서 MRI를 업로드하고 분석을 실행하세요.</div>
      </div>
    );
  }

  const TABS: Array<{ id: Tab; label: string; icon: string }> = [
    { id: "overview", label: "Overview", icon: "📋" },
    { id: "morphometry", label: "Structure", icon: "🧠" },
    { id: "vascular", label: "Vascular", icon: "🩸" },
    { id: "risk", label: "AD Risk", icon: "⚠️" },
    { id: "connectome", label: "Connectome", icon: "🔗" },
    { id: "longitudinal", label: "Tracking", icon: "📈" },
  ];

  return (
    <div className="space-y-4">
      {/* Subject Header */}
      <div className="card flex items-center justify-between">
        <div>
          <div className="text-xs text-gray-500 uppercase">Subject</div>
          <div className="text-xl font-mono font-bold text-brand-400">{subjectId}</div>
          <div className="text-xs text-gray-500 mt-1">
            {results.scan_date} · Age: {results.age_at_scan || "—"} · Tier: {results.tier}
          </div>
        </div>
        <div className="flex gap-2">
          {results.brain_age && <span className="badge badge-blue">Brain Age</span>}
          {results.wmh && <span className="badge badge-blue">WMH</span>}
          {results.microbleeds && <span className="badge badge-blue">CMB</span>}
          {results.connectome && <span className="badge badge-blue">Connectome</span>}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-surface-border overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`tab whitespace-nowrap ${tab === t.id ? "tab-active" : "tab-inactive"}`}
          >
            <span className="mr-1">{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {tab === "overview" && <OverviewTab results={results} longitudinal={longitudinal} />}
        {tab === "morphometry" && <MorphometryTab results={results} />}
        {tab === "vascular" && <VascularTab results={results} />}
        {tab === "risk" && <RiskTab results={results} />}
        {tab === "connectome" && <ConnectomeTab results={results} />}
        {tab === "longitudinal" && <LongitudinalChart subjectId={subjectId} />}
      </div>
    </div>
  );
}

/* ============================================================ */
/* Tab Components                                               */
/* ============================================================ */

function OverviewTab({ results, longitudinal }: { results: SubjectResults; longitudinal: LongitudinalData | null }) {
  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Brain Volume"
          value={results.brain_volume_cm3 ? `${results.brain_volume_cm3.toFixed(0)}` : "—"}
          unit="cm³"
          color="text-brand-400"
        />
        <MetricCard
          label="Brain Age"
          value={results.brain_age?.predicted_age?.toFixed(1) || "—"}
          unit="years"
          color="text-purple-400"
        />
        <MetricCard
          label="Brain Age Gap"
          value={results.brain_age?.brain_age_gap != null
            ? `${results.brain_age.brain_age_gap > 0 ? "+" : ""}${results.brain_age.brain_age_gap.toFixed(1)}`
            : "—"}
          unit="years"
          color={
            results.brain_age?.brain_age_gap != null
              ? (results.brain_age.brain_age_gap > 3 ? "text-red-400"
                : results.brain_age.brain_age_gap < -3 ? "text-green-400" : "text-yellow-400")
              : "text-gray-400"
          }
        />
        <MetricCard
          label="Timepoints"
          value={String(longitudinal?.timepoint_count || 1)}
          unit=""
          color="text-blue-400"
        />
      </div>

      {/* WMH + CMB Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results.wmh?.success && (
          <div className="card">
            <div className="card-label">White Matter Hyperintensities</div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold ${
                results.wmh.fazekas_grade <= 1 ? "text-green-400"
                  : results.wmh.fazekas_grade === 2 ? "text-yellow-400" : "text-red-400"
              }`}>{results.wmh.wmh_volume_ml?.toFixed(1)} mL</span>
              <span className="text-sm text-gray-500">Fazekas {results.wmh.fazekas_grade}</span>
            </div>
            <div className="text-xs text-gray-500 mt-1">{results.wmh.wmh_count} lesions</div>
          </div>
        )}
        {results.microbleeds?.success && (
          <div className="card">
            <div className="card-label">Cerebral Microbleeds</div>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold ${
                results.microbleeds.cmb_count === 0 ? "text-green-400"
                  : results.microbleeds.cmb_count <= 2 ? "text-yellow-400"
                  : results.microbleeds.cmb_count <= 10 ? "text-orange-400" : "text-red-400"
              }`}>{results.microbleeds.cmb_count} CMBs</span>
              <span className="text-sm text-gray-500">{results.microbleeds.mars_category?.replace("_", " ")}</span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              L:{results.microbleeds.regional_counts?.lobar || 0}{" "}
              D:{results.microbleeds.regional_counts?.deep || 0}{" "}
              I:{results.microbleeds.regional_counts?.infratentorial || 0}
            </div>
          </div>
        )}
      </div>

      {/* Normative z-scores */}
      {results.normative?.scores && results.normative.scores.length > 0 && (
        <div className="card">
          <div className="card-label">Normative Comparison (z-scores)</div>
          <div className="space-y-2 mt-2">
            {results.normative.scores.map((s: any, i: number) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs text-gray-400 w-36 capitalize">{s.metric.replace(/_/g, " ")}</span>
                <div className="flex-1 h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      Math.abs(s.z_score) < 1 ? "bg-green-500"
                        : Math.abs(s.z_score) < 2 ? "bg-yellow-500" : "bg-red-500"
                    }`}
                    style={{ width: `${Math.min(Math.abs(s.z_score) / 4 * 100, 100)}%` }}
                  />
                </div>
                <span className={`text-xs font-mono w-12 text-right ${
                  Math.abs(s.z_score) < 1 ? "text-green-400"
                    : Math.abs(s.z_score) < 2 ? "text-yellow-400" : "text-red-400"
                }`}>
                  {s.z_score > 0 ? "+" : ""}{s.z_score}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MorphometryTab({ results }: { results: SubjectResults }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard label="Brain Volume" value={results.brain_volume_cm3?.toFixed(0) || "—"} unit="cm³" color="text-brand-400" />
        <MetricCard label="Hippocampus" value={results.hippocampus_mm3?.toFixed(0) || "—"} unit="mm³" color="text-purple-400" />
        <MetricCard label="Cortical Thickness" value={results.cortical_thickness_mm?.toFixed(3) || "—"} unit="mm" color="text-green-400" />
      </div>
      {!results.brain_volume_cm3 && (
        <div className="text-center py-8 text-gray-500 text-sm">
          구조 분석 데이터가 없습니다. T1w MRI 분석이 필요합니다.
        </div>
      )}
    </div>
  );
}

function VascularTab({ results }: { results: SubjectResults }) {
  const wmh = results.wmh;
  const cmb = results.microbleeds;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-300 uppercase">뇌소혈관질환 종합 평가</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* WMH */}
        <div className="card">
          <div className="card-label">WMH (FLAIR)</div>
          {wmh?.success ? (
            <>
              <div className={`text-3xl font-bold ${
                wmh.fazekas_grade <= 1 ? "text-green-400" : wmh.fazekas_grade === 2 ? "text-yellow-400" : "text-red-400"
              }`}>{wmh.wmh_volume_ml?.toFixed(1)} mL</div>
              <div className="text-sm text-gray-400 mt-1">Fazekas Grade {wmh.fazekas_grade}</div>
              <div className="text-xs text-gray-500 mt-1">{wmh.fazekas_description}</div>
              <div className="text-xs text-gray-500 mt-2">Lesions: {wmh.wmh_count}</div>
            </>
          ) : (
            <div className="text-sm text-gray-500">FLAIR 데이터 없음 — 업로드 후 분석하세요</div>
          )}
        </div>

        {/* CMB */}
        <div className="card">
          <div className="card-label">Microbleeds (SWI)</div>
          {cmb?.success ? (
            <>
              <div className={`text-3xl font-bold ${
                cmb.cmb_count === 0 ? "text-green-400" : cmb.cmb_count <= 10 ? "text-yellow-400" : "text-red-400"
              }`}>{cmb.cmb_count} CMBs</div>
              <div className="text-sm text-gray-400 mt-1">MARS: {cmb.mars_category?.replace("_", " ")}</div>
              <div className="text-xs text-gray-500 mt-2">
                Lobar: {cmb.regional_counts?.lobar || 0} ·
                Deep: {cmb.regional_counts?.deep || 0} ·
                Infratentorial: {cmb.regional_counts?.infratentorial || 0}
              </div>
              {cmb.clinical_significance && (
                <div className="text-xs text-gray-400 mt-3 p-2 bg-surface rounded-lg">
                  {cmb.clinical_significance}
                </div>
              )}
            </>
          ) : (
            <div className="text-sm text-gray-500">SWI 데이터 없음 — 업로드 후 분석하세요</div>
          )}
        </div>
      </div>
    </div>
  );
}

function RiskTab({ results }: { results: SubjectResults }) {
  const ad = results.ad_risk;

  if (!ad || "error" in ad || ad.risk_level === "insufficient_data") {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-3 opacity-30">⚠️</div>
        <div className="text-gray-400">AD 위험도 평가 데이터가 부족합니다.</div>
        <div className="text-xs text-gray-600 mt-1">T1w 기반 구조 분석이 필요합니다.</div>
      </div>
    );
  }

  const levelColors: Record<string, string> = {
    low: "text-green-400", moderate: "text-yellow-400",
    high: "text-orange-400", very_high: "text-red-400",
  };
  const levelColor = levelColors[ad.risk_level as string] || "text-gray-400";

  return (
    <div className="space-y-4">
      <div className="card text-center">
        <div className="card-label">AD/MCI Risk Score</div>
        <div className={`text-6xl font-black ${levelColor}`}>{ad.risk_score?.toFixed(0)}</div>
        <div className={`text-sm font-semibold mt-2 uppercase ${levelColor}`}>
          {ad.risk_level?.replace("_", " ")}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          NC: {(ad.probabilities?.NC * 100)?.toFixed(0)}% ·
          MCI: {(ad.probabilities?.MCI * 100)?.toFixed(0)}% ·
          AD: {(ad.probabilities?.AD * 100)?.toFixed(0)}%
        </div>
      </div>

      {/* Biomarker Contributions */}
      {ad.biomarker_contributions && ad.biomarker_contributions.length > 0 && (
        <div className="card">
          <div className="card-label">Biomarker Contributions</div>
          <div className="space-y-3 mt-2">
            {ad.biomarker_contributions.map((c: any, i: number) => (
              <div key={i}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-400">{c.biomarker}</span>
                  <span className="text-gray-500">z={c.z_score}</span>
                </div>
                <div className="h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      c.weighted_contribution > 10 ? "bg-red-500"
                        : c.weighted_contribution > 5 ? "bg-yellow-500" : "bg-green-500"
                    }`}
                    style={{ width: `${Math.min(c.weighted_contribution / 20 * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {ad.recommendations && ad.recommendations.length > 0 && (
        <div className="card">
          <div className="card-label">Recommendations</div>
          <div className="space-y-1 mt-2">
            {ad.recommendations.map((r: string, i: number) => (
              <div key={i} className={`text-sm ${
                r.startsWith("*") ? "text-gray-600 italic text-xs mt-2" : "text-gray-300"
              }`}>{r}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConnectomeTab({ results }: { results: SubjectResults }) {
  const conn = results.connectome;
  if (!conn?.success) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-3 opacity-30">🔗</div>
        <div className="text-gray-400">연결체 데이터가 없습니다.</div>
      </div>
    );
  }

  const m = conn.network_metrics;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Method" value={conn.method} unit="" color="text-brand-400" />
        <MetricCard label="Edges" value={String(m?.n_edges || 0)} unit="" color="text-purple-400" />
        <MetricCard label="Density" value={m?.density?.toFixed(3) || "—"} unit="" color="text-green-400" />
        <MetricCard label="Clustering" value={m?.mean_clustering_coefficient?.toFixed(3) || "—"} unit="" color="text-yellow-400" />
      </div>
      {m?.hub_nodes && (
        <div className="card">
          <div className="card-label">Hub Regions</div>
          <div className="space-y-1 mt-2">
            {m.hub_nodes.map((h: any, i: number) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-gray-300 font-mono">{h.region}</span>
                <span className="text-brand-400">degree: {h.degree}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ============================================================ */
/* Shared Components                                            */
/* ============================================================ */

function MetricCard({ label, value, unit, color }: {
  label: string; value: string; unit: string; color: string;
}) {
  return (
    <div className="card">
      <div className="card-label">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>
        {value} <span className="text-sm font-normal text-gray-500">{unit}</span>
      </div>
    </div>
  );
}
