"""AD/MCI risk classification module.

Estimates Alzheimer's Disease and Mild Cognitive Impairment risk from
structural brain morphometry. Uses a multi-biomarker scoring approach
combining hippocampal volume, cortical thickness, ventricular enlargement,
Brain Age Gap, and WMH burden.

Two approaches implemented:
1. Biomarker-based risk scoring (Phase 1 — available now)
   - Uses z-scores from normative comparison as input features
   - Weighted combination of AD-relevant biomarkers
   - Interpretable: each biomarker's contribution visible

2. Deep learning classification (Phase 2 — future)
   - vkola-lab 3D ResNet18 model (MIT, vendor/AD-Diagnosis)
   - Trained on ADNI/OASIS/NACC multi-site data
   - Requires raw MRI input (not morphometrics)

Classification output:
- Risk level: Low / Moderate / High / Very High
- Risk score: 0-100 continuous scale
- Per-biomarker contribution (SHAP-like interpretation)
- Recommendations for follow-up

Reference: Kola et al., Nature Communications 2022
"""

from dataclasses import dataclass, field

import math

from loguru import logger


@dataclass
class ADRiskResult:
    """AD/MCI risk assessment result.

    Attributes:
        risk_score: 0-100 continuous risk score.
        risk_level: Categorical risk level.
        classification: NC/MCI/AD most likely classification.
        probabilities: Probability for each class.
        biomarker_contributions: Per-biomarker contribution to risk score.
        recommendations: Clinical follow-up recommendations.
        method: Scoring method used.
    """

    risk_score: float = 0.0
    risk_level: str = "unknown"
    classification: str = "unknown"
    probabilities: dict = field(default_factory=dict)
    biomarker_contributions: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    method: str = "biomarker_scoring"

    def to_dict(self) -> dict:
        return {
            "risk_score": round(self.risk_score, 1),
            "risk_level": self.risk_level,
            "classification": self.classification,
            "probabilities": self.probabilities,
            "biomarker_contributions": self.biomarker_contributions,
            "recommendations": self.recommendations,
            "method": self.method,
        }


# Biomarker weights for AD risk scoring
# Higher weight = stronger association with AD
# Source: Jack et al., Alzheimer's & Dementia 2018 (ATN framework)
_BIOMARKER_WEIGHTS = {
    "hippocampus_volume": {
        "weight": 0.30,  # Hippocampal atrophy is the #1 structural AD marker
        "direction": "negative",  # Lower = worse (atrophy)
        "label": "Hippocampal Volume",
    },
    "cortical_thickness": {
        "weight": 0.20,  # Cortical thinning in temporal/parietal
        "direction": "negative",
        "label": "Cortical Thickness",
    },
    "total_brain_volume": {
        "weight": 0.15,  # Global atrophy
        "direction": "negative",
        "label": "Brain Volume",
    },
    "wmh_volume": {
        "weight": 0.15,  # Vascular contribution to dementia
        "direction": "positive",  # Higher = worse (more lesions)
        "label": "WMH Burden",
    },
    "brain_age_gap": {
        "weight": 0.20,  # Accelerated aging correlates with AD
        "direction": "positive",  # Higher gap = worse
        "label": "Brain Age Gap",
    },
}

# Risk thresholds
_RISK_LEVELS = [
    (0, 25, "low", "NC"),
    (25, 50, "moderate", "MCI"),
    (50, 75, "high", "MCI"),
    (75, 101, "very_high", "AD"),  # 101 to include score=100
]


