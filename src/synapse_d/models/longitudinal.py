"""Longitudinal session management and trend analysis.

Stores and compares multiple analysis timepoints for the same subject,
enabling tracking of brain structural changes over time. This is the
core "Digital Twin" differentiator — not just a snapshot, but a
temporal trajectory of brain health.

Key metrics tracked per timepoint:
- Total brain volume (ICV-normalized)
- Hippocampal volume (ICV-normalized)
- Mean cortical thickness
- Brain Age / Brain Age Gap
- WMH burden (Phase 2)

Change rate calculation:
- Annualized percent change for volumes
- Comparison against expected aging trajectory
- Acceleration/deceleration detection

Storage: JSON files per subject (DB-free for Phase 1).
Path: data/processed/{subject_id}/longitudinal.json
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

import numpy as np
from loguru import logger

from synapse_d.config import settings


@dataclass
class Timepoint:
    """Single analysis timepoint for a subject.

    Attributes:
        session_id: Unique session identifier (e.g., 'ses-20260401').
        scan_date: Date of MRI acquisition.
        age_at_scan: Subject's age at the time of scan.
        brain_volume_cm3: Total brain volume (ICV-normalized if available).
        hippocampus_mm3: Total hippocampal volume (ICV-normalized if available).
        cortical_thickness_mm: Mean cortical thickness.
        brain_age: Predicted brain age.
        brain_age_gap: Predicted age - chronological age.
        tier: Analysis quality tier (full/standard/basic).
        metadata: Additional info (scanner, resolution, etc.).
    """

    session_id: str = ""
    scan_date: str = ""  # ISO format: YYYY-MM-DD
    age_at_scan: float = 0.0
    brain_volume_cm3: float | None = None
    hippocampus_mm3: float | None = None
    cortical_thickness_mm: float | None = None
    brain_age: float | None = None
    brain_age_gap: float | None = None
    tier: str = "full"
    metadata: dict = field(default_factory=dict)


@dataclass
class LongitudinalChange:
    """Change between two timepoints for a single metric.

    Attributes:
        metric: Metric name.
        baseline_value: Value at first timepoint.
        latest_value: Value at latest timepoint.
        absolute_change: latest - baseline.
        percent_change: (latest - baseline) / baseline * 100.
        annualized_change: percent_change normalized to per-year rate.
        interval_years: Time between measurements in years.
        interpretation: Human-readable interpretation.
    """

    metric: str = ""
    baseline_value: float = 0.0
    latest_value: float = 0.0
    absolute_change: float = 0.0
    percent_change: float = 0.0
    annualized_change: float = 0.0
    interval_years: float = 0.0
    interpretation: str = ""


@dataclass
class LongitudinalResult:
    """Full longitudinal analysis for a subject.

    Attributes:
        subject_id: BIDS subject ID.
        timepoints: All analysis timepoints, sorted chronologically.
        changes: Computed changes between baseline and latest.
        summary: Dashboard-ready summary.
    """

    subject_id: str = ""
    timepoints: list[Timepoint] = field(default_factory=list)
    changes: list[LongitudinalChange] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# Expected annual change rates for healthy aging (reference ranges)
# Source: Fjell et al., Cerebral Cortex 2009; Jack et al., Neurology 2004
_EXPECTED_ANNUAL_CHANGE = {
    "brain_volume": {
        "normal": (-0.4, -0.1),  # -0.1% to -0.4% per year (healthy aging)
        "concerning": -0.5,       # > 0.5% loss per year
        "alarming": -1.0,         # > 1.0% loss per year (AD-range)
    },
    "hippocampus": {
        "normal": (-1.5, -0.5),   # -0.5% to -1.5% per year
        "concerning": -2.0,        # > 2.0% loss per year
        "alarming": -3.5,          # > 3.5% loss per year (AD-range)
    },
    "cortical_thickness": {
        "normal": (-0.5, -0.1),   # -0.1% to -0.5% per year
        "concerning": -0.7,
        "alarming": -1.2,
    },
}


def save_timepoint(
    subject_id: str,
    analysis_result: dict,
    scan_date: str | None = None,
    age_at_scan: float | None = None,
) -> Timepoint:
    """Save an analysis result as a longitudinal timepoint.

    Extracts key metrics from the pipeline result and appends to the
    subject's longitudinal record.

    Args:
        subject_id: BIDS subject ID.
        analysis_result: Full pipeline result dict from run_pipeline().
        scan_date: ISO date string (defaults to today).
        age_at_scan: Age at scan (uses chronological_age from brain_age if available).

    Returns:
        The saved Timepoint.
    """
    preproc = analysis_result.get("preprocessing", {})
    morpho = preproc.get("morphometrics", {})
    brain_age_data = analysis_result.get("brain_age", {})
    resolution = preproc.get("resolution", {})

    # Determine age
    if age_at_scan is None and "brain_age_gap" in brain_age_data:
        predicted = brain_age_data.get("predicted_age", 0)
        gap = brain_age_data.get("brain_age_gap")
        if gap is not None and predicted:
            age_at_scan = predicted - gap

    # Build timepoint
    session_id = f"ses-{(scan_date or date.today().isoformat()).replace('-', '')}"
    tp = Timepoint(
        session_id=session_id,
        scan_date=scan_date or date.today().isoformat(),
        age_at_scan=age_at_scan or 0.0,
        brain_volume_cm3=morpho.get("total_brain_volume_normalized_cm3")
            or morpho.get("total_brain_volume_cm3"),
        hippocampus_mm3=morpho.get("hippocampus_total_normalized_mm3")
            or morpho.get("hippocampus_total_mm3"),
        cortical_thickness_mm=morpho.get("mean_cortical_thickness_mm"),
        brain_age=brain_age_data.get("predicted_age") if "predicted_age" in brain_age_data else None,
        brain_age_gap=brain_age_data.get("brain_age_gap") if "brain_age_gap" in brain_age_data else None,
        tier=resolution.get("tier", "unknown"),
        metadata={
            "scanner": preproc.get("scanner_info", {}),
            "resolution": resolution,
        },
    )

    # Load existing record, append, save
    record = _load_record(subject_id)
    # Avoid duplicate session_id
    record = [t for t in record if t.session_id != session_id]
    record.append(tp)
    record.sort(key=lambda t: t.scan_date)
    _save_record(subject_id, record)

    logger.info(f"[{subject_id}] Saved timepoint {session_id} "
                f"({len(record)} total timepoints)")
    return tp


def get_longitudinal(subject_id: str) -> LongitudinalResult:
    """Get full longitudinal analysis for a subject.

    Args:
        subject_id: BIDS subject ID.

    Returns:
        LongitudinalResult with timepoints, changes, and summary.
    """
    timepoints = _load_record(subject_id)

    if len(timepoints) < 2:
        return LongitudinalResult(
            subject_id=subject_id,
            timepoints=timepoints,
            summary={
                "timepoint_count": len(timepoints),
                "message": "종단적 비교를 위해 최소 2개 시점의 데이터가 필요합니다."
                           if len(timepoints) < 2 else "",
            },
        )

    baseline = timepoints[0]
    latest = timepoints[-1]
    interval = _date_diff_years(baseline.scan_date, latest.scan_date)

    changes = _compute_changes(baseline, latest, interval)

    summary = _build_longitudinal_summary(timepoints, changes, interval)

    return LongitudinalResult(
        subject_id=subject_id,
        timepoints=timepoints,
        changes=changes,
        summary=summary,
    )


def _compute_changes(
    baseline: Timepoint, latest: Timepoint, interval_years: float
) -> list[LongitudinalChange]:
    """Compute changes between baseline and latest timepoints."""
    changes = []
    metrics = [
        ("brain_volume", baseline.brain_volume_cm3, latest.brain_volume_cm3, "cm³"),
        ("hippocampus", baseline.hippocampus_mm3, latest.hippocampus_mm3, "mm³"),
        ("cortical_thickness", baseline.cortical_thickness_mm, latest.cortical_thickness_mm, "mm"),
        ("brain_age_gap", baseline.brain_age_gap, latest.brain_age_gap, "years"),
    ]

    for name, val_b, val_l, _ in metrics:
        if val_b is None or val_l is None or val_b == 0:
            continue

        abs_change = val_l - val_b

        if name == "brain_age_gap":
            # Brain Age Gap: absolute change, not percentage
            pct = 0.0
            annual = abs_change / interval_years if interval_years > 0 else 0.0
            interp = _interpret_gap_change(abs_change)
        else:
            pct = (abs_change / abs(val_b)) * 100
            annual = pct / interval_years if interval_years > 0 else 0.0
            interp = _interpret_change(name, annual)

        changes.append(LongitudinalChange(
            metric=name,
            baseline_value=round(val_b, 2),
            latest_value=round(val_l, 2),
            absolute_change=round(abs_change, 2),
            percent_change=round(pct, 2),
            annualized_change=round(annual, 2),
            interval_years=round(interval_years, 2),
            interpretation=interp,
        ))

    return changes


def _interpret_change(metric: str, annual_pct: float) -> str:
    """Interpret annualized change rate against expected aging norms."""
    ref = _EXPECTED_ANNUAL_CHANGE.get(metric)
    if not ref:
        return "no reference data"

    if annual_pct >= 0:
        return "stable or increasing"

    alarming = ref["alarming"]
    concerning = ref["concerning"]
    normal_low, normal_high = ref["normal"]

    if annual_pct <= alarming:
        return "accelerated decline (above AD-range threshold)"
    if annual_pct <= concerning:
        return "concerning decline (above normal aging rate)"
    if normal_low <= annual_pct <= normal_high:
        return "normal aging range"
    return "within expected range"


def _interpret_gap_change(abs_change: float) -> str:
    """Interpret Brain Age Gap change over time."""
    if abs_change > 2:
        return "brain aging accelerating"
    if abs_change < -2:
        return "brain aging decelerating (improvement)"
    return "stable brain aging trajectory"


def _build_longitudinal_summary(
    timepoints: list[Timepoint],
    changes: list[LongitudinalChange],
    interval_years: float,
) -> dict:
    """Build dashboard-ready summary of longitudinal analysis."""
    summary: dict = {
        "timepoint_count": len(timepoints),
        "baseline_date": timepoints[0].scan_date,
        "latest_date": timepoints[-1].scan_date,
        "interval_years": round(interval_years, 1),
        "changes": [asdict(c) for c in changes],
    }

    # Build time series for chart rendering
    series: dict[str, list[dict]] = {}
    for tp in timepoints:
        entry = {"date": tp.scan_date, "age": tp.age_at_scan}
        if tp.brain_volume_cm3 is not None:
            series.setdefault("brain_volume", []).append(
                {**entry, "value": round(tp.brain_volume_cm3, 1)}
            )
        if tp.hippocampus_mm3 is not None:
            series.setdefault("hippocampus", []).append(
                {**entry, "value": round(tp.hippocampus_mm3, 0)}
            )
        if tp.cortical_thickness_mm is not None:
            series.setdefault("cortical_thickness", []).append(
                {**entry, "value": round(tp.cortical_thickness_mm, 3)}
            )
        if tp.brain_age_gap is not None:
            series.setdefault("brain_age_gap", []).append(
                {**entry, "value": round(tp.brain_age_gap, 1)}
            )

    summary["series"] = series

    # Overall assessment
    vol_change = next((c for c in changes if c.metric == "brain_volume"), None)
    if vol_change:
        summary["overall_assessment"] = vol_change.interpretation
    else:
        summary["overall_assessment"] = "insufficient data for assessment"

    return summary


def _load_record(subject_id: str) -> list[Timepoint]:
    """Load longitudinal record for a subject from JSON file."""
    path = _record_path(subject_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return [Timepoint(**tp) for tp in data]
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"[{subject_id}] Failed to load longitudinal record: {e}")
        return []


def _save_record(subject_id: str, timepoints: list[Timepoint]) -> None:
    """Save longitudinal record to JSON file."""
    path = _record_path(subject_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [asdict(tp) for tp in timepoints]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _record_path(subject_id: str) -> Path:
    """Get path to a subject's longitudinal record file."""
    return settings.output_dir / subject_id / "longitudinal.json"


def _date_diff_years(date1: str, date2: str) -> float:
    """Calculate difference between two ISO date strings in years."""
    try:
        d1 = datetime.fromisoformat(date1)
        d2 = datetime.fromisoformat(date2)
        return abs((d2 - d1).days) / 365.25
    except (ValueError, TypeError):
        return 0.0
