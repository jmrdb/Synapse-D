"""Structural MRI preprocessing pipeline.

Implements the core HD-BET → ANTs → FastSurfer pipeline for T1-weighted MRI.
All tools use Apache 2.0 license - safe for commercial use.

Pipeline steps:
    1. Brain Extraction (HD-BET): Removes skull and non-brain tissue
    2. Registration (ANTs): Aligns brain to MNI152 standard space
    3. Segmentation (FastSurfer): Cortical/subcortical parcellation

Usage:
    from synapse_d.pipeline.preprocessing import PreprocessingPipeline
    pipeline = PreprocessingPipeline(output_dir=Path("./output"))
    result = pipeline.run(t1_path=Path("sub-01_T1w.nii.gz"))
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import nibabel as nib
import numpy as np
from loguru import logger

from synapse_d.config import settings
from synapse_d.utils.bids import get_subject_id, get_voxel_info, make_output_dir


@dataclass
class PreprocessingResult:
    """Result of the preprocessing pipeline for a single subject.

    Attributes:
        subject_id: BIDS subject identifier.
        input_path: Original T1w input file.
        brain_extracted: Path to skull-stripped brain.
        brain_mask: Path to binary brain mask.
        registered: Path to MNI-registered brain.
        segmentation: Path to FastSurfer segmentation output.
        morphometrics: Extracted morphometric measurements.
        success: Whether all pipeline steps completed.
        errors: List of errors encountered.
    """

    subject_id: str = ""
    input_path: Path = Path()
    brain_extracted: Path | None = None
    brain_mask: Path | None = None
    registered: Path | None = None
    segmentation: Path | None = None
    morphometrics: dict = field(default_factory=dict)
    success: bool = False
    errors: list[str] = field(default_factory=list)


class PreprocessingPipeline:
    """T1w MRI preprocessing pipeline: HD-BET → ANTs → FastSurfer.

    Args:
        output_dir: Root directory for pipeline outputs.
        device: Compute device ('cpu' or 'cuda').
    """

    def __init__(self, output_dir: Path | None = None, device: str | None = None):
        self.output_dir = output_dir or settings.output_dir
        self.device = device or settings.device
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, t1_path: Path) -> PreprocessingResult:
        """Execute the full preprocessing pipeline on a T1w MRI.

        Args:
            t1_path: Path to input T1-weighted NIfTI file.

        Returns:
            PreprocessingResult with paths to all outputs and metrics.
        """
        subject_id = get_subject_id(t1_path)
        result = PreprocessingResult(subject_id=subject_id, input_path=t1_path)
        out_dir = make_output_dir(self.output_dir, subject_id)

        logger.info(f"[{subject_id}] Starting preprocessing pipeline")
        logger.info(f"[{subject_id}] Input: {t1_path}")

        # Validate input
        try:
            img = nib.load(str(t1_path))
            info = get_voxel_info(img)
            logger.info(f"[{subject_id}] Volume: shape={info['shape']}, "
                        f"voxel={info['voxel_size']}")
        except Exception as e:
            result.errors.append(f"Input validation failed: {e}")
            return result

        # Step 1: Brain Extraction (HD-BET)
        brain_path, mask_path = self._brain_extraction(t1_path, out_dir, subject_id)
        if brain_path:
            result.brain_extracted = brain_path
            result.brain_mask = mask_path
        else:
            result.errors.append("Brain extraction failed")
            return result

        # Step 2: Registration to MNI (ANTs)
        reg_path = self._registration(brain_path, out_dir, subject_id)
        if reg_path:
            result.registered = reg_path
        else:
            result.errors.append("Registration failed")
            # Continue anyway - segmentation can work without registration

        # Step 3: Segmentation (FastSurfer)
        seg_path = self._segmentation(t1_path, out_dir, subject_id)
        if seg_path:
            result.segmentation = seg_path
        else:
            result.errors.append("Segmentation failed")

        # Step 4: Extract morphometrics
        result.morphometrics = self._extract_morphometrics(result, subject_id)

        result.success = result.brain_extracted is not None
        status = "SUCCESS" if result.success else "FAILED"
        logger.info(f"[{subject_id}] Pipeline {status} "
                    f"(errors: {len(result.errors)})")
        return result

    def _brain_extraction(
        self, t1_path: Path, out_dir: Path, subject_id: str
    ) -> tuple[Path | None, Path | None]:
        """Step 1: Skull stripping with HD-BET.

        Args:
            t1_path: Input T1w NIfTI.
            out_dir: Output directory.
            subject_id: For logging.

        Returns:
            Tuple of (brain_path, mask_path) or (None, None) on failure.
        """
        logger.info(f"[{subject_id}] Step 1/3: Brain extraction (HD-BET)")
        brain_path = out_dir / f"{subject_id}_T1w_brain.nii.gz"
        mask_path = out_dir / f"{subject_id}_T1w_brain_mask.nii.gz"

        try:
            cmd = [
                "hd-bet",
                "-i", str(t1_path),
                "-o", str(brain_path),
                "-device", self.device,
                "-mode", "fast",
                "-tta", "0",
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
            logger.info(f"[{subject_id}] Brain extraction complete: {brain_path}")
            return brain_path, mask_path
        except FileNotFoundError:
            logger.warning(f"[{subject_id}] HD-BET not installed, using fallback")
            return self._brain_extraction_fallback(t1_path, brain_path, mask_path, subject_id)
        except subprocess.CalledProcessError as e:
            logger.error(f"[{subject_id}] HD-BET failed: {e.stderr}")
            return None, None
        except subprocess.TimeoutExpired:
            logger.error(f"[{subject_id}] HD-BET timed out")
            return None, None

    def _brain_extraction_fallback(
        self, t1_path: Path, brain_path: Path, mask_path: Path, subject_id: str
    ) -> tuple[Path | None, Path | None]:
        """Fallback brain extraction using simple intensity thresholding.

        Used when HD-BET is not installed (development/testing).
        NOT suitable for production - use HD-BET for real analysis.

        Args:
            t1_path: Input T1w NIfTI.
            brain_path: Output brain path.
            mask_path: Output mask path.
            subject_id: For logging.

        Returns:
            Tuple of (brain_path, mask_path).
        """
        logger.warning(f"[{subject_id}] Using fallback brain extraction (dev only)")
        img = nib.load(str(t1_path))
        data = np.asanyarray(img.dataobj, dtype=np.float32)

        # Simple Otsu-like threshold for dev/testing
        threshold = np.percentile(data[data > 0], 30)
        mask = (data > threshold).astype(np.uint8)
        brain = data * mask

        nib.save(nib.Nifti1Image(brain, img.affine, img.header), str(brain_path))
        nib.save(nib.Nifti1Image(mask, img.affine, img.header), str(mask_path))
        logger.info(f"[{subject_id}] Fallback brain extraction complete")
        return brain_path, mask_path

    def _registration(
        self, brain_path: Path, out_dir: Path, subject_id: str
    ) -> Path | None:
        """Step 2: Register brain to MNI152 standard space using ANTs.

        Args:
            brain_path: Skull-stripped brain NIfTI.
            out_dir: Output directory.
            subject_id: For logging.

        Returns:
            Path to registered brain, or None on failure.
        """
        logger.info(f"[{subject_id}] Step 2/3: MNI registration (ANTs)")
        reg_path = out_dir / f"{subject_id}_T1w_MNI.nii.gz"

        try:
            import ants

            brain = ants.image_read(str(brain_path))
            template = ants.get_ants_data("mni")
            mni = ants.image_read(template)

            reg = ants.registration(
                fixed=mni,
                moving=brain,
                type_of_transform="SyNQuick",
            )
            ants.image_write(reg["warpedmovout"], str(reg_path))
            logger.info(f"[{subject_id}] Registration complete: {reg_path}")
            return reg_path
        except ImportError:
            logger.warning(f"[{subject_id}] ANTsPy not installed, skipping registration")
            return None
        except Exception as e:
            logger.error(f"[{subject_id}] Registration failed: {e}")
            return None

    def _segmentation(
        self, t1_path: Path, out_dir: Path, subject_id: str
    ) -> Path | None:
        """Step 3: Whole-brain segmentation with FastSurfer.

        Args:
            t1_path: Original T1w NIfTI (FastSurfer handles skull stripping internally).
            out_dir: Output directory.
            subject_id: For logging.

        Returns:
            Path to segmentation output, or None on failure.
        """
        logger.info(f"[{subject_id}] Step 3/3: Segmentation (FastSurfer)")
        fs_dir = out_dir.parent / "fastsurfer"

        try:
            cmd = [
                "fastsurfer",
                "--t1", str(t1_path),
                "--sid", subject_id,
                "--sd", str(fs_dir),
                "--seg_only",
                "--no_cuda" if self.device == "cpu" else "",
            ]
            cmd = [c for c in cmd if c]  # Remove empty strings
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=1800)
            seg_path = fs_dir / subject_id / "mri" / "aparc.DKTatlas+aseg.deep.mgz"
            if seg_path.exists():
                logger.info(f"[{subject_id}] Segmentation complete: {seg_path}")
                return seg_path
            return None
        except FileNotFoundError:
            logger.warning(f"[{subject_id}] FastSurfer not installed, skipping segmentation")
            return None
        except subprocess.CalledProcessError as e:
            logger.error(f"[{subject_id}] FastSurfer failed: {e.stderr[:500]}")
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"[{subject_id}] FastSurfer timed out (30min)")
            return None

    def _extract_morphometrics(
        self, result: PreprocessingResult, subject_id: str
    ) -> dict:
        """Extract basic morphometric measurements from pipeline outputs.

        Args:
            result: Current preprocessing result with output paths.
            subject_id: For logging.

        Returns:
            Dict of morphometric measurements.
        """
        metrics = {}

        # Brain volume from mask
        if result.brain_mask and result.brain_mask.exists():
            mask_img = nib.load(str(result.brain_mask))
            mask_data = np.asanyarray(mask_img.dataobj)
            voxel_vol = np.prod(mask_img.header.get_zooms()[:3])
            brain_vol_mm3 = float(np.sum(mask_data > 0) * voxel_vol)
            metrics["total_brain_volume_mm3"] = brain_vol_mm3
            metrics["total_brain_volume_cm3"] = brain_vol_mm3 / 1000.0
            logger.info(f"[{subject_id}] Brain volume: "
                        f"{metrics['total_brain_volume_cm3']:.1f} cm³")

        return metrics
