"""BIDS (Brain Imaging Data Structure) utilities.

Handles BIDS-compliant file discovery, validation, and path generation
for the Synapse-D preprocessing pipeline.
"""

from pathlib import Path

import nibabel as nib


def find_t1w_files(bids_dir: Path) -> list[Path]:
    """Find all T1-weighted NIfTI files in a BIDS directory.

    Args:
        bids_dir: Root BIDS directory containing sub-*/anat/ structure.

    Returns:
        Sorted list of paths to T1w NIfTI files.
    """
    patterns = ["sub-*/anat/*_T1w.nii.gz", "sub-*/anat/*_T1w.nii"]
    files = []
    for pattern in patterns:
        files.extend(bids_dir.glob(pattern))
    return sorted(files)


def get_subject_id(nifti_path: Path) -> str:
    """Extract BIDS subject ID from a NIfTI file path.

    Args:
        nifti_path: Path like sub-01/anat/sub-01_T1w.nii.gz

    Returns:
        Subject ID string, e.g. 'sub-01'.
    """
    for part in nifti_path.parts:
        if part.startswith("sub-"):
            return part
    return nifti_path.stem.split("_")[0]


def make_output_dir(output_root: Path, subject_id: str) -> Path:
    """Create BIDS-like output directory for a subject.

    Args:
        output_root: Root output directory.
        subject_id: BIDS subject ID.

    Returns:
        Created directory path.
    """
    out = output_root / subject_id / "anat"
    out.mkdir(parents=True, exist_ok=True)
    return out


def load_nifti(path: Path) -> nib.Nifti1Image:
    """Load a NIfTI file and return the nibabel image object.

    Args:
        path: Path to .nii or .nii.gz file.

    Returns:
        Loaded NIfTI image.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"NIfTI file not found: {path}")
    return nib.load(str(path))


def get_voxel_info(img: nib.Nifti1Image) -> dict:
    """Extract basic voxel information from a NIfTI image.

    Args:
        img: Loaded nibabel NIfTI image.

    Returns:
        Dict with shape, voxel_size, and affine info.
    """
    return {
        "shape": img.shape,
        "voxel_size": tuple(img.header.get_zooms()[:3]),
        "dtype": str(img.get_data_dtype()),
    }
