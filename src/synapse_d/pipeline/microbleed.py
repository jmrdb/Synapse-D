"""Cerebral Microbleed (CMB) detection from SWI.

Detects and quantifies cerebral microbleeds from Susceptibility Weighted
Imaging (SWI), a key biomarker for cerebral small vessel disease (CSVD),
cerebral amyloid angiopathy (CAA), and vascular dementia risk.

CMB characteristics on SWI:
- Small (2-10mm diameter), round/ovoid hypointense foci
- Signal loss due to hemosiderin deposits from prior microhemorrhages
- Location pattern distinguishes etiology:
  - Lobar (cortical/subcortical): CAA-related
  - Deep (basal ganglia, thalamus): hypertensive arteriopathy
  - Infratentorial (brainstem, cerebellum): hypertensive arteriopathy

Clinical significance:
- CMB count correlates with future stroke risk
- CMB + WMH together = comprehensive CSVD assessment
- Lobar CMB pattern → amyloid-related → AD risk factor

Pipeline:
    1. Brain extraction (HD-BET)
    2. CMB candidate detection (dark spot detection on SWI)
    3. False positive filtering (vessels, calcifications, air)
    4. Quantification: count, size, anatomical location classification

Reference scales:
- MARS (Microbleed Anatomical Rating Scale): lobar/deep/infratentorial
- BOMBS (Brain Observer MicroBleed Scale): standardized counting
"""

from dataclasses import dataclass, field
from pathlib import Path

import nibabel as nib
import numpy as np
from loguru import logger

from synapse_d.config import settings


@dataclass
class MicrobleedResult:
    """CMB detection and quantification result.

    Attributes:
        subject_id: BIDS subject ID.
        cmb_count: Total number of detected microbleeds.
        cmb_locations: List of individual CMB locations and sizes.
        regional_counts: CMB count by anatomical region (MARS classification).
        mars_category: MARS classification (lobar/deep/mixed).
        clinical_significance: Interpretation of CMB pattern.
        segmentation_path: Path to CMB detection mask.
        success: Whether detection completed.
        used_fallback: Whether threshold-based fallback was used.
        errors: List of errors/warnings.
    """

    subject_id: str = ""
    cmb_count: int = 0
    cmb_locations: list[dict] = field(default_factory=list)
    regional_counts: dict = field(default_factory=dict)
    mars_category: str = "none"
    clinical_significance: str = ""
    segmentation_path: Path | None = None
    success: bool = False
    used_fallback: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cmb_count": self.cmb_count,
            "regional_counts": self.regional_counts,
            "mars_category": self.mars_category,
            "clinical_significance": self.clinical_significance,
            "cmb_locations": self.cmb_locations,
            "segmentation_path": str(self.segmentation_path) if self.segmentation_path else None,
            "success": self.success,
            "used_fallback": self.used_fallback,
            "errors": self.errors,
        }


# CMB size criteria (mm diameter)
_CMB_MIN_DIAMETER_MM = 2.0
_CMB_MAX_DIAMETER_MM = 10.0

# Axial zone boundaries for MARS anatomical classification
# (fraction of brain height from inferior to superior)
_MARS_ZONES = {
    "infratentorial": (0.0, 0.25),    # Bottom 25%: brainstem, cerebellum
    "deep": (0.25, 0.65),             # Middle 40%: basal ganglia, thalamus
    "lobar": (0.65, 1.0),             # Top 35%: cortical, subcortical
}


