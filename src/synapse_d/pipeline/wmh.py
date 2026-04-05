"""White Matter Hyperintensity (WMH) segmentation pipeline.

Detects and quantifies white matter hyperintensities from T2/FLAIR MRI,
a key biomarker for cerebral small vessel disease and vascular dementia risk.

Pipeline:
    1. Brain Extraction (HD-BET) on FLAIR
    2. WMH Segmentation (nnU-Net or threshold-based fallback)
    3. Quantification: total volume, Fazekas grade, regional distribution

WMH burden correlates with:
- Cognitive decline risk
- Vascular dementia progression
- Stroke risk
- Age-related brain changes

Note: T2/FLAIR measures WMH volume only — cortical thickness is NOT
measured from FLAIR (T1 only, per platform design).
"""

from dataclasses import dataclass, field
from pathlib import Path

import nibabel as nib
import numpy as np
from loguru import logger

from synapse_d.config import settings


@dataclass
class WMHResult:
    """WMH segmentation and quantification result.

    Attributes:
        subject_id: BIDS subject ID.
        wmh_volume_mm3: Total WMH volume in mm³.
        wmh_volume_ml: Total WMH volume in mL (= cm³).
        wmh_count: Number of discrete WMH lesions.
        fazekas_grade: Estimated Fazekas scale grade (0-3).
        fazekas_description: Human-readable Fazekas interpretation.
        regional_distribution: WMH volume by brain region (periventricular, deep, etc.).
        segmentation_path: Path to WMH segmentation mask NIfTI.
        success: Whether segmentation completed.
        used_fallback: Whether threshold-based fallback was used.
        errors: List of errors/warnings.
    """

    subject_id: str = ""
    wmh_volume_mm3: float = 0.0
    wmh_volume_ml: float = 0.0
    wmh_count: int = 0
    fazekas_grade: int = 0
    fazekas_description: str = ""
    regional_distribution: dict = field(default_factory=dict)
    segmentation_path: Path | None = None
    success: bool = False
    used_fallback: bool = False
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "wmh_volume_mm3": round(self.wmh_volume_mm3, 1),
            "wmh_volume_ml": round(self.wmh_volume_ml, 2),
            "wmh_count": self.wmh_count,
            "fazekas_grade": self.fazekas_grade,
            "fazekas_description": self.fazekas_description,
            "regional_distribution": self.regional_distribution,
            "segmentation_path": str(self.segmentation_path) if self.segmentation_path else None,
            "success": self.success,
            "used_fallback": self.used_fallback,
            "errors": self.errors,
        }


# Fazekas scale thresholds (WMH volume in mL)
# Source: Defined per clinical convention + Griffanti et al., NeuroImage 2016
_FAZEKAS_THRESHOLDS = [
    (0, 0.5, 0, "Grade 0: No WMH or minimal punctate"),
    (0.5, 5.0, 1, "Grade 1: Punctate foci"),
    (5.0, 25.0, 2, "Grade 2: Beginning confluence"),
    (25.0, float("inf"), 3, "Grade 3: Large confluent areas"),
]


def segment_wmh(
    flair_path: Path,
    output_dir: Path | None = None,
    device: str | None = None,
) -> WMHResult:
    """Segment white matter hyperintensities from FLAIR MRI.

    Args:
        flair_path: Path to T2-FLAIR NIfTI file.
        output_dir: Output directory (default: settings.output_dir).
        device: Compute device ('cpu' or 'cuda').

    Returns:
        WMHResult with volume, Fazekas grade, and regional distribution.
    """
    from synapse_d.utils.bids import get_subject_id, make_output_dir

    output_dir = output_dir or settings.output_dir
    device = device or settings.device
    subject_id = get_subject_id(flair_path)
    out_dir = make_output_dir(output_dir, subject_id)
    result = WMHResult(subject_id=subject_id)

    logger.info(f"[{subject_id}] Starting WMH segmentation pipeline")

    # Validate input
    try:
        img = nib.load(str(flair_path))
        shape = img.shape[:3]
        voxel_size = img.header.get_zooms()[:3]
        logger.info(f"[{subject_id}] FLAIR: shape={shape}, voxel={voxel_size}")
    except Exception as e:
        result.errors.append(f"FLAIR validation failed: {e}")
        return result

    # Step 1: Brain extraction on FLAIR
    brain_path = out_dir / f"{subject_id}_FLAIR_brain.nii.gz"
    mask_path = out_dir / f"{subject_id}_FLAIR_brain_mask.nii.gz"
    brain_path, mask_path = _extract_brain_flair(
        flair_path, brain_path, mask_path, device, subject_id
    )
    if not brain_path:
        result.errors.append("FLAIR brain extraction failed")
        return result

    # Step 2: WMH segmentation
    wmh_mask_path = out_dir / f"{subject_id}_WMH_mask.nii.gz"
    wmh_mask_path, used_fallback = _segment_wmh(
        brain_path, wmh_mask_path, device, subject_id
    )
    if not wmh_mask_path:
        result.errors.append("WMH segmentation failed")
        return result

    result.segmentation_path = wmh_mask_path
    result.used_fallback = used_fallback

    # Step 3: Quantification
    _quantify_wmh(result, wmh_mask_path, mask_path, img, subject_id)

    result.success = True
    logger.info(f"[{subject_id}] WMH: {result.wmh_volume_ml:.1f} mL, "
                f"Fazekas {result.fazekas_grade}, {result.wmh_count} lesions")
    return result


