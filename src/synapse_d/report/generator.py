"""IR-grade analysis report generator.

Generates a self-contained HTML report from analysis results that:
- Includes all analysis data (Brain Age, morphometry, WMH, CMB, AD Risk, connectome)
- Renders inline charts using Chart.js CDN
- Has professional styling with Synapse-D branding
- Is printable / exportable to PDF via browser print
- Works as a standalone file (no server needed)

Usage:
    from synapse_d.report.generator import generate_report
    html = generate_report(result_dict, subject_id="sub-01")
    Path("report.html").write_text(html)
"""

import html as html_mod
import json
from datetime import datetime
from pathlib import Path

from loguru import logger


def _esc(value: object) -> str:
    """Escape a value for safe HTML insertion — prevents XSS."""
    return html_mod.escape(str(value)) if value is not None else "—"


def generate_report(
    result: dict,
    subject_id: str = "",
    title: str = "Brain Digital Twin Analysis Report",
) -> str:
    """Generate a complete HTML analysis report.

    Args:
        result: Full pipeline result dict (from run_pipeline or latest_result.json).
        subject_id: BIDS subject ID.
        title: Report title.

    Returns:
        Complete HTML string — self-contained, ready to open in browser.
    """
    preproc = result.get("preprocessing", {})
    morpho = preproc.get("morphometrics", {})
    scanner = preproc.get("scanner_info", {})
    resolution = preproc.get("resolution", {})
    brain_age = result.get("brain_age", {})
    wmh = result.get("wmh", {})
    cmb = result.get("microbleeds", {})
    normative = result.get("normative", {})
    ad_risk = result.get("ad_risk", {})
    connectome = result.get("connectome", {})

    sid = _esc(result.get("subject_id", subject_id))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sections = []

    # Section 1: Patient & Scanner Info
    sections.append(_section_header(sid, now, scanner, resolution))

    # Section 2: Brain Age & Volume
    sections.append(_section_brain_age(brain_age, morpho))

    # Section 3: Normative Comparison
    if normative.get("scores"):
        sections.append(_section_normative(normative))

    # Section 4: WMH (FLAIR)
    if wmh.get("success"):
        sections.append(_section_wmh(wmh))

    # Section 5: Microbleeds (SWI)
    if cmb.get("success"):
        sections.append(_section_cmb(cmb))

    # Section 6: AD Risk
    if ad_risk.get("risk_score") is not None and ad_risk.get("risk_level") != "insufficient_data":
        sections.append(_section_ad_risk(ad_risk))

    # Section 7: Connectome
    if connectome.get("success"):
        sections.append(_section_connectome(connectome))

    # Section 8: Brain Simulation (TVB)
    simulation = result.get("simulation", {})
    if simulation.get("success"):
        sections.append(_section_simulation(simulation, connectome))

    # Disclaimer
    sections.append(_section_disclaimer())

    body = "\n".join(sections)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {sid}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
{_get_css()}
</style>
</head>
<body>
<div class="report">
{body}
</div>
<script>
{_get_chart_scripts(normative, ad_risk, wmh, cmb)}
</script>
</body>
</html>"""

    logger.info(f"Report generated for {sid} ({len(html)} bytes)")
    return html


def _section_header(sid: str, now: str, scanner: dict, resolution: dict) -> str:
    tier = resolution.get("tier", "unknown")
    tier_color = {"full": "#22c55e", "standard": "#eab308", "basic": "#ef4444"}.get(tier, "#888")
    voxel = resolution.get("voxel_size_mm", [])
    voxel_str = f"{voxel[0]:.1f}×{voxel[1]:.1f}×{voxel[2]:.1f}mm" if len(voxel) >= 3 else "—"

    return f"""
    <div class="header">
        <div class="logo">
            <div class="logo-icon">S</div>
            <div>
                <div class="logo-text">Synapse-D</div>
                <div class="logo-sub">Brain Digital Twin Platform</div>
            </div>
        </div>
        <div class="header-right">
            <div class="report-date">{now}</div>
            <div class="ruo-badge">Research Use Only</div>
        </div>
    </div>

    <div class="patient-bar">
        <div class="patient-info">
            <span class="label">Subject</span>
            <span class="value mono">{sid}</span>
        </div>
        <div class="patient-info">
            <span class="label">Scanner</span>
            <span class="value">{_esc(scanner.get('manufacturer','?'))} {_esc(scanner.get('model','?'))} {scanner.get('field_strength_t',0)}T</span>
        </div>
        <div class="patient-info">
            <span class="label">Resolution</span>
            <span class="value">{voxel_str}</span>
        </div>
        <div class="patient-info">
            <span class="label">Tier</span>
            <span class="tier-badge" style="background:{tier_color}20;color:{tier_color}">{tier.upper()}</span>
        </div>
    </div>
    """


def _section_brain_age(ba: dict, morpho: dict) -> str:
    if not ba.get("predicted_age"):
        return ""

    age = ba["predicted_age"]
    gap = ba.get("brain_age_gap")
    gap_str = f"{'+' if gap and gap > 0 else ''}{gap:.1f}" if gap is not None else "—"
    gap_color = "#ef4444" if gap and gap > 3 else "#22c55e" if gap and gap < -3 else "#eab308"
    gap_label = "accelerated" if gap and gap > 3 else "resilient" if gap and gap < -3 else "normal"

    vol = morpho.get("total_brain_volume_cm3", "—")
    hippo = morpho.get("hippocampus_total_mm3") or morpho.get("hippocampus_total_normalized_mm3") or "—"
    thickness = morpho.get("mean_cortical_thickness_mm", "—")

    return f"""
    <div class="section">
        <h2>🧠 Brain Structure & Age</h2>
        <div class="metrics-row">
            <div class="metric-card">
                <div class="metric-label">Predicted Brain Age</div>
                <div class="metric-value blue">{age:.1f}<span class="unit">years</span></div>
            </div>
            <div class="metric-card highlight" style="border-color:{gap_color}40">
                <div class="metric-label">Brain Age Gap</div>
                <div class="metric-value" style="color:{gap_color}">{gap_str}<span class="unit">years</span></div>
                <div class="metric-sub">{gap_label} aging</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Brain Volume</div>
                <div class="metric-value blue">{vol if isinstance(vol, str) else f'{vol:.0f}'}<span class="unit">cm³</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Hippocampus</div>
                <div class="metric-value purple">{hippo if isinstance(hippo, str) else f'{hippo:.0f}'}<span class="unit">mm³</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Cortical Thickness</div>
                <div class="metric-value green">{thickness if isinstance(thickness, str) else f'{thickness:.3f}'}<span class="unit">mm</span></div>
            </div>
        </div>
    </div>
    """


def _section_normative(norm: dict) -> str:
    scores = norm.get("scores", [])
    if not scores:
        return ""

    bars_html = ""
    for s in scores:
        z = s["z_score"]
        color = "#22c55e" if abs(z) < 1 else "#eab308" if abs(z) < 2 else "#ef4444"
        width = min(abs(z) / 4 * 100, 100)
        bars_html += f"""
        <div class="z-row">
            <span class="z-label">{_esc(s['metric'].replace('_', ' '))}</span>
            <div class="z-bar-bg">
                <div class="z-bar" style="width:{width}%;background:{color}"></div>
            </div>
            <span class="z-value" style="color:{color}">{'+' if z > 0 else ''}{z:.2f}</span>
            <span class="z-interp">{_esc(s['interpretation'])}</span>
        </div>"""

    icv = "✓" if norm.get("icv_normalized") else "—"
    field = "✓" if norm.get("field_strength_corrected") else "—"

    return f"""
    <div class="section">
        <h2>📊 Normative Comparison</h2>
        <p class="section-desc">동일 연령/성별 대비 z-score (0 = 평균, ±2 이내 = 정상)</p>
        <div class="z-chart">
            {bars_html}
        </div>
        <div class="corrections">
            <span>ICV Normalized: {icv}</span>
            <span>Field Strength Corrected: {field}</span>
        </div>
    </div>
    """


def _section_wmh(wmh: dict) -> str:
    vol = wmh.get("wmh_volume_ml", 0)
    faz = wmh.get("fazekas_grade", 0)
    cnt = wmh.get("wmh_count", 0)
    desc = wmh.get("fazekas_description", "")
    color = "#22c55e" if faz <= 1 else "#eab308" if faz == 2 else "#ef4444"

    regional = wmh.get("regional_distribution", {})
    reg_html = ""
    for k, v in regional.items():
        if k.startswith("_"):
            continue
        reg_html += f"<div class='reg-item'><span>{k}</span><span>{v:.1f} mL</span></div>"

    return f"""
    <div class="section">
        <h2>⚪ White Matter Hyperintensities (FLAIR)</h2>
        <div class="metrics-row">
            <div class="metric-card highlight" style="border-color:{color}40">
                <div class="metric-label">WMH Volume</div>
                <div class="metric-value" style="color:{color}">{vol:.1f}<span class="unit">mL</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Fazekas Grade</div>
                <div class="metric-value" style="color:{color}">{faz}<span class="unit">/ 3</span></div>
                <div class="metric-sub">{desc}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Lesion Count</div>
                <div class="metric-value blue">{cnt}</div>
            </div>
        </div>
        {f'<div class="regional-box"><h4>Regional Distribution</h4>{reg_html}</div>' if reg_html else ''}
    </div>
    """


def _section_cmb(cmb: dict) -> str:
    cnt = cmb.get("cmb_count", 0)
    mars = cmb.get("mars_category", "none")
    rc = cmb.get("regional_counts", {})
    sig = cmb.get("clinical_significance", "")
    color = "#22c55e" if cnt == 0 else "#eab308" if cnt <= 10 else "#ef4444"

    return f"""
    <div class="section">
        <h2>🔴 Cerebral Microbleeds (SWI)</h2>
        <div class="metrics-row">
            <div class="metric-card highlight" style="border-color:{color}40">
                <div class="metric-label">CMB Count</div>
                <div class="metric-value" style="color:{color}">{cnt}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">MARS Classification</div>
                <div class="metric-value blue">{_esc(mars.replace('_', ' '))}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Regional Distribution</div>
                <div class="metric-sub" style="font-size:14px;margin-top:8px">
                    Lobar: <b>{rc.get('lobar',0)}</b> ·
                    Deep: <b>{rc.get('deep',0)}</b> ·
                    Infra: <b>{rc.get('infratentorial',0)}</b>
                </div>
            </div>
        </div>
        {f'<div class="clinical-note">{_esc(sig)}</div>' if sig else ''}
        <canvas id="cmbChart" height="150"></canvas>
    </div>
    """


def _section_ad_risk(ad: dict) -> str:
    score = ad.get("risk_score", 0)
    level = ad.get("risk_level", "unknown")
    probs = ad.get("probabilities", {})
    contribs = ad.get("biomarker_contributions", [])
    recs = ad.get("recommendations", [])

    colors = {"low": "#22c55e", "moderate": "#eab308", "high": "#f97316", "very_high": "#ef4444"}
    color = colors.get(level, "#888")

    contrib_html = ""
    for c in contribs:
        w = min(c.get("weighted_contribution", 0) / 20 * 100, 100)
        cc = "#ef4444" if c.get("weighted_contribution", 0) > 10 else "#eab308" if c.get("weighted_contribution", 0) > 5 else "#22c55e"
        contrib_html += f"""
        <div class="z-row">
            <span class="z-label">{_esc(c['biomarker'])} (z={c['z_score']:.1f})</span>
            <div class="z-bar-bg"><div class="z-bar" style="width:{w}%;background:{cc}"></div></div>
            <span class="z-value" style="color:{cc}">{c['weighted_contribution']:.1f}</span>
        </div>"""

    recs_html = "".join(f"<li>{_esc(r)}</li>" for r in recs if r)

    return f"""
    <div class="section">
        <h2>⚠️ AD/MCI Risk Assessment</h2>
        <div class="risk-hero" style="background:{color}10;border-color:{color}30">
            <div class="risk-score" style="color:{color}">{score:.0f}</div>
            <div class="risk-level" style="color:{color}">{level.replace('_', ' ').upper()}</div>
            <div class="risk-probs">
                NC {probs.get('NC',0)*100:.0f}% · MCI {probs.get('MCI',0)*100:.0f}% · AD {probs.get('AD',0)*100:.0f}%
            </div>
        </div>
        <h4 style="margin-top:20px">Biomarker Contributions</h4>
        <div class="z-chart">{contrib_html}</div>
        {f'<div class="recs"><h4>Clinical Recommendations</h4><ul>{recs_html}</ul></div>' if recs_html else ''}
    </div>
    """


def _section_connectome(conn: dict) -> str:
    m = conn.get("network_metrics", {})
    hubs = m.get("hub_nodes", [])

    hub_html = ""
    for h in hubs[:5]:
        hub_html += f"<div class='reg-item'><span class='mono'>{_esc(h['region'])}</span><span>degree: {h['degree']}</span></div>"

    return f"""
    <div class="section">
        <h2>🔗 Structural Connectome</h2>
        <div class="metrics-row">
            <div class="metric-card"><div class="metric-label">Method</div><div class="metric-value blue" style="font-size:18px">{conn.get('method','—')}</div></div>
            <div class="metric-card"><div class="metric-label">Regions</div><div class="metric-value purple">{conn.get('n_regions',0)}</div></div>
            <div class="metric-card"><div class="metric-label">Edges</div><div class="metric-value green">{m.get('n_edges',0)}</div></div>
            <div class="metric-card"><div class="metric-label">Density</div><div class="metric-value blue">{m.get('density',0):.4f}</div></div>
            <div class="metric-card"><div class="metric-label">Clustering</div><div class="metric-value purple">{m.get('mean_clustering_coefficient',0):.4f}</div></div>
        </div>
        <div class="regional-box"><h4>Hub Regions</h4>{hub_html}</div>
    </div>
    """


def _section_simulation(sim: dict, connectome: dict) -> str:
    sc_fc = sim.get("sc_fc_correlation", 0)
    fc_corr = sim.get("fc_mean_correlation", 0)
    elapsed = sim.get("elapsed_seconds", 0)
    model = _esc(sim.get("model", "unknown"))
    n = sim.get("n_regions", 0)
    eeg_pts = sim.get("eeg_timepoints", 0)

    sc_fc_color = "#22c55e" if sc_fc > 0.3 else "#eab308" if sc_fc > 0.1 else "#ef4444"
    sc_fc_pct = abs(sc_fc) * 100

    # Encode SC and FC matrices as JSON for canvas rendering
    sc_matrix = connectome.get("connectivity_matrix", [])
    fc_matrix = sim.get("fc_matrix", [])

    # Limit matrix size for inline JSON (avoid huge HTML)
    max_render = 82
    if len(sc_matrix) > max_render:
        sc_matrix = [row[:max_render] for row in sc_matrix[:max_render]]
    if len(fc_matrix) > max_render:
        fc_matrix = [row[:max_render] for row in fc_matrix[:max_render]]

    sc_json = json.dumps(sc_matrix)
    fc_json = json.dumps(fc_matrix)

    return f"""
    <div class="section">
        <h2>🧬 Brain Simulation (Digital Twin)</h2>
        <p class="section-desc">
            구조적 연결체(SC)를 기반으로 TVB 신경질량모델 시뮬레이션을 실행하여
            기능적 연결체(FC)를 예측합니다.
        </p>

        <div class="metrics-row">
            <div class="metric-card highlight" style="border-color:{sc_fc_color}40">
                <div class="metric-label">SC-FC Correlation</div>
                <div class="metric-value" style="color:{sc_fc_color}">
                    {sc_fc:.3f}
                </div>
                <div class="metric-sub">구조가 기능의 {sc_fc_pct:.0f}%를 설명</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">FC Mean Correlation</div>
                <div class="metric-value blue">{fc_corr:.3f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Model</div>
                <div class="metric-value purple" style="font-size:16px">{model}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Simulation</div>
                <div class="metric-value green" style="font-size:16px">
                    {n} regions · {eeg_pts} pts · {elapsed}s
                </div>
            </div>
        </div>

        <!-- SC vs FC Heatmap Comparison -->
        <div class="sim-comparison">
            <div class="sim-panel">
                <div class="sim-panel-title">Structural Connectivity (SC)</div>
                <div class="sim-panel-sub">MRI에서 추출한 뇌 배선</div>
                <canvas id="scHeatmap" width="280" height="280"></canvas>
            </div>
            <div class="sim-arrow">
                <div class="sim-arrow-icon">→</div>
                <div class="sim-arrow-label">TVB<br>Simulation</div>
            </div>
            <div class="sim-panel">
                <div class="sim-panel-title">Functional Connectivity (FC)</div>
                <div class="sim-panel-sub">시뮬레이션된 뇌 활동 패턴</div>
                <canvas id="fcHeatmap" width="280" height="280"></canvas>
            </div>
        </div>

        <div class="sim-legend">
            <div class="sim-legend-bar"></div>
            <div class="sim-legend-labels">
                <span>0 (없음)</span>
                <span>연결 강도</span>
                <span>1 (최대)</span>
            </div>
        </div>
    </div>

    <script>
    (function() {{
        function drawHeatmap(canvasId, matrix) {{
            var canvas = document.getElementById(canvasId);
            if (!canvas || !matrix || matrix.length === 0) return;
            var ctx = canvas.getContext('2d');
            var n = matrix.length;
            var size = canvas.width;
            var cell = size / n;

            for (var i = 0; i < n; i++) {{
                for (var j = 0; j < n; j++) {{
                    var v = Math.abs(matrix[i][j]);
                    v = Math.min(v, 1.0);
                    // Blue-to-red colormap
                    var r = Math.round(v * 255);
                    var g = Math.round(v * 60);
                    var b = Math.round((1 - v) * 120);
                    ctx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
                    ctx.fillRect(j * cell, i * cell, cell + 0.5, cell + 0.5);
                }}
            }}
        }}

        var sc = {sc_json};
        var fc = {fc_json};
        drawHeatmap('scHeatmap', sc);
        drawHeatmap('fcHeatmap', fc);
    }})();
    </script>
    """


def _section_disclaimer() -> str:
    return """
    <div class="disclaimer">
        <p><strong>Disclaimer</strong></p>
        <p>본 리포트는 구조적 MRI 바이오마커 기반의 연구용(Research Use Only) 분석 결과이며,
        의료기기 인허가를 받은 진단 도구가 아닙니다. 임상적 판단은 반드시 전문 의료진과 상담하세요.</p>
        <p>Synapse-D Brain Digital Twin Platform v0.1.0</p>
    </div>
    """


def _get_css() -> str:
    return """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0a0a14; color: #e5e5e5; }
    .report { max-width: 900px; margin: 0 auto; padding: 30px 40px; }

    .header { display: flex; justify-content: space-between; align-items: center;
              padding: 20px 0; border-bottom: 1px solid #1e1e30; }
    .logo { display: flex; align-items: center; gap: 12px; }
    .logo-icon { width: 40px; height: 40px; border-radius: 10px; background: #3b82f6;
                 display: flex; align-items: center; justify-content: center;
                 color: white; font-weight: 800; font-size: 18px; }
    .logo-text { font-size: 20px; font-weight: 700; color: white; }
    .logo-sub { font-size: 11px; color: #666; }
    .header-right { text-align: right; }
    .report-date { font-size: 12px; color: #888; }
    .ruo-badge { display: inline-block; margin-top: 4px; padding: 2px 10px;
                 border-radius: 4px; font-size: 10px; font-weight: 600;
                 background: #ef444420; color: #ef4444; }

    .patient-bar { display: flex; gap: 30px; padding: 16px 0;
                   border-bottom: 1px solid #1e1e30; margin-bottom: 20px; }
    .patient-info .label { font-size: 10px; color: #666; text-transform: uppercase;
                           display: block; }
    .patient-info .value { font-size: 14px; color: #ccc; }
    .mono { font-family: 'SF Mono', 'Fira Code', monospace; }
    .tier-badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
                  font-size: 11px; font-weight: 600; }

    .section { margin: 28px 0; }
    .section h2 { font-size: 16px; font-weight: 600; color: #ddd; margin-bottom: 4px; }
    .section-desc { font-size: 12px; color: #666; margin-bottom: 16px; }

    .metrics-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; }
    .metric-card { flex: 1; min-width: 140px; background: #12121e; border: 1px solid #1e1e30;
                   border-radius: 10px; padding: 14px 16px; }
    .metric-card.highlight { border-width: 2px; }
    .metric-label { font-size: 10px; color: #888; text-transform: uppercase;
                    letter-spacing: 0.5px; margin-bottom: 6px; }
    .metric-value { font-size: 28px; font-weight: 800; line-height: 1; }
    .metric-value .unit { font-size: 13px; font-weight: 400; color: #666; margin-left: 3px; }
    .metric-sub { font-size: 11px; color: #888; margin-top: 4px; }
    .blue { color: #3b82f6; }
    .purple { color: #a78bfa; }
    .green { color: #22c55e; }

    .z-chart { margin: 16px 0; }
    .z-row { display: flex; align-items: center; gap: 10px; margin: 8px 0; }
    .z-label { font-size: 12px; color: #aaa; width: 140px; text-transform: capitalize; }
    .z-bar-bg { flex: 1; height: 10px; background: #1a1a2e; border-radius: 5px; overflow: hidden; }
    .z-bar { height: 100%; border-radius: 5px; transition: width 0.5s; }
    .z-value { font-size: 12px; font-family: monospace; width: 50px; text-align: right; }
    .z-interp { font-size: 10px; color: #666; width: 120px; }
    .corrections { font-size: 10px; color: #555; display: flex; gap: 20px; margin-top: 8px; }

    .risk-hero { text-align: center; padding: 30px; border-radius: 12px;
                 border: 2px solid; margin-top: 12px; }
    .risk-score { font-size: 72px; font-weight: 900; line-height: 1; }
    .risk-level { font-size: 18px; font-weight: 700; margin-top: 8px; }
    .risk-probs { font-size: 13px; color: #888; margin-top: 8px; }

    .regional-box { background: #12121e; border-radius: 8px; padding: 14px 16px; margin-top: 12px; }
    .regional-box h4 { font-size: 11px; color: #888; text-transform: uppercase; margin-bottom: 8px; }
    .reg-item { display: flex; justify-content: space-between; font-size: 13px;
                padding: 4px 0; border-bottom: 1px solid #1a1a2e; color: #ccc; }

    .clinical-note { background: #12121e; border-radius: 8px; padding: 14px 16px;
                     font-size: 13px; color: #aaa; margin-top: 12px; line-height: 1.6; }

    .recs { margin-top: 16px; }
    .recs h4 { font-size: 12px; color: #888; text-transform: uppercase; margin-bottom: 8px; }
    .recs ul { list-style: none; }
    .recs li { font-size: 13px; color: #bbb; padding: 4px 0; padding-left: 12px;
               border-left: 2px solid #1e1e30; margin: 4px 0; }

    .disclaimer { margin-top: 40px; padding: 20px; background: #0d0d18;
                  border: 1px solid #1e1e30; border-radius: 8px; }
    .disclaimer p { font-size: 11px; color: #666; margin: 4px 0; line-height: 1.5; }

    canvas { margin-top: 16px; background: #12121e; border-radius: 8px; padding: 10px; }

    .sim-comparison { display: flex; align-items: center; justify-content: center;
                      gap: 20px; margin: 24px 0; flex-wrap: wrap; }
    .sim-panel { text-align: center; }
    .sim-panel-title { font-size: 13px; font-weight: 600; color: #ccc; margin-bottom: 2px; }
    .sim-panel-sub { font-size: 10px; color: #666; margin-bottom: 10px; }
    .sim-panel canvas { border-radius: 8px; border: 1px solid #1e1e30; }
    .sim-arrow { text-align: center; padding: 0 10px; }
    .sim-arrow-icon { font-size: 36px; color: #3b82f6; }
    .sim-arrow-label { font-size: 10px; color: #888; margin-top: 4px; }
    .sim-legend { max-width: 300px; margin: 10px auto; text-align: center; }
    .sim-legend-bar { height: 10px; border-radius: 5px;
                      background: linear-gradient(to right, rgb(0,0,120), rgb(128,30,50), rgb(255,60,0)); }
    .sim-legend-labels { display: flex; justify-content: space-between;
                         font-size: 9px; color: #666; margin-top: 3px; }

    @media print {
        body { background: white; color: #333; }
        .report { padding: 20px; }
        .metric-card, .regional-box, .clinical-note { background: #f5f5f5; border-color: #ddd; }
        .z-bar-bg { background: #eee; }
        .risk-hero { border-color: #ccc !important; }
        .disclaimer { background: #f5f5f5; }
    }
    """


def _get_chart_scripts(normative: dict, ad_risk: dict, wmh: dict, cmb: dict) -> str:
    scripts = []

    # CMB regional doughnut chart (useful — shows spatial distribution)
    rc = cmb.get("regional_counts", {})
    if any(v for v in rc.values() if isinstance(v, (int, float)) and v > 0):
        scripts.append(f"""
        if (document.getElementById('cmbChart')) {{
            new Chart(document.getElementById('cmbChart'), {{
                type: 'doughnut',
                data: {{
                    labels: ['Lobar', 'Deep', 'Infratentorial'],
                    datasets: [{{ data: [{rc.get('lobar',0)}, {rc.get('deep',0)}, {rc.get('infratentorial',0)}],
                                  backgroundColor: ['#3b82f6', '#a78bfa', '#f97316'] }}]
                }},
                options: {{
                    plugins: {{ legend: {{ position: 'right', labels: {{ color: '#aaa' }} }} }}
                }}
            }});
        }}""")

    return "\n".join(scripts)
