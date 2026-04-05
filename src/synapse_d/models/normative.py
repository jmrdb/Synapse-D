"""Normative comparison module.

Compares individual brain morphometric measurements against population norms
to calculate z-scores (standard deviations from expected values for age/sex).

Positive z-score = larger than expected for age (e.g., ventricular enlargement)
Negative z-score = smaller than expected (e.g., hippocampal atrophy)

Corrections applied:
- ICV normalization: removes head-size-driven sex/ethnicity bias (Liu 2025)
- Field strength correction: 1.5T→3T scaling (Reuter 2012, Pardoe 2013)
  3T systematically overestimates vs 1.5T; norms are 3T-based.

Reference values are derived from published large-scale studies:
- Brain volume: Bethlehem et al., Nature 2022 (Lifespan Brain Chart)
- Hippocampal volume: Nobis et al., NeuroImage 2019
- Cortical thickness: Fjell et al., Cerebral Cortex 2015
- Field strength: Reuter et al., NeuroImage 2012; Pardoe et al., HBM 2013

Phase 2 will integrate BrainStat + neuroHarmonize for continuous modeling.
"""

from dataclasses import dataclass, field

import numpy as np
from loguru import logger


@dataclass
class NormativeScore:
    """Z-score comparison for a single metric.

    Attributes:
        metric: Name of the metric.
        value: Individual's measured value.
        expected: Expected value for age/sex.
        std: Population standard deviation.
        z_score: (value - expected) / std.
        interpretation: Human-readable interpretation.
    """

    metric: str
    value: float
    expected: float
    std: float
    z_score: float
    interpretation: str = ""


@dataclass
class NormativeResult:
    """Full normative comparison for a subject.

    Attributes:
        subject_id: BIDS subject ID.
        age: Chronological age used for comparison.
        sex: Sex used for comparison ('M' or 'F').
        scores: List of z-score comparisons.
        summary: Overall brain health assessment.
    """

    subject_id: str = ""
    age: float = 0.0
    sex: str = "unknown"
    scores: list[NormativeScore] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# Normative reference data (mean, std) by age decade
# Source: Bethlehem et al., Nature 2022 (Lifespan Brain Chart)
# Values: (mean_cm3, std_cm3) for total brain volume
_BRAIN_VOLUME_NORMS: dict[str, dict[int, tuple[float, float]]] = {
    "M": {
        20: (1270, 80), 30: (1250, 80), 40: (1230, 85),
        50: (1200, 85), 60: (1160, 90), 70: (1110, 90),
        80: (1060, 95),
    },
    "F": {
        20: (1130, 75), 30: (1115, 75), 40: (1100, 80),
        50: (1075, 80), 60: (1040, 85), 70: (995, 85),
        80: (950, 90),
    },
}

# Sex-pooled norms for ICV-normalized volumes.
# When ICV normalization is applied, sex-based head size difference is already
# removed, so sex-pooled norms should be used to avoid double correction.
# Values: weighted average of M and F norms (approx 50/50 sex ratio)
_BRAIN_VOLUME_NORMS_POOLED: dict[int, tuple[float, float]] = {
    20: (1200, 100), 30: (1183, 100), 40: (1165, 105),
    50: (1138, 105), 60: (1100, 110), 70: (1053, 110),
    80: (1005, 115),
}

_HIPPOCAMPUS_NORMS_POOLED: dict[int, tuple[float, float]] = {
    20: (8000, 820), 30: (7900, 820), 40: (7700, 860),
    50: (7400, 860), 60: (7000, 900), 70: (6500, 900),
    80: (5950, 940),
}

# Hippocampal volume norms (sum of L+R, mm3) — sex-specific (for raw values)
# Source: Nobis et al., NeuroImage 2019
_HIPPOCAMPUS_NORMS: dict[str, dict[int, tuple[float, float]]] = {
    "M": {
        20: (8200, 800), 30: (8100, 800), 40: (7900, 850),
        50: (7600, 850), 60: (7200, 900), 70: (6700, 900),
        80: (6100, 950),
    },
    "F": {
        20: (7800, 750), 30: (7700, 750), 40: (7500, 800),
        50: (7200, 800), 60: (6800, 850), 70: (6300, 850),
        80: (5800, 900),
    },
}

# WMH volume norms (mL) — sex-pooled (WMH is primarily age-driven)
# Source: Habes et al., Brain 2016; de Leeuw et al., Neurology 2001
_WMH_VOLUME_NORMS: dict[int, tuple[float, float]] = {
    20: (0.1, 0.2), 30: (0.3, 0.4), 40: (0.8, 0.8),
    50: (2.5, 2.5), 60: (5.0, 4.0), 70: (10.0, 7.0),
    80: (18.0, 12.0),
}