def detect_microbleeds(
    swi_path: Path,
    output_dir: Path | None = None,
    device: str | None = None,
) -> MicrobleedResult:
    """Detect cerebral microbleeds from SWI.

    Args:
        swi_path: Path to SWI NIfTI file.
        output_dir: Output directory.
        device: Compute device.

    Returns:
        MicrobleedResult with CMB count, locations, and classification.
    """
    from synapse_d.utils.bids import get_subject_id, make_output_dir

    output_dir = output_dir or settings.output_dir
    device = device or settings.device
    subject_id = get_subject_id(swi_path)
    out_dir = make_output_dir(output_dir, subject_id)
    result = MicrobleedResult(subject_id=subject_id)

    logger.info(f"[{subject_id}] Starting CMB detection pipeline (SWI)")

    # Validate input
    try:
        img = nib.load(str(swi_path))
        data = np.asarray(img.dataobj, dtype=np.float32)
        voxel_size = [float(z) for z in img.header.get_zooms()[:3]]
        logger.info(f"[{subject_id}] SWI: shape={data.shape[:3]}, voxel={voxel_size}mm")
    except Exception as e:
        result.errors.append(f"SWI validation failed: {e}")
        return result

    # Step 1: Brain extraction
    brain_data, brain_mask = _extract_brain_swi(
        data, swi_path, out_dir, device, subject_id
    )
    if brain_data is None:
        result.errors.append("SWI brain extraction failed")
        return result

    # Step 2: CMB candidate detection
    candidates = _detect_cmb_candidates(brain_data, brain_mask, voxel_size, subject_id)

    # Step 3: Filter false positives
    cmb_mask, cmb_labels = _filter_candidates(
        candidates, brain_data, voxel_size, subject_id
    )

    # Step 4: Quantification and classification
    _quantify_cmbs(result, cmb_labels, brain_mask, voxel_size, data.shape[:3], img.affine, subject_id)

    # Save CMB mask
    cmb_mask_path = out_dir / f"{subject_id}_CMB_mask.nii.gz"
    nib.save(nib.Nifti1Image(cmb_mask.astype(np.uint8), img.affine, img.header),
             str(cmb_mask_path))
    result.segmentation_path = cmb_mask_path

    result.success = True
    result.used_fallback = True  # Always threshold-based for now (no DL model)
    logger.info(f"[{subject_id}] CMB detection complete: {result.cmb_count} microbleeds, "
                f"MARS={result.mars_category}")
    return result


