"""Morphometric analysis module.

Parses FastSurfer/FreeSurfer output files (aseg.stats, aparc.stats) to extract
structured volumetric and cortical thickness measurements. When FastSurfer
outputs are unavailable (e.g., dev mode with fallback brain extraction),
computes basic morphometrics from the brain mask.

Output format: MorphometryResult with region-level measurements suitable
for normative comparison and dashboard visualization.
"""

from dataclasses import dataclass, field
from pathlib import Path

import nibabel as nib
import numpy as np
from loguru import logger


@dataclass
class RegionMeasure:
    """Measurement for a single brain region.

    Attributes:
        name: Anatomical region name (e.g., 'Left-Hippocampus').
        volume_mm3: Volume in cubic millimeters.
        thickness_mm: Mean cortical thickness in mm (cortical regions only).
        area_mm2: Surface area in square mm (cortical regions only).
    """

    name: str
    volume_mm3: float = 0.0
    thickness_mm: float | None = None
    area_mm2: float | None = None


@dataclass
class MorphometryResult:
    """Full morphometric profile for a subject.

    Attributes:
        subject_id: BIDS subject identifier.
        total_brain_volume_cm3: Total brain volume in cm3.
        subcortical: List of subcortical region measurements.
        cortical_lh: Left hemisphere cortical parcellation.
        cortical_rh: Right hemisphere cortical parcellation.
        summary: Key summary metrics for dashboard display.
    """

    subject_id: str = ""
    total_brain_volume_cm3: float = 0.0
    subcortical: list[RegionMeasure] = field(default_factory=list)
    cortical_lh: list[RegionMeasure] = field(default_factory=list)
    cortical_rh: list[RegionMeasure] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# Key subcortical regions for clinical reporting
_KEY_SUBCORTICAL = [
    "Left-Hippocampus", "Right-Hippocampus",
    "Left-Amygdala", "Right-Amygdala",
    "Left-Caudate", "Right-Caudate",
    "Left-Putamen", "Right-Putamen",
    "Left-Thalamus", "Right-Thalamus",
    "Left-Lateral-Ventricle", "Right-Lateral-Ventricle",
]

# Key cortical regions (Desikan-Killiany atlas)
_KEY_CORTICAL = [
    "superiorfrontal", "middletemporal", "inferiorparietal",
    "entorhinal", "fusiform", "precuneus",
    "posteriorcingulate", "superiortemporal", "precentral",
    "postcentral", "supramarginal", "lateraloccipital",
]


def parse_aseg_stats(stats_path: Path) -> list[RegionMeasure]:
    """Parse FreeSurfer/FastSurfer aseg.stats file for subcortical volumes.

    The aseg.stats file has a header section (lines starting with #) followed
    by tab-separated data rows with columns:
    Index SegId NVoxels Volume_mm3 StructName ...

    Args:
        stats_path: Path to aseg.stats file.

    Returns:
        List of RegionMeasure for each subcortical structure.
    """
    if not stats_path.exists():
        logger.warning(f"aseg.stats not found: {stats_path}")
        return []

    regions = []
    for line in stats_path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 5:
            name = parts[4]
            volume = float(parts[3])
            regions.append(RegionMeasure(name=name, volume_mm3=volume))

    logger.info(f"Parsed {len(regions)} subcortical regions from aseg.stats")
    return regions


def parse_aparc_stats(stats_path: Path) -> list[RegionMeasure]:
    """Parse FreeSurfer/FastSurfer aparc.stats file for cortical measurements.

    The aparc.stats file contains cortical parcellation data with columns:
    StructName NumVert SurfArea GrayVol ThickAvg ThickStd MeanCurv ...

    Args:
        stats_path: Path to lh.aparc.stats or rh.aparc.stats file.

    Returns:
        List of RegionMeasure with volume, thickness, and area.
    """
    if not stats_path.exists():
        logger.warning(f"aparc.stats not found: {stats_path}")
        return []

    regions = []
    for line in stats_path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 5:
            name = parts[0]
            area = float(parts[2])
            volume = float(parts[3])
            thickness = float(parts[4])
            regions.append(RegionMeasure(
                name=name,
                volume_mm3=volume,
                thickness_mm=thickness,
                area_mm2=area,
            ))

    logger.info(f"Parsed {len(regions)} cortical regions from {stats_path.name}")
    return regions


def compute_from_mask(
    brain_mask_path: Path, subject_id: str
) -> MorphometryResult:
    """Compute basic morphometrics from brain mask when FastSurfer is unavailable.

    Only provides total brain volume — no regional parcellation.
    Used as fallback for dev/testing environments.

    Args:
        brain_mask_path: Path to binary brain mask NIfTI.
        subject_id: BIDS subject ID.

    Returns:
        MorphometryResult with total volume only.
    """
    img = nib.load(str(brain_mask_path))
    mask_data = np.asanyarray(img.dataobj)
    voxel_vol = float(np.prod(img.header.get_zooms()[:3]))
    brain_vol_mm3 = float(np.sum(mask_data > 0) * voxel_vol)
    brain_vol_cm3 = brain_vol_mm3 / 1000.0

    result = MorphometryResult(
        subject_id=subject_id,
        total_brain_volume_cm3=brain_vol_cm3,
        summary={
            "total_brain_volume_cm3": round(brain_vol_cm3, 1),
            "source": "mask_only",
        },
    )
    logger.info(f"[{subject_id}] Mask-based volume: {brain_vol_cm3:.1f} cm³")
    return result


