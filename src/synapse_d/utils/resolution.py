"""MRI resolution detection and analysis grade gating.

Automatically classifies input MRI into analysis tiers based on spatial
resolution (voxel size), determining which pipeline features are reliable.

Tier system:
- FULL:     ≤1.5mm isotropic → all features (cortical thickness, Brain Age, volumes)
- STANDARD: 1.5~3mm any axis → volumes reliable, cortical thickness with warning
- BASIC:    >3mm any axis    → SynthSeg volumes only, cortical thickness/Brain Age blocked

Modality rules:
- T1: subject to all tiers (thickness + volume + Brain Age)
- T2/FLAIR/dMRI: volume-only by design — no cortical thickness measurement,
  so resolution mainly affects volumetric and WMH segmentation accuracy

Resolution thresholds based on:
- FreeSurfer/FastSurfer: 1mm isotropic required for cortical thickness (Reuter 2012)
- SynthSeg: validated 0.5–9mm, volumetric ICC ≥0.90 at 5mm (Billot 2023)
- SFCN Brain Age: trained on 1mm UK Biobank, MAE degrades 2.5→7-10yr at 5mm
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import nibabel as nib
from loguru import logger


class AnalysisTier(str, Enum):
    """Analysis capability tier based on input resolution."""

    FULL = "full"          # ≤1.5mm — all features available
    STANDARD = "standard"  # 1.5~3mm — volumes OK, thickness with warning
    BASIC = "basic"        # >3mm — volumes only, thickness/Brain Age blocked


class Modality(str, Enum):
    """MRI modality type."""

    T1 = "T1"
    T2 = "T2"
    FLAIR = "FLAIR"
    DWI = "DWI"
    SWI = "SWI"
    UNKNOWN = "unknown"


# Resolution thresholds (mm) — based on the LARGEST voxel dimension
_FULL_THRESHOLD = 1.5
_STANDARD_THRESHOLD = 3.0


@dataclass
class ResolutionInfo:
    """MRI resolution analysis result.

    Attributes:
        voxel_size: Voxel dimensions in mm (x, y, z).
        max_voxel_dim: Largest voxel dimension (determines tier).
        is_isotropic: Whether voxels are roughly cubic (max/min ratio < 1.5).
        slice_thickness: Largest dimension (typically slice thickness).
        tier: Analysis capability tier.
        modality: Detected MRI modality.
        available_features: List of features available at this tier.
        blocked_features: List of features blocked at this tier.
        warnings: Resolution-related warnings for the user.
    """

    voxel_size: tuple[float, float, float] = (0, 0, 0)
    max_voxel_dim: float = 0.0
    is_isotropic: bool = False
    slice_thickness: float = 0.0
    tier: AnalysisTier = AnalysisTier.BASIC
    modality: Modality = Modality.UNKNOWN
    available_features: list[str] = None  # type: ignore[assignment]
    blocked_features: list[str] = None  # type: ignore[assignment]
    warnings: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.available_features is None:
            self.available_features = []
        if self.blocked_features is None:
            self.blocked_features = []
        if self.warnings is None:
            self.warnings = []

    def to_dict(self) -> dict:
        return {
            "voxel_size_mm": list(self.voxel_size),
            "max_voxel_dim_mm": round(self.max_voxel_dim, 2),
            "slice_thickness_mm": round(self.slice_thickness, 2),
            "is_isotropic": self.is_isotropic,
            "tier": self.tier.value,
            "modality": self.modality.value,
            "available_features": self.available_features,
            "blocked_features": self.blocked_features,
            "warnings": self.warnings,
        }


def detect_resolution(
    nifti_path: Path, modality: Modality | str = Modality.UNKNOWN
) -> ResolutionInfo:
    """Detect MRI resolution and determine analysis tier.

    Args:
        nifti_path: Path to NIfTI file.
        modality: MRI modality (T1, T2, FLAIR, DWI).

    Returns:
        ResolutionInfo with tier, available/blocked features, and warnings.
    """
    if isinstance(modality, str) and not isinstance(modality, Modality):
        modality = _detect_modality(modality, nifti_path)

    try:
        img = nib.load(str(nifti_path))
        zooms = img.header.get_zooms()[:3]
        voxel_size = tuple(round(float(z), 3) for z in zooms)
    except Exception as e:
        logger.error(f"Failed to read resolution from {nifti_path}: {e}")
        return ResolutionInfo(warnings=[f"Resolution detection failed: {e}"])

    max_dim = max(voxel_size)
    min_dim = min(voxel_size)

    # Validate voxel dimensions
    if max_dim <= 0 or min_dim <= 0:
        logger.error(f"Invalid voxel size {voxel_size} from {nifti_path}")
        return ResolutionInfo(
            voxel_size=voxel_size,
            tier=AnalysisTier.BASIC,
            warnings=[f"Invalid voxel dimensions: {voxel_size}"],
        )

    is_iso = (max_dim / min_dim) < 1.5

    # Determine tier
    tier = _classify_tier(max_dim, modality)

    # Determine available/blocked features
    available, blocked, warnings = _gate_features(tier, modality, max_dim, voxel_size)

    info = ResolutionInfo(
        voxel_size=voxel_size,
        max_voxel_dim=max_dim,
        is_isotropic=is_iso,
        slice_thickness=max_dim,
        tier=tier,
        modality=modality,
        available_features=available,
        blocked_features=blocked,
        warnings=warnings,
    )

    logger.info(
        f"Resolution: {voxel_size}mm, max={max_dim:.1f}mm, "
        f"iso={is_iso}, tier={tier.value}, modality={modality.value}"
    )
    return info


def _classify_tier(max_dim: float, modality: Modality) -> AnalysisTier:
    """Classify analysis tier based on resolution and modality.

    T2/FLAIR/DWI are volume-only by design, so they get at least STANDARD
    tier (thickness is never applicable for these modalities).
    """
    if modality in (Modality.T2, Modality.FLAIR, Modality.DWI, Modality.SWI):
        # Non-T1 modalities: volume-only, thickness N/A
        # Even 5mm FLAIR is usable for SynthSeg volumetrics
        if max_dim <= _STANDARD_THRESHOLD:
            return AnalysisTier.FULL
        return AnalysisTier.STANDARD  # Still usable for volumes

    # T1 modality: full tier system
    if max_dim <= _FULL_THRESHOLD:
        return AnalysisTier.FULL
    if max_dim <= _STANDARD_THRESHOLD:
        return AnalysisTier.STANDARD
    return AnalysisTier.BASIC


def _gate_features(
    tier: AnalysisTier,
    modality: Modality,
    max_dim: float,
    voxel_size: tuple[float, ...],
) -> tuple[list[str], list[str], list[str]]:
    """Determine available/blocked features and generate warnings."""
    available = []
    blocked = []
    warnings = []

    is_t1 = modality in (Modality.T1, Modality.UNKNOWN)
    if modality == Modality.UNKNOWN:
        warnings.append("모달리티를 자동 감지하지 못했습니다. T1으로 가정하여 처리합니다.")

    if tier == AnalysisTier.FULL:
        available = ["brain_extraction", "segmentation", "volumetrics"]
        if is_t1:
            available.extend(["cortical_thickness", "brain_age", "normative_comparison"])
        else:
            available.extend(["wmh_segmentation"])
            blocked.append("cortical_thickness (T2/FLAIR 모달리티)")

    elif tier == AnalysisTier.STANDARD:
        available = ["brain_extraction", "segmentation", "volumetrics"]
        if is_t1:
            available.append("normative_comparison")
            available.append("cortical_thickness")
            warnings.append(
                f"해상도 {max_dim:.1f}mm: 피질 두께 정확도 저하 "
                f"(오차 ±0.3mm, 권장 ≤1.5mm)"
            )
            available.append("brain_age")
            warnings.append(
                f"해상도 {max_dim:.1f}mm: Brain Age 오차 증가 "
                f"(MAE ~4년, 권장 ≤1.5mm)"
            )
        else:
            available.extend(["wmh_segmentation"])
            warnings.append(
                f"해상도 {max_dim:.1f}mm: 소형 WMH 검출 민감도 저하 (~70%)"
            )

    elif tier == AnalysisTier.BASIC:
        available = ["brain_extraction", "volumetrics"]
        warnings.append(
            f"해상도 {max_dim:.1f}mm: SynthSeg 용적 측정만 가능 (ICC ~0.90)"
        )
        if is_t1:
            blocked.append("cortical_thickness (해상도 부족, 오차 ±0.8~1.2mm)")
            blocked.append("brain_age (해상도 부족, MAE 7~10년)")
            blocked.append("segmentation (FastSurfer 신뢰 불가)")
            warnings.append(
                "SynthSeg 기반 용적 측정으로 전환됩니다. "
                "피질 두께 및 Brain Age는 1.5mm 이하 T1 MRI에서만 제공됩니다."
            )
        else:
            available.append("wmh_segmentation")
            warnings.append(
                f"해상도 {max_dim:.1f}mm: 소형 WMH(<3mL) 검출 불가, "
                f"대형 WMH만 신뢰 (Dice ~0.70)"
            )

    return available, blocked, warnings


def _detect_modality(modality_str: str, nifti_path: Path) -> Modality:
    """Detect modality from string or filename."""
    s = modality_str.upper().strip()
    if s in ("T1", "T1W", "T1-WEIGHTED"):
        return Modality.T1
    if s in ("T2", "T2W", "T2-WEIGHTED"):
        return Modality.T2
    if s in ("FLAIR", "T2-FLAIR", "T2FLAIR"):
        return Modality.FLAIR
    if s in ("DWI", "DMRI", "DTI", "DIFFUSION"):
        return Modality.DWI
    if s in ("SWI", "SUSCEPTIBILITY"):
        return Modality.SWI

    # Try to detect from filename (BIDS convention)
    name = nifti_path.name.lower()
    if "_t1w" in name or "_t1_" in name:
        return Modality.T1
    if "_flair" in name:
        return Modality.FLAIR
    if "_t2w" in name or "_t2_" in name:
        return Modality.T2
    if "_swi" in name:
        return Modality.SWI
    if "_dwi" in name or "_dti" in name:
        return Modality.DWI

    return Modality.UNKNOWN
