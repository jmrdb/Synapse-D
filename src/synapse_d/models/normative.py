"""Normative comparison module.

Compares individual brain morphometric measurements against population norms
to calculate z-scores (standard deviations from expected values for age/sex).

Positive z-score = larger than expected for age (e.g., ventricular enlargement)
Negative z-score = smaller than expected (e.g., hippocampal atrophy)

Reference values are derived from published large-scale studies:
- Brain volume: Bethlehem et al., Nature 2022 (Lifespan Brain Chart)
- Hippocampal volume: Nobis et al., NeuroImage 2019
- Cortical thickness: Fjell et al., Cerebral Cortex 2015

These are approximate normative ranges for MVP. Phase 2 will integrate
BrainStat for proper age-continuous normative modeling.
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

# Hippocampal volume norms (sum of L+R, mm3)
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
    subject_id: str = "",
) -> NormativeResult:
    """Compare individual morphometrics against age/sex norms.

    Args:
        morphometrics: Summary dict from MorphometryResult.summary.
        age: Chronological age in years.
        sex: 'M' or 'F'.
        subject_id: For logging.

    Returns:
        NormativeResult with z-scores for available metrics.
    """
    sex = sex.upper()
    if sex not in ("M", "F"):
        sex = "M"  # Default

    result = NormativeResult(subject_id=subject_id, age=age, sex=sex)
    scores = []
    icv_available = "normalization_method" in morphometrics

    # Total brain volume — use ICV-normalized value if available
    # ICV normalization removes sex/ethnicity head-size bias (Liu et al., 2025)
    vol_key = "total_brain_volume_normalized_cm3" if icv_available else "total_brain_volume_cm3"
    vol = morphometrics.get(vol_key) or morphometrics.get("total_brain_volume_cm3")
    if vol:
        sex_norms = _BRAIN_VOLUME_NORMS.get(sex, _BRAIN_VOLUME_NORMS["M"])
        mean, std = _get_norm(sex_norms, age)
        z = (vol - mean) / std if std > 0 else 0.0
        scores.append(NormativeScore(
            metric="total_brain_volume",
            value=vol, expected=round(mean, 1), std=round(std, 1),
            z_score=round(z, 2),
            interpretation=_interpret_z(z, "brain volume"),
        ))

    # Hippocampal volume — use ICV-normalized if available
    hippo_key = "hippocampus_total_normalized_mm3" if icv_available else "hippocampus_total_mm3"
    hippo = morphometrics.get(hippo_key) or morphometrics.get("hippocampus_total_mm3")
    if hippo:
        sex_norms = _HIPPOCAMPUS_NORMS.get(sex, _HIPPOCAMPUS_NORMS["M"])
        mean, std = _get_norm(sex_norms, age)
        z = (hippo - mean) / std if std > 0 else 0.0
        scores.append(NormativeScore(
            metric="hippocampus_volume",
            value=hippo, expected=round(mean, 0), std=round(std, 0),
            z_score=round(z, 2),
            interpretation=_interpret_z(z, "hippocampal volume"),
        ))

    # Mean cortical thickness — NO ICV normalization (ethnicity-stable per Wisch 2025)
    thickness = morphometrics.get("mean_cortical_thickness_mm")
    if thickness:
        mean, std = _get_norm(_CORTICAL_THICKNESS_NORMS, age)
        z = (thickness - mean) / std if std > 0 else 0.0
        scores.append(NormativeScore(
            metric="cortical_thickness",
            value=thickness, expected=round(mean, 3), std=round(std, 3),
            z_score=round(z, 2),
            interpretation=_interpret_z(z, "cortical thickness"),
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
        }
        logger.info(f"[{subject_id}] Normative comparison: "
                    f"{len(scores)} metrics, mean z={np.mean(z_values):.2f}")

    return result