def _extract_brain_swi(
    data: np.ndarray, swi_path: Path, out_dir: Path,
    device: str, subject_id: str,
) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Brain extraction for SWI — uses HD-BET or intensity fallback."""
    import subprocess

    brain_path = out_dir / f"{subject_id}_SWI_brain.nii.gz"
    logger.info(f"[{subject_id}] CMB Step 1/4: SWI brain extraction")

    try:
        cmd = [
            "hd-bet", "-i", str(swi_path), "-o", str(brain_path),
            "-device", device, "--disable_tta", "--save_bet_mask",
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        brain_img = nib.load(str(brain_path))
        brain_data = np.asarray(brain_img.dataobj, dtype=np.float32)

        # Find mask
        for suffix in ["_bet.nii.gz", "_mask.nii.gz"]:
            mask_path = brain_path.with_name(brain_path.name.replace(".nii.gz", suffix))
            if mask_path.exists():
                mask_data = np.asarray(nib.load(str(mask_path)).dataobj) > 0
                return brain_data, mask_data

        mask_data = brain_data > 0
        return brain_data, mask_data

    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        logger.warning(f"[{subject_id}] HD-BET unavailable, using SWI intensity fallback")
        # Fallback: use a LOW threshold to preserve dark CMB candidates
        # SWI CMBs are hypointense — aggressive skull stripping removes them
        # Use 2nd percentile (very conservative) to keep dark brain voxels
        nonzero = data[data > 0]
        if len(nonzero) < 1000:
            return None, None
        threshold = np.percentile(nonzero, 2)
        mask = data > threshold
        logger.info(f"[{subject_id}] SWI fallback mask: threshold={threshold:.1f}, "
                    f"voxels={mask.sum():,}")
        return data * mask, mask


def _detect_cmb_candidates(
    brain_data: np.ndarray, brain_mask: np.ndarray,
    voxel_size: list[float], subject_id: str,
) -> np.ndarray:
    """Detect CMB candidates as small dark foci in SWI.

    CMBs appear as small, round hypointense spots on SWI due to
    susceptibility effects of hemosiderin deposits.

    Method: Global intensity statistics — voxels significantly
    darker than the brain-wide mean (below mean - 2.5*std).
    """
    logger.info(f"[{subject_id}] CMB Step 2/4: Candidate detection")

    # Compute statistics on brain region only
    brain_voxels = brain_data[brain_mask & (brain_data > 0)]
    if len(brain_voxels) < 1000:
        return np.zeros_like(brain_data, dtype=bool)

    brain_mean = float(brain_voxels.mean())
    brain_std = float(brain_voxels.std())

    # CMB candidates: voxels significantly darker than average
    dark_threshold = brain_mean - 2.5 * brain_std

    # SWI intensity distributions are often highly skewed (many dark voxels).
    # If mean-2.5*std falls below zero, the threshold is useless because
    # all positive voxels pass. Fall back to percentile-based detection.
    if dark_threshold <= 0:
        dark_threshold = float(np.percentile(brain_voxels, 5))
        logger.info(f"[{subject_id}] Skewed SWI distribution (mean-2.5*std={brain_mean - 2.5 * brain_std:.0f}), "
                    f"using 5th percentile threshold: {dark_threshold:.1f}")

    candidates = (brain_data < dark_threshold) & (brain_data > 0) & brain_mask

    logger.info(f"[{subject_id}] Dark threshold={dark_threshold:.1f}, "
                f"candidates: {candidates.sum()}")
    return candidates


def _filter_candidates(
    candidates: np.ndarray, brain_data: np.ndarray,
    voxel_size: list[float], subject_id: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Filter CMB candidates by size and shape criteria.

    Removes:
    - Too small (< 2mm): noise
    - Too large (> 10mm): likely veins or other structures
    - Non-spherical objects: likely vessels (elongated)
    """
    from scipy.ndimage import label, find_objects

    logger.info(f"[{subject_id}] CMB Step 3/4: False positive filtering")

    labeled, n_components = label(candidates)
    cmb_mask = np.zeros_like(candidates, dtype=bool)

    voxel_vol_mm3 = float(np.prod(voxel_size))

    # Volume thresholds for CMB (sphere: V = 4/3 * pi * r^3)
    min_vol_mm3 = (4 / 3) * np.pi * (_CMB_MIN_DIAMETER_MM / 2) ** 3  # ~4.2 mm³
    max_vol_mm3 = (4 / 3) * np.pi * (_CMB_MAX_DIAMETER_MM / 2) ** 3  # ~524 mm³

    cmb_count = 0
    for i, slc in enumerate(find_objects(labeled), 1):
        if slc is None:
            continue

        component = labeled[slc] == i
        vol_voxels = component.sum()
        vol_mm3 = vol_voxels * voxel_vol_mm3

        # Size filter
        if vol_mm3 < min_vol_mm3 or vol_mm3 > max_vol_mm3:
            continue

        # Shape filter: check aspect ratio in mm (not voxels)
        # Anisotropic voxels (e.g., 0.5x0.5x2mm) would otherwise
        # misclassify spherical CMBs as elongated
        extents_mm = [(s.stop - s.start) * vs for s, vs in zip(slc, voxel_size)]
        if len(extents_mm) == 3:
            max_extent = max(extents_mm)
            min_extent = max(min(extents_mm), 0.001)
            aspect_ratio = max_extent / min_extent
            # CMB should be roughly round — reject elongated structures (vessels)
            if aspect_ratio > 3.0:
                continue

        # Passed all filters → mark as CMB
        cmb_mask[slc][component] = True
        cmb_count += 1

    logger.info(f"[{subject_id}] Filtered CMBs: {cmb_count} "
                f"(from {n_components} candidates)")

    # Re-label the filtered mask
    cmb_labels, _ = label(cmb_mask)
    return cmb_mask, cmb_labels