def _extract_brain_flair(
    flair_path: Path, brain_path: Path, mask_path: Path,
    device: str, subject_id: str,
) -> tuple[Path | None, Path | None]:
    """Brain extraction on FLAIR image."""
    import subprocess

    logger.info(f"[{subject_id}] WMH Step 1/3: FLAIR brain extraction")
    try:
        cmd = [
            "hd-bet", "-i", str(flair_path), "-o", str(brain_path),
            "-device", device, "-mode", "fast", "-tta", "0",
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        return brain_path, mask_path
    except FileNotFoundError:
        # Fallback: intensity thresholding (dev only)
        logger.warning(f"[{subject_id}] HD-BET not installed, using FLAIR fallback")
        img = nib.load(str(flair_path))
        data = np.asanyarray(img.dataobj, dtype=np.float32)
        threshold = np.percentile(data[data > 0], 25)
        mask = (data > threshold).astype(np.uint8)
        brain = data * mask
        nib.save(nib.Nifti1Image(brain, img.affine, img.header), str(brain_path))
        nib.save(nib.Nifti1Image(mask, img.affine, img.header), str(mask_path))
        return brain_path, mask_path
    except Exception as e:
        logger.error(f"[{subject_id}] FLAIR brain extraction failed: {e}")
        return None, None


def _segment_wmh(
    brain_path: Path, wmh_mask_path: Path,
    device: str, subject_id: str,
) -> tuple[Path | None, bool]:
    """Segment WMH using nnU-Net or intensity-based fallback.

    Returns:
        Tuple of (wmh_mask_path, used_fallback).
    """
    import subprocess

    logger.info(f"[{subject_id}] WMH Step 2/3: WMH segmentation")

    # Try nnU-Net first
    try:
        cmd = [
            "nnUNetv2_predict",
            "-i", str(brain_path.parent),
            "-o", str(wmh_mask_path.parent),
            "-d", "Dataset_WMH",
            "-c", "3d_fullres",
            "--device", device,
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=1800)
        if wmh_mask_path.exists():
            logger.info(f"[{subject_id}] nnU-Net WMH segmentation complete")
            return wmh_mask_path, False
    except FileNotFoundError:
        logger.warning(f"[{subject_id}] nnU-Net not installed, using threshold fallback")
    except Exception as e:
        logger.warning(f"[{subject_id}] nnU-Net failed ({e}), using threshold fallback")

    # Fallback: intensity-based WMH detection
    # WMH appears as hyperintense on FLAIR — simple but effective for large lesions
    return _wmh_threshold_fallback(brain_path, wmh_mask_path, subject_id)


def _wmh_threshold_fallback(
    brain_path: Path, wmh_mask_path: Path, subject_id: str
) -> tuple[Path | None, bool]:
    """Threshold-based WMH detection from FLAIR.

    WMH are hyperintense on FLAIR. We use mean + 2.5*std of brain
    intensity as threshold. This catches large WMH but misses
    subtle/small lesions. Results flagged as approximate.

    DEV/TEST ONLY — nnU-Net should be used in production.
    """
    try:
        img = nib.load(str(brain_path))
        data = np.asanyarray(img.dataobj, dtype=np.float32)

        # Compute threshold: mean + 2.5*std of non-zero voxels
        brain_voxels = data[data > 0]
        if len(brain_voxels) < 1000:
            return None, True

        threshold = brain_voxels.mean() + 2.5 * brain_voxels.std()
        wmh_mask = (data > threshold).astype(np.uint8)

        nib.save(nib.Nifti1Image(wmh_mask, img.affine, img.header), str(wmh_mask_path))
        logger.warning(f"[{subject_id}] FALLBACK WMH segmentation — approximate results")
        return wmh_mask_path, True
    except Exception as e:
        logger.error(f"[{subject_id}] WMH threshold fallback failed: {e}")
        return None, True


def _quantify_wmh(
    result: WMHResult, wmh_mask_path: Path, brain_mask_path: Path | None,
    original_img: nib.Nifti1Image, subject_id: str,
) -> None:
    """Quantify WMH: volume, lesion count, Fazekas grade, regional distribution."""
    wmh_img = nib.load(str(wmh_mask_path))
    wmh_data = np.asanyarray(wmh_img.dataobj)
    voxel_vol = float(np.prod(wmh_img.header.get_zooms()[:3]))

    # Total volume
    wmh_voxels = np.sum(wmh_data > 0)
    result.wmh_volume_mm3 = float(wmh_voxels * voxel_vol)
    result.wmh_volume_ml = result.wmh_volume_mm3 / 1000.0

    # Lesion count (connected components)
    try:
        from scipy.ndimage import label
        labeled, n_lesions = label(wmh_data > 0)
        result.wmh_count = int(n_lesions)
    except ImportError:
        result.wmh_count = 1 if wmh_voxels > 0 else 0

    # Fazekas grade estimation based on total volume
    for low, high, grade, desc in _FAZEKAS_THRESHOLDS:
        if low <= result.wmh_volume_ml < high:
            result.fazekas_grade = grade
            result.fazekas_description = desc
            break

    # Regional distribution (axial thirds as approximation)
    # Bottom third = infratentorial, middle = periventricular, top = juxtacortical
    if wmh_data.ndim == 3:
        z_size = wmh_data.shape[2]
        third = z_size // 3
        regions = {
            "infratentorial": float(np.sum(wmh_data[:, :, :third] > 0) * voxel_vol / 1000),
            "periventricular": float(np.sum(wmh_data[:, :, third:2*third] > 0) * voxel_vol / 1000),
            "juxtacortical": float(np.sum(wmh_data[:, :, 2*third:] > 0) * voxel_vol / 1000),
        }
        result.regional_distribution = {k: round(v, 2) for k, v in regions.items()}

    logger.info(f"[{subject_id}] WMH quantified: {result.wmh_volume_ml:.1f} mL, "
                f"{result.wmh_count} lesions, Fazekas {result.fazekas_grade}")