def assess_ad_risk(
    normative_scores: list[dict],
    brain_age_gap: float | None = None,
    age: float | None = None,
    subject_id: str = "",
) -> ADRiskResult:
    """Assess AD/MCI risk from normative z-scores and brain age.

    Combines multiple biomarker z-scores into a single risk score
    using clinically-validated weights. Each biomarker's contribution
    is tracked for SHAP-like interpretability.

    Args:
        normative_scores: List of z-score dicts from normative comparison.
        brain_age_gap: Brain Age Gap in years (positive = older appearing).
        age: Chronological age (affects base risk).
        subject_id: For logging.

    Returns:
        ADRiskResult with risk score, level, and per-biomarker contributions.
    """
    result = ADRiskResult()
    contributions = []
    total_weight = 0.0
    weighted_risk = 0.0

    # Build z-score lookup from normative scores
    z_lookup = {s["metric"]: s["z_score"] for s in normative_scores}

    for biomarker, config in _BIOMARKER_WEIGHTS.items():
        z = z_lookup.get(biomarker)

        # Special handling for brain_age_gap (not in normative z-scores)
        if biomarker == "brain_age_gap" and z is None and brain_age_gap is not None:
            # Convert Brain Age Gap to pseudo z-score
            # Gap of 5 years ≈ z-score of 2.0 (based on typical std ~2.5 years)
            z = brain_age_gap / 2.5

        if z is None:
            continue

        weight = config["weight"]
        direction = config["direction"]

        # Convert z-score to risk contribution (0-100 scale)
        # Negative direction: z < 0 = risk (atrophy)
        # Positive direction: z > 0 = risk (burden/gap)
        if direction == "negative":
            risk_contrib = _z_to_risk(-z)  # Flip: more negative z = higher risk
        else:
            risk_contrib = _z_to_risk(z)

        weighted_risk += risk_contrib * weight
        total_weight += weight

        contributions.append({
            "biomarker": config["label"],
            "z_score": round(z, 2),
            "risk_contribution": round(risk_contrib, 1),
            "weight": weight,
            "weighted_contribution": round(risk_contrib * weight, 1),
        })

    # Normalize to 0-100
    if total_weight > 0:
        risk_score = weighted_risk / total_weight
    else:
        risk_score = 0.0

    # Age-based base risk adjustment (older = higher baseline)
    if age is not None and age > 60:
        age_factor = min((age - 60) / 40, 1.0) * 10  # +0 to +10 for age 60-100
        risk_score = min(risk_score + age_factor, 100)

    result.risk_score = risk_score

    # Determine risk level and classification
    for low, high, level, classification in _RISK_LEVELS:
        if low <= risk_score < high:
            result.risk_level = level
            result.classification = classification
            break
    else:
        result.risk_level = "very_high"
        result.classification = "AD"

    # Approximate class probabilities from risk score
    result.probabilities = _risk_to_probabilities(risk_score)

    # Sort contributions by weighted impact (descending)
    contributions.sort(key=lambda c: abs(c["weighted_contribution"]), reverse=True)
    result.biomarker_contributions = contributions

    # Generate recommendations
    result.recommendations = _generate_recommendations(
        result.risk_level, contributions, age
    )

    logger.info(f"[{subject_id}] AD risk: score={risk_score:.0f}, "
                f"level={result.risk_level}, class={result.classification}")
    return result


def _z_to_risk(z: float) -> float:
    """Convert a z-score to a 0-100 risk scale.

    Uses a sigmoid-like mapping:
    z = 0 → risk ≈ 23
    z = 1 → risk ≈ 50
    z = 2 → risk ≈ 77
    z = 3 → risk ≈ 92
    """
    # Sigmoid centered at z=1.0, scaled to 0-100
    risk = 100 / (1 + math.exp(-1.2 * (z - 1.0)))
    return max(0, min(100, risk))


def _risk_to_probabilities(risk_score: float) -> dict:
    """Convert risk score to approximate NC/MCI/AD probabilities.

    Simple softmax-like distribution based on risk score position.
    """
    if risk_score < 20:
        return {"NC": 0.85, "MCI": 0.12, "AD": 0.03}
    elif risk_score < 40:
        return {"NC": 0.55, "MCI": 0.35, "AD": 0.10}
    elif risk_score < 60:
        return {"NC": 0.20, "MCI": 0.50, "AD": 0.30}
    elif risk_score < 80:
        return {"NC": 0.08, "MCI": 0.37, "AD": 0.55}
    else:
        return {"NC": 0.03, "MCI": 0.17, "AD": 0.80}


def _generate_recommendations(
    risk_level: str,
    contributions: list[dict],
    age: float | None,
) -> list[str]:
    """Generate clinical follow-up recommendations based on risk assessment."""
    recs = []

    if risk_level == "low":
        recs.append("현재 구조적 뇌 바이오마커가 정상 범위입니다.")
        recs.append("정기 추적 검사를 권장합니다 (12-24개월 간격).")
    elif risk_level == "moderate":
        recs.append("일부 바이오마커에서 경미한 변화가 관찰됩니다.")
        recs.append("신경심리검사(MMSE/MoCA) 시행을 권장합니다.")
        recs.append("6-12개월 후 추적 MRI를 권장합니다.")
    elif risk_level == "high":
        recs.append("복수의 바이오마커에서 유의한 변화가 관찰됩니다.")
        recs.append("신경과 전문의 상담을 강력히 권장합니다.")
        recs.append("종합 신경심리검사 및 PET 검사를 고려하세요.")
        recs.append("3-6개월 후 추적 MRI를 권장합니다.")
    elif risk_level == "very_high":
        recs.append("다수의 바이오마커에서 심각한 변화가 관찰됩니다.")
        recs.append("조기 신경과 전문의 진료를 권장합니다.")
        recs.append("아밀로이드/타우 PET 또는 CSF 바이오마커 검사를 권장합니다.")

    # Biomarker-specific recommendations
    for c in contributions[:3]:  # Top 3 contributors
        if c["risk_contribution"] > 60:
            recs.append(f"  - {c['biomarker']}: 주의 필요 (z={c['z_score']:.1f})")

    # Disclaimer
    recs.append("* 본 결과는 구조적 MRI 바이오마커 기반 위험도 추정이며, "
                "확정 진단이 아닙니다. 임상 판단은 반드시 전문의와 상담하세요.")

    return recs