def _quantify_cmbs(
    result: MicrobleedResult, cmb_labels: np.ndarray,
    brain_mask: np.ndarray, voxel_size: list[float],
    volume_shape: tuple, affine: np.ndarray, subject_id: str,
) -> None:
    """Quantify CMBs: count, size, and anatomical location (MARS)."""
    from scipy.ndimage import find_objects

    logger.info(f"[{subject_id}] CMB Step 4/4: Quantification & MARS classification")

    voxel_vol_mm3 = float(np.prod(voxel_size))
    n_cmbs = cmb_labels.max()
    result.cmb_count = int(n_cmbs)

    if n_cmbs == 0:
        result.mars_category = "none"
        result.clinical_significance = "미세출혈이 검출되지 않았습니다."
        result.regional_counts = {"lobar": 0, "deep": 0, "infratentorial": 0}
        return

    # Determine which voxel axis corresponds to Superior-Inferior (SI)
    # by finding the axis most aligned with the S-I direction in the affine
    si_axis = _find_si_axis(affine)
    si_height = volume_shape[si_axis]

    # Classify each CMB by MARS zone
    regional = {"lobar": 0, "deep": 0, "infratentorial": 0}
    locations = []

    for i in range(1, n_cmbs + 1):
        component = cmb_labels == i
        vol_mm3 = float(component.sum() * voxel_vol_mm3)
        diameter_mm = 2 * (3 * vol_mm3 / (4 * np.pi)) ** (1 / 3)

        # Find geometric center for location classification
        coords = np.argwhere(component)
        center = coords.mean(axis=0)
        z_fraction = center[si_axis] / si_height if si_height > 0 else 0.5

        # MARS classification based on axial position
        zone = "lobar"  # default
        for zone_name, (z_low, z_high) in _MARS_ZONES.items():
            if z_low <= z_fraction < z_high:
                zone = zone_name
                break

        regional[zone] += 1
        locations.append({
            "id": i,
            "center_voxel": [round(c) for c in center.tolist()],
            "diameter_mm": round(diameter_mm, 1),
            "volume_mm3": round(vol_mm3, 1),
            "zone": zone,
        })

    result.regional_counts = regional
    result.cmb_locations = locations

    # MARS category determination
    if regional["lobar"] > 0 and regional["deep"] == 0 and regional["infratentorial"] == 0:
        result.mars_category = "lobar_only"
    elif regional["deep"] > 0 or regional["infratentorial"] > 0:
        if regional["lobar"] > 0:
            result.mars_category = "mixed"
        else:
            result.mars_category = "deep_or_infratentorial"
    else:
        result.mars_category = "none"

    # Clinical significance
    result.clinical_significance = _interpret_cmbs(
        result.cmb_count, result.mars_category, regional
    )

    logger.info(f"[{subject_id}] CMBs: {n_cmbs} total — "
                f"lobar={regional['lobar']}, deep={regional['deep']}, "
                f"infra={regional['infratentorial']} → {result.mars_category}")


def _interpret_cmbs(count: int, mars: str, regional: dict) -> str:
    """Generate clinical interpretation of CMB findings."""
    if count == 0:
        return "미세출혈이 검출되지 않았습니다."

    parts = []

    # Count-based severity
    if count <= 2:
        parts.append(f"미세출혈 {count}개 검출 (경미).")
    elif count <= 10:
        parts.append(f"미세출혈 {count}개 검출 (중등도).")
    else:
        parts.append(f"미세출혈 {count}개 검출 (다발성 — 뇌소혈관질환 의심).")

    # Pattern-based interpretation
    if mars == "lobar_only":
        parts.append(
            "엽성(lobar) 분포: 뇌아밀로이드혈관병(CAA) 가능성. "
            "알츠하이머병 위험 인자로 평가됩니다."
        )
    elif mars == "deep_or_infratentorial":
        parts.append(
            "심부/천막하(deep/infratentorial) 분포: "
            "고혈압성 소혈관병(hypertensive arteriopathy) 시사."
        )
    elif mars == "mixed":
        parts.append(
            "혼합 분포: 엽성 + 심부 미세출혈이 동시에 관찰됩니다. "
            "복합 소혈관질환 평가가 필요합니다."
        )

    # WMH synergy note
    parts.append(
        "* FLAIR WMH 결과와 함께 종합적인 뇌소혈관질환 평가를 권장합니다."
    )

    return " ".join(parts)


def _find_si_axis(affine: np.ndarray) -> int:
    """Find the voxel axis most aligned with Superior-Inferior direction.

    The NIfTI affine maps voxel indices to RAS world coordinates.
    Row 2 of the rotation matrix gives the S-I component for each voxel axis.
    We return the voxel axis with the largest S-I alignment.

    Returns:
        Voxel axis index (0, 1, or 2) corresponding to S-I.
    """
    rotation = affine[:3, :3]
    si_alignment = np.abs(rotation[2, :])
    return int(np.argmax(si_alignment))