# Mean cortical thickness norms (mm)
# Source: Fjell et al., Cerebral Cortex 2015
_CORTICAL_THICKNESS_NORMS: dict[int, tuple[float, float]] = {
    20: (2.65, 0.12), 30: (2.60, 0.12), 40: (2.55, 0.13),
    50: (2.48, 0.13), 60: (2.40, 0.14), 70: (2.30, 0.14),
    80: (2.20, 0.15),
}


def _get_norm(
    norms: dict[int, tuple[float, float]], age: float
) -> tuple[float, float]:
    """Interpolate normative values for a given age.

    Args:
        norms: Dict mapping age decade → (mean, std).
        age: Subject's age.

    Returns:
        Tuple of (interpolated_mean, interpolated_std).
    """
    decades = sorted(norms.keys())

    if age <= decades[0]:
        return norms[decades[0]]
    if age >= decades[-1]:
        return norms[decades[-1]]

    # Linear interpolation between nearest decades
    for i in range(len(decades) - 1):
        if decades[i] <= age <= decades[i + 1]:
            t = (age - decades[i]) / (decades[i + 1] - decades[i])
            m0, s0 = norms[decades[i]]
            m1, s1 = norms[decades[i + 1]]
            return (m0 + t * (m1 - m0), s0 + t * (s1 - s0))

    return norms[decades[-1]]


# Field strength correction factors: 1.5T → 3T equivalent scaling.
# Normative tables are 3T-based (most large cohorts use 3T).
# 3T systematically overestimates vs 1.5T due to higher SNR/contrast.
# These factors scale 1.5T measurements UP to 3T-equivalent values.
#
# Source: Reuter et al., NeuroImage 2012 (cortical thickness ~+4.5%)
#         Pardoe et al., Human Brain Mapping 2013 (hippocampus ~+5%)
#         General literature consensus (brain volume ~+2%)
_FIELD_STRENGTH_CORRECTION: dict[str, float] = {
    "cortical_thickness": 1.045,   # 1.5T * 1.045 ≈ 3T equivalent
    "hippocampus_volume": 1.05,    # 1.5T * 1.05 ≈ 3T equivalent
    "brain_volume": 1.02,          # 1.5T * 1.02 ≈ 3T equivalent
    # "ventricle_volume": 0.98  # Reserved for Phase 2 ventricle normative comparison
}


def _apply_field_correction(
    value: float, metric: str, field_strength_t: float
) -> tuple[float, bool]:
    """Apply field strength correction to normalize 1.5T values to 3T equivalent.

    Normative reference tables are derived from 3T data (UK Biobank, HCP, etc.).
    When input is from a 1.5T scanner, measurements are systematically lower
    for most metrics. This correction scales 1.5T values up to 3T-equivalent.

    No correction is applied for 3T data or unknown field strength.

    Args:
        value: Raw measurement value.
        metric: Metric name matching _FIELD_STRENGTH_CORRECTION keys.
        field_strength_t: Scanner field strength in Tesla.

    Returns:
        Tuple of (corrected_value, was_corrected).
    """
    if field_strength_t <= 0:
        return value, False  # Unknown field strength
    if field_strength_t >= 2.5:
        if field_strength_t > 4.0:
            logger.warning(f"7T+ scanner ({field_strength_t}T) — field correction "
                          f"not supported, normative results may be biased")
        return value, False  # 3T or higher — norms are 3T-based

    factor = _FIELD_STRENGTH_CORRECTION.get(metric, 1.0)
    corrected = value * factor
    return corrected, True


def _interpret_z(z: float, metric_name: str) -> str:
    """Generate human-readable interpretation of a z-score."""
    abs_z = abs(z)
    if abs_z < 1.0:
        return "normal range"
    elif abs_z < 2.0:
        direction = "above" if z > 0 else "below"
        return f"mildly {direction} average"
    else:
        direction = "above" if z > 0 else "below"
        return f"significantly {direction} average"