def extract_morphometry(
    fastsurfer_dir: Path | None,
    brain_mask_path: Path | None,
    subject_id: str,
) -> MorphometryResult:
    """Extract morphometric measurements from FastSurfer outputs or mask.

    Tries FastSurfer stats files first. Falls back to mask-based volume
    if FastSurfer outputs are not available.

    Args:
        fastsurfer_dir: FastSurfer output directory for this subject
                        (e.g., processed/sub-01/fastsurfer/sub-01/).
        brain_mask_path: Path to brain mask NIfTI (fallback).
        subject_id: BIDS subject ID.

    Returns:
        MorphometryResult with all available measurements.
    """
    # Try FastSurfer stats
    if fastsurfer_dir and fastsurfer_dir.exists():
        stats_dir = fastsurfer_dir / "stats"
        aseg_path = stats_dir / "aseg.stats"
        lh_aparc = stats_dir / "lh.aparc.stats"
        rh_aparc = stats_dir / "rh.aparc.stats"

        if aseg_path.exists():
            logger.info(f"[{subject_id}] Parsing FastSurfer stats")
            subcortical = parse_aseg_stats(aseg_path)
            cortical_lh = parse_aparc_stats(lh_aparc)
            cortical_rh = parse_aparc_stats(rh_aparc)

            # Compute total brain volume from subcortical volumes
            total_vol = sum(r.volume_mm3 for r in subcortical)
            total_vol_cm3 = total_vol / 1000.0

            # Build summary with key clinical metrics
            summary = _build_summary(subcortical, cortical_lh, cortical_rh, total_vol_cm3)

            return MorphometryResult(
                subject_id=subject_id,
                total_brain_volume_cm3=total_vol_cm3,
                subcortical=subcortical,
                cortical_lh=cortical_lh,
                cortical_rh=cortical_rh,
                summary=summary,
            )

    # Fallback: mask-based
    if brain_mask_path and brain_mask_path.exists():
        return compute_from_mask(brain_mask_path, subject_id)

    logger.warning(f"[{subject_id}] No morphometry data available")
    return MorphometryResult(subject_id=subject_id)


def _build_summary(
    subcortical: list[RegionMeasure],
    cortical_lh: list[RegionMeasure],
    cortical_rh: list[RegionMeasure],
    total_vol_cm3: float,
) -> dict:
    """Build clinical summary from regional measurements.

    Extracts key biomarkers: hippocampal volume, ventricular volume,
    mean cortical thickness for key regions.
    """
    sub_map = {r.name: r for r in subcortical}
    summary: dict = {
        "total_brain_volume_cm3": round(total_vol_cm3, 1),
        "source": "fastsurfer",
    }

    # Hippocampal volumes (AD biomarker)
    lh = sub_map.get("Left-Hippocampus")
    rh = sub_map.get("Right-Hippocampus")
    if lh and rh:
        summary["hippocampus_total_mm3"] = round(lh.volume_mm3 + rh.volume_mm3, 0)
        summary["hippocampus_left_mm3"] = round(lh.volume_mm3, 0)
        summary["hippocampus_right_mm3"] = round(rh.volume_mm3, 0)

    # Ventricular volumes (hydrocephalus / atrophy indicator)
    lv_l = sub_map.get("Left-Lateral-Ventricle")
    lv_r = sub_map.get("Right-Lateral-Ventricle")
    if lv_l and lv_r:
        summary["ventricle_total_mm3"] = round(lv_l.volume_mm3 + lv_r.volume_mm3, 0)

    # Mean cortical thickness for key regions
    all_cortical = cortical_lh + cortical_rh
    key_regions = [r for r in all_cortical if r.name in _KEY_CORTICAL and r.thickness_mm]
    if key_regions:
        thicknesses = [r.thickness_mm for r in key_regions if r.thickness_mm is not None]
        summary["mean_cortical_thickness_mm"] = round(float(np.mean(thicknesses)), 3)

    # Per-region thickness for radar chart
    region_thickness = {}
    for r in cortical_lh:
        if r.name in _KEY_CORTICAL and r.thickness_mm is not None:
            region_thickness[f"lh_{r.name}"] = round(r.thickness_mm, 3)
    for r in cortical_rh:
        if r.name in _KEY_CORTICAL and r.thickness_mm is not None:
            region_thickness[f"rh_{r.name}"] = round(r.thickness_mm, 3)
    if region_thickness:
        summary["cortical_thickness_by_region"] = region_thickness

    # Per-region subcortical volumes for bar chart
    region_volumes = {}
    for name in _KEY_SUBCORTICAL:
        r = sub_map.get(name)
        if r:
            region_volumes[name] = round(r.volume_mm3, 0)
    if region_volumes:
        summary["subcortical_volumes"] = region_volumes

    return summary
