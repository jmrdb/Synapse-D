"""Subject identity verification for longitudinal analysis.

Verifies that a new MRI scan belongs to the same person as previous
scans before adding to longitudinal tracking. Prevents corrupted
trajectory data from mismatched subjects.

Method:
1. Rigid registration (6-DOF) to align new scan to reference — handles
   different head positioning/orientation in the scanner
2. NCC on aligned brain-masked voxels for identity scoring

Rigid registration corrects for:
- Head tilt (rotation around 3 axes)
- Head position shift (translation in 3 axes)
- Does NOT scale or deform — preserves brain shape for identity check

Thresholds (post-alignment):
- Same person, same session: NCC 0.97-0.99
- Same person, 1-5 year gap: NCC 0.92-0.97
- Different person:          NCC 0.70-0.88

References:
- Valizadeh et al., 2017: structural MRI individual identification 85-95%
"""

from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np
from loguru import logger

# NCC threshold for same-person determination (post-alignment)
IDENTITY_THRESHOLD = 0.90
IDENTITY_REJECT_THRESHOLD = 0.80


@dataclass
class IdentityCheckResult:
    """Result of identity verification between two scans.

    Attributes:
        is_same_subject: Whether scans are from the same person.
        ncc_score: Normalized cross-correlation score (0-1).
        confidence: Confidence level ('high', 'medium', 'low').
        message: Human-readable explanation.
        aligned: Whether rigid alignment was performed before comparison.
    """

    is_same_subject: bool
    ncc_score: float
    confidence: str
    message: str
    aligned: bool = False

    def to_dict(self) -> dict:
        return {
            "is_same_subject": self.is_same_subject,
            "ncc_score": round(self.ncc_score, 4),
            "confidence": self.confidence,
            "message": self.message,
            "aligned": self.aligned,
        }


def verify_identity(
    new_brain_path: Path,
    reference_brain_path: Path,
    subject_id: str = "",
) -> IdentityCheckResult:
    """Verify that two brain-extracted MRI scans are from the same person.

    First attempts rigid registration (6-DOF) to align scans, then
    computes NCC. This handles different head orientations between scans.
    Falls back to affine-header-based alignment if ANTs is unavailable.

    Args:
        new_brain_path: Path to the new brain-extracted NIfTI.
        reference_brain_path: Path to the previous brain-extracted NIfTI.
        subject_id: For logging.

    Returns:
        IdentityCheckResult with match decision, score, and explanation.
    """
    try:
        # Step 1: Align scans (rigid registration or header-based)
        new_data, ref_data, aligned = _align_and_load(
            new_brain_path, reference_brain_path, subject_id
        )

        # Step 2: Compute NCC on aligned brain voxels
        ncc = _normalized_cross_correlation(new_data, ref_data)

    except Exception as e:
        logger.error(f"[{subject_id}] Identity verification failed: {e}")
        return IdentityCheckResult(
            is_same_subject=False,  # Fail-closed: reject on error for data safety
            ncc_score=0.0,
            confidence="error",
            message=f"동일인 검증 실패: 기술적 오류 발생. 수동 확인이 필요합니다.",
            aligned=False,
        )

    # Step 3: Determine result
    return _classify_result(ncc, aligned, subject_id)


def _align_and_load(
    new_path: Path, ref_path: Path, subject_id: str
) -> tuple[np.ndarray, np.ndarray, bool]:
    """Align two brain volumes and return voxel data for comparison.

    Tries ANTs rigid registration first (handles arbitrary head positioning).
    Falls back to nibabel affine-based resampling if ANTs unavailable.

    Returns:
        Tuple of (new_data_1d, ref_data_1d, was_rigidly_aligned).
    """
    # Try ANTs rigid registration (6-DOF: 3 rotation + 3 translation)
    try:
        import ants

        ref_ants = ants.image_read(str(ref_path))
        new_ants = ants.image_read(str(new_path))

        # Rigid = rotation + translation only (no scaling/deformation)
        # This corrects for different head positioning in the scanner
        reg = ants.registration(
            fixed=ref_ants,
            moving=new_ants,
            type_of_transform="Rigid",
        )
        aligned_new = reg["warpedmovout"]

        new_data = aligned_new.numpy().flatten().astype(np.float32)
        ref_data = ref_ants.numpy().flatten().astype(np.float32)

        # Free ANTs objects immediately to reduce memory pressure
        del ref_ants, new_ants, reg, aligned_new

        # Validate ANTs output — registration can "succeed" but produce garbage
        if np.all(new_data == 0) or np.any(np.isnan(new_data)):
            logger.warning(f"[{subject_id}] ANTs produced invalid output, "
                           f"falling back to header-based alignment")
            return _header_based_align(new_path, ref_path, subject_id)

        logger.info(f"[{subject_id}] Identity check: ANTs rigid alignment applied")
        return new_data, ref_data, True

    except ImportError:
        logger.info(f"[{subject_id}] ANTs not available, using header-based alignment")
    except Exception as e:
        logger.warning(f"[{subject_id}] ANTs rigid registration failed: {e}, "
                       f"falling back to header-based alignment")

    # Fallback: Resample to common grid using NIfTI affine headers
    # This handles basic orientation differences (RAS/LAS/etc.) but
    # NOT arbitrary head tilts within the same orientation convention
    return _header_based_align(new_path, ref_path, subject_id)


