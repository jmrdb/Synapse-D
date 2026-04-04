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
from synapse_d.utils.bids import get_subject_id, get_voxel_info, load_nifti, make_output_dir


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
    used_fallback: bool = False
    errors: list[str] = field(default_factory=list)


class PreprocessingPipeline:
    """T1w MRI preprocessing pipeline: HD-BET → ANTs → FastSurfer.

    Args:
        output_dir: Root directory for pipeline outputs.
        device: Compute device ('cpu' or 'cuda').
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        device: str | None = None,
        allow_fallback: bool | None = None,
    ):
        self.output_dir = output_dir or settings.output_dir
        self.device = device or settings.device
        # Fallback: allowed in dev (cpu), blocked in production (cuda)
        if allow_fallback is not None:
            self.allow_fallback = allow_fallback
        else:
            self.allow_fallback = self.device == "cpu"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _run_command(
        cmd: list[str], subject_id: str, tool_name: str, timeout: int = 600
    ) -> tuple[bool, str]:
        """Execute an external tool as subprocess with unified error handling.

        Args:
            cmd: Command and arguments.
            subject_id: For logging.
            tool_name: Human-readable tool name for error messages.
            timeout: Max seconds to wait.

        Returns:
            Tuple of (success, error_message). error_message contains
            "not found" if the tool is not installed.
        """
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
            return True, ""
        except FileNotFoundError:
            return False, f"{tool_name} not found"
        except subprocess.CalledProcessError as e:
            logger.error(f"[{subject_id}] {tool_name} failed: {e.stderr[:500]}")
            return False, e.stderr[:500]
        except subprocess.TimeoutExpired:
            logger.error(f"[{subject_id}] {tool_name} timed out ({timeout}s)")
            return False, "timeout"

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

        self._used_fallback = False
        logger.info(f"[{subject_id}] Starting preprocessing pipeline")
        logger.info(f"[{subject_id}] Input: {t1_path}")

        # Validate input
        try:
            img = load_nifti(t1_path)
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
            result.used_fallback = self._used_fallback
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

        # Step 4: Extract morphometrics (FastSurfer stats or mask-based fallback)
        from synapse_d.pipeline.morphometry import extract_morphometry

        fs_subject_dir = None
        if result.segmentation:
            # FastSurfer output: processed/sub-xx/fastsurfer/sub-xx/
            fs_subject_dir = result.segmentation.parent.parent

        morph = extract_morphometry(fs_subject_dir, result.brain_mask, subject_id)
        result.morphometrics = morph.summary

        # Minimum success condition: brain extraction must succeed.
        # Registration and segmentation failures are non-fatal —
        # Brain Age prediction only requires the extracted brain volume.
        result.success = result.brain_extracted is not None
        status = "SUCCESS" if result.success else "FAILED"
        if result.success and result.errors:
            status = "PARTIAL"
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

        cmd = [
            "hd-bet",
            "-i", str(t1_path),
            "-o", str(brain_path),
            "-device", self.device,
            "-mode", "fast",
            "-tta", "0",
        ]
        ok, err = self._run_command(cmd, subject_id, "HD-BET", timeout=600)
        if ok:
            return brain_path, mask_path
        if "not found" in err and self.allow_fallback:
            self._used_fallback = True
            return self._brain_extraction_fallback(t1_path, brain_path, mask_path, subject_id)
        if "not found" in err and not self.allow_fallback:
            logger.error(f"[{subject_id}] HD-BET not installed and fallback disabled")
        return None, None

    def _brain_extraction_fallback(
        self, t1_path: Path, brain_path: Path, mask_path: Path, subject_id: str
    ) -> tuple[Path | None, Path | None]:
        """Fallback brain extraction using simple intensity thresholding.

        DEV/TEST ONLY. Results are inaccurate (no proper skull stripping).
        The 'used_fallback' flag is set on the result so consumers know
        the brain extraction quality is degraded.

        Args:
            t1_path: Input T1w NIfTI.
            brain_path: Output brain path.
            mask_path: Output mask path.
            subject_id: For logging.

        Returns:
            Tuple of (brain_path, mask_path).
        """
        logger.warning(f"[{subject_id}] FALLBACK brain extraction — results are approximate (dev only)")
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

        cmd = [
            "fastsurfer",
            "--t1", str(t1_path),
            "--sid", subject_id,
            "--sd", str(fs_dir),
            "--seg_only",
        ]
        if self.device == "cpu":
            cmd.append("--no_cuda")

        ok, _ = self._run_command(cmd, subject_id, "FastSurfer", timeout=1800)
        if ok:
            seg_path = fs_dir / subject_id / "mri" / "aparc.DKTatlas+aseg.deep.mgz"
            if seg_path.exists():
                logger.info(f"[{subject_id}] Segmentation complete: {seg_path}")
                return seg_path
        return None