def compare_normative(
    morphometrics: dict,
    age: float,
    sex: str = "M",
    field_strength_t: float = 0.0,
    subject_id: str = "",
) -> NormativeResult:
    """Compare individual morphometrics against age/sex norms.

    Applies corrections for:
    - ICV normalization (if available): removes sex/ethnicity head-size bias
    - Field strength (1.5T→3T): norms are 3T-based, 1.5T values scaled up
    - Sex-pooled vs sex-specific norms based on ICV availability

    Args:
        morphometrics: Summary dict from MorphometryResult.summary.
        age: Chronological age in years.
        sex: 'M' or 'F'.
        field_strength_t: MRI field strength in Tesla (0=unknown, 1.5, 3.0).
        subject_id: For logging.

    Returns:
        NormativeResult with z-scores for available metrics.
    """
    sex = sex.upper()
    if sex not in ("M", "F"):
        logger.warning(f"[{subject_id}] Unknown sex '{sex}', defaulting to 'M'")
        sex = "M"

    result = NormativeResult(subject_id=subject_id, age=age, sex=sex)
    scores = []
    icv_available = "normalization_method" in morphometrics
    field_corrected = False

    # Total brain volume
    # ICV normalization already cancels field strength bias in the ratio
    # (both numerator and denominator are biased in the same direction),
    # so field correction is only applied to RAW (non-ICV-normalized) values.
    vol_key = "total_brain_volume_normalized_cm3" if icv_available else "total_brain_volume_cm3"
    vol = morphometrics.get(vol_key) or morphometrics.get("total_brain_volume_cm3")
    if vol:
        raw_vol = vol
        if not icv_available:
            vol, fc = _apply_field_correction(vol, "brain_volume", field_strength_t)
            field_corrected = field_corrected or fc
        if icv_available:
            mean, std = _get_norm(_BRAIN_VOLUME_NORMS_POOLED, age)
        else:
            sex_norms = _BRAIN_VOLUME_NORMS.get(sex, _BRAIN_VOLUME_NORMS["M"])
            mean, std = _get_norm(sex_norms, age)
        z = (vol - mean) / std if std > 0 else 0.0
        scores.append(NormativeScore(
            metric="total_brain_volume",
            value=round(raw_vol, 1), expected=round(mean, 1), std=round(std, 1),
            z_score=round(z, 2),
            interpretation=_interpret_z(z, "brain volume"),
        ))

    # Hippocampal volume — same logic: skip field correction if ICV-normalized
    hippo_key = "hippocampus_total_normalized_mm3" if icv_available else "hippocampus_total_mm3"
    hippo = morphometrics.get(hippo_key) or morphometrics.get("hippocampus_total_mm3")
    if hippo:
        raw_hippo = hippo
        if not icv_available:
            hippo, fc = _apply_field_correction(hippo, "hippocampus_volume", field_strength_t)
            field_corrected = field_corrected or fc
        if icv_available:
            mean, std = _get_norm(_HIPPOCAMPUS_NORMS_POOLED, age)
        else:
            sex_norms = _HIPPOCAMPUS_NORMS.get(sex, _HIPPOCAMPUS_NORMS["M"])
            mean, std = _get_norm(sex_norms, age)
        z = (hippo - mean) / std if std > 0 else 0.0
        scores.append(NormativeScore(
            metric="hippocampus_volume",
            value=round(raw_hippo, 0), expected=round(mean, 0), std=round(std, 0),
            z_score=round(z, 2),
            interpretation=_interpret_z(z, "hippocampal volume"),
        ))

    # Mean cortical thickness — NOT ICV-normalized (ethnicity-stable, Wisch 2025)
    # Field correction IS needed (+4.5% at 3T vs 1.5T, Reuter 2012)
    thickness = morphometrics.get("mean_cortical_thickness_mm")
    if thickness:
        raw_thickness = thickness
        thickness, fc = _apply_field_correction(thickness, "cortical_thickness", field_strength_t)
        field_corrected = field_corrected or fc
        mean, std = _get_norm(_CORTICAL_THICKNESS_NORMS, age)
        z = (thickness - mean) / std if std > 0 else 0.0
        scores.append(NormativeScore(
            metric="cortical_thickness",
            value=round(raw_thickness, 3), expected=round(mean, 3), std=round(std, 3),
            z_score=round(z, 2),
            interpretation=_interpret_z(z, "cortical thickness"),
        ))

    # WMH volume — sex-pooled (primarily age-driven), no ICV/field correction needed
    wmh_ml = morphometrics.get("wmh_volume_ml")
    if wmh_ml is not None and wmh_ml >= 0:
        mean, std = _get_norm(_WMH_VOLUME_NORMS, age)
        # WMH is positively skewed — higher = worse
        z = (wmh_ml - mean) / std if std > 0 else 0.0
        interp = (
            "normal WMH burden" if z < 1.0
            else "mildly elevated WMH" if z < 2.0
            else "significantly elevated WMH (vascular risk)"
        )
        scores.append(NormativeScore(
            metric="wmh_volume",
            value=round(wmh_ml, 2), expected=round(mean, 1), std=round(std, 1),
            z_score=round(z, 2),
            interpretation=interp,
        ))

    result.scores = scores

    # Overall summary
    if scores:
        z_values = [s.z_score for s in scores]
        result.summary = {
            "scores": [
                {
                    "metric": s.metric,
                    "value": s.value,
                    "expected": s.expected,
                    "z_score": s.z_score,
                    "interpretation": s.interpretation,
                }
                for s in scores
            ],
            "overall_z_mean": round(float(np.mean(z_values)), 2),
            "icv_normalized": icv_available,
            "field_strength_corrected": field_corrected,
            "field_strength_t": field_strength_t if field_strength_t > 0 else None,
        }
        logger.info(f"[{subject_id}] Normative comparison: "
                    f"{len(scores)} metrics, mean z={np.mean(z_values):.2f}")

    return result