def _header_based_align(
    new_path: Path, ref_path: Path, subject_id: str
) -> tuple[np.ndarray, np.ndarray, bool]:
    """Align using NIfTI affine headers — fallback when ANTs unavailable.

    Resamples the new image to the reference image's voxel grid using
    the affine transformations stored in NIfTI headers. This corrects
    for different voxel orderings (RAS vs LAS) and basic orientation,
    but does NOT correct for arbitrary head tilts.

    The NCC threshold should be interpreted more conservatively when
    only header-based alignment is used.
    """
    from nibabel.processing import resample_from_to

    ref_img = nib.load(str(ref_path))
    new_img = nib.load(str(new_path))

    # Resample new image to reference image's grid
    try:
        new_resampled = resample_from_to(new_img, ref_img, order=1)
        new_data = np.asanyarray(new_resampled.dataobj, dtype=np.float32).flatten()
        ref_data = np.asanyarray(ref_img.dataobj, dtype=np.float32).flatten()
        logger.info(f"[{subject_id}] Identity check: header-based resampling applied")
        return new_data, ref_data, False
    except Exception as e:
        # Resampling failed — cannot safely compare without alignment
        raise ValueError(
            f"Cannot align volumes for identity comparison: {e}. "
            f"Neither ANTs nor nibabel resampling succeeded."
        ) from e


def _classify_result(
    ncc: float, aligned: bool, subject_id: str
) -> IdentityCheckResult:
    """Classify identity check result based on NCC score.

    When only header-based alignment was used (not rigid registration),
    results are less reliable — reflected in confidence level.
    """
    alignment_note = "" if aligned else " (정밀 정합 미적용, 촬영 자세 차이로 점수가 낮을 수 있음)"

    if ncc >= IDENTITY_THRESHOLD:
        confidence = "high" if ncc >= 0.95 and aligned else "medium"
        result = IdentityCheckResult(
            is_same_subject=True,
            ncc_score=ncc,
            confidence=confidence,
            message=f"동일인 확인 (NCC={ncc:.3f}){alignment_note}",
            aligned=aligned,
        )
    elif ncc >= IDENTITY_REJECT_THRESHOLD:
        result = IdentityCheckResult(
            is_same_subject=True,
            ncc_score=ncc,
            confidence="low",
            message=f"동일인 가능성 있으나 확신 낮음 (NCC={ncc:.3f}). "
                    f"장기간 간격 또는 스캐너/자세 차이일 수 있습니다.{alignment_note}",
            aligned=aligned,
        )
    else:
        result = IdentityCheckResult(
            is_same_subject=False,
            ncc_score=ncc,
            confidence="high" if aligned else "medium",
            message=f"동일인이 아닌 것으로 판단됩니다 (NCC={ncc:.3f}).{alignment_note}",
            aligned=aligned,
        )

    logger.info(f"[{subject_id}] Identity: NCC={ncc:.3f}, "
                f"same={result.is_same_subject}, aligned={aligned}")
    return result


def find_reference_brain(subject_id: str) -> Path | None:
    """Find the most recent brain-extracted NIfTI for a subject.

    Args:
        subject_id: BIDS subject ID.

    Returns:
        Path to most recent brain NIfTI, or None if no previous scan exists.
    """
    from synapse_d.config import settings

    subject_dir = settings.output_dir / subject_id / "anat"
    if not subject_dir.exists():
        return None

    brain_files = sorted(
        subject_dir.glob("*_brain.nii.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return brain_files[0] if brain_files else None


def _normalized_cross_correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Compute NCC between two 1D arrays on non-zero (brain) voxels.

    NCC = mean((a - mean_a) * (b - mean_b)) / (std_a * std_b)
    Range: 0 to 1 (1 = identical).
    """
    mask = (a > 0) & (b > 0)
    overlap = int(mask.sum())
    total = max(len(a), len(b))
    if overlap < 1000 or (total > 0 and overlap / total < 0.1):
        logger.warning(f"Brain mask overlap too small: {overlap}/{total} "
                       f"({overlap/total:.1%})" if total > 0 else "Empty volumes")
        return 0.0

    a_m = a[mask]
    b_m = b[mask]

    a_mean, a_std = a_m.mean(), a_m.std()
    b_mean, b_std = b_m.mean(), b_m.std()

    if a_std < 1e-10 or b_std < 1e-10:
        return 0.0

    ncc = float(np.mean((a_m - a_mean) * (b_m - b_mean)) / (a_std * b_std))
    return float(np.clip(ncc, 0.0, 1.0))
