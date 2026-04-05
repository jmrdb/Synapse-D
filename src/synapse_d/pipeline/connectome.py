"""Structural connectome generation from dMRI data.

Generates a brain connectivity matrix from diffusion MRI (dMRI) data,
representing the structural wiring between brain regions. The connectome
is the foundation for brain network simulation (TVB integration in Phase 3).

Pipeline:
    1. dMRI preprocessing (eddy correction, brain extraction)
    2. Tractography (fiber tracking)
    3. Parcellation-based connectivity matrix generation
    4. Network metrics computation

When dMRI processing tools (MRtrix3/dipy) are unavailable, generates
a synthetic connectome from morphometric data for development/demo.

Future: Connectome Mapper 3 (BSD-3) integration for production.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from loguru import logger

from synapse_d.config import settings

# Desikan-Killiany atlas regions (68 cortical + 14 subcortical = 82 ROIs)
_DK_REGIONS = [
    # Left hemisphere cortical (34)
    "lh-bankssts", "lh-caudalanteriorcingulate", "lh-caudalmiddlefrontal",
    "lh-cuneus", "lh-entorhinal", "lh-fusiform", "lh-inferiorparietal",
    "lh-inferiortemporal", "lh-isthmuscingulate", "lh-lateraloccipital",
    "lh-lateralorbitofrontal", "lh-lingual", "lh-medialorbitofrontal",
    "lh-middletemporal", "lh-parahippocampal", "lh-paracentral",
    "lh-parsopercularis", "lh-parsorbitalis", "lh-parstriangularis",
    "lh-pericalcarine", "lh-postcentral", "lh-posteriorcingulate",
    "lh-precentral", "lh-precuneus", "lh-rostralanteriorcingulate",
    "lh-rostralmiddlefrontal", "lh-superiorfrontal", "lh-superiorparietal",
    "lh-superiortemporal", "lh-supramarginal", "lh-frontalpole",
    "lh-temporalpole", "lh-transversetemporal", "lh-insula",
    # Right hemisphere cortical (34)
    "rh-bankssts", "rh-caudalanteriorcingulate", "rh-caudalmiddlefrontal",
    "rh-cuneus", "rh-entorhinal", "rh-fusiform", "rh-inferiorparietal",
    "rh-inferiortemporal", "rh-isthmuscingulate", "rh-lateraloccipital",
    "rh-lateralorbitofrontal", "rh-lingual", "rh-medialorbitofrontal",
    "rh-middletemporal", "rh-parahippocampal", "rh-paracentral",
    "rh-parsopercularis", "rh-parsorbitalis", "rh-parstriangularis",
    "rh-pericalcarine", "rh-postcentral", "rh-posteriorcingulate",
    "rh-precentral", "rh-precuneus", "rh-rostralanteriorcingulate",
    "rh-rostralmiddlefrontal", "rh-superiorfrontal", "rh-superiorparietal",
    "rh-superiortemporal", "rh-supramarginal", "rh-frontalpole",
    "rh-temporalpole", "rh-transversetemporal", "rh-insula",
    # Subcortical (14)
    "lh-thalamus", "lh-caudate", "lh-putamen", "lh-pallidum",
    "lh-hippocampus", "lh-amygdala", "lh-accumbens",
    "rh-thalamus", "rh-caudate", "rh-putamen", "rh-pallidum",
    "rh-hippocampus", "rh-amygdala", "rh-accumbens",
]

N_REGIONS = len(_DK_REGIONS)  # 82


@dataclass
class ConnectomeResult:
    """Structural connectome analysis result.

    Attributes:
        subject_id: BIDS subject ID.
        n_regions: Number of brain regions (ROIs).
        region_labels: List of region names.
        connectivity_matrix: N×N symmetric matrix of connection strengths.
        network_metrics: Global and nodal network metrics.
        method: How the connectome was generated.
        success: Whether generation completed.
    """

    subject_id: str = ""
    n_regions: int = N_REGIONS
    region_labels: list[str] = field(default_factory=lambda: list(_DK_REGIONS))
    connectivity_matrix: list[list[float]] = field(default_factory=list)
    network_metrics: dict = field(default_factory=dict)
    method: str = "unknown"
    success: bool = False

    def to_dict(self) -> dict:
        return {
            "subject_id": self.subject_id,
            "n_regions": self.n_regions,
            "region_labels": self.region_labels,
            "connectivity_matrix": self.connectivity_matrix,
            "network_metrics": self.network_metrics,
            "method": self.method,
            "success": self.success,
        }


def generate_connectome(
    dwi_path: Path | None = None,
    morphometrics: dict | None = None,
    subject_id: str = "",
) -> ConnectomeResult:
    """Generate structural connectome from dMRI or morphometric data.

    Tries dMRI tractography first. Falls back to morphometry-based
    synthetic connectome for development/demo.

    Args:
        dwi_path: Path to dMRI NIfTI file.
        morphometrics: Morphometric summary dict (for synthetic fallback).
        subject_id: BIDS subject ID.

    Returns:
        ConnectomeResult with connectivity matrix and network metrics.
    """
    result = ConnectomeResult(subject_id=subject_id)

    # Try dMRI-based tractography (requires dipy)
    if dwi_path and dwi_path.exists():
        try:
            matrix = _tractography_connectome(dwi_path, subject_id)
            result.connectivity_matrix = matrix.tolist()
            result.method = "tractography"
            result.success = True
            logger.info(f"[{subject_id}] Tractography connectome: {N_REGIONS}x{N_REGIONS}")
            result.network_metrics = _compute_network_metrics(matrix, subject_id)
            return result
        except ImportError as e:
            logger.error(f"[{subject_id}] dipy not installed — cannot run tractography: {e}")
        except Exception as e:
            logger.warning(f"[{subject_id}] Tractography failed: {e}", exc_info=True)

    # Fallback: synthetic connectome based on morphometrics
    matrix = _synthetic_connectome(morphometrics, subject_id)
    result.connectivity_matrix = matrix.tolist()
    result.method = "synthetic"
    result.success = True
    result.network_metrics = _compute_network_metrics(matrix, subject_id)
    logger.info(f"[{subject_id}] Synthetic connectome generated ({N_REGIONS}x{N_REGIONS})")
    return result


def _tractography_connectome(dwi_path: Path, subject_id: str) -> np.ndarray:
    """Generate structural connectome via dMRI tractography using dipy.

    Pipeline:
        1. Load dMRI + bvals/bvecs
        2. Fit diffusion tensor model (DTI)
        3. Compute fractional anisotropy (FA) for stopping criterion
        4. Deterministic fiber tracking (EuDX)
        5. Build connectivity matrix from streamline endpoints

    Uses a simplified parcellation (axial slabs) for the connectivity matrix
    since FreeSurfer parcellation requires T1 segmentation. Future: integrate
    with FastSurfer segmentation for anatomically precise connectome.

    Args:
        dwi_path: Path to dMRI NIfTI file (.nii.gz).
        subject_id: For logging.

    Returns:
        N_REGIONS x N_REGIONS symmetric connectivity matrix.
    """
    from dipy.core.gradients import gradient_table
    from dipy.io.gradients import read_bvals_bvecs
    from dipy.reconst.dti import TensorModel
    from dipy.tracking.stopping_criterion import ThresholdStoppingCriterion
    from dipy.tracking.local_tracking import LocalTracking
    from dipy.tracking.streamline import Streamlines
    from dipy.direction import peaks_from_model
    from dipy.reconst.shm import CsaOdfModel
    import nibabel as nib

    # Find bvals/bvecs (BIDS convention: same directory, same prefix)
    dwi_dir = dwi_path.parent
    stem = dwi_path.name.replace(".nii.gz", "").replace(".nii", "")
    # BIDS: .bval/.bvec, dcm2niix may use .bvals/.bvecs
    bval_path = dwi_dir / f"{stem}.bval"
    bvec_path = dwi_dir / f"{stem}.bvec"
    if not bval_path.exists():
        bval_path = dwi_dir / f"{stem}.bvals"
    if not bvec_path.exists():
        bvec_path = dwi_dir / f"{stem}.bvecs"

    if not bval_path.exists() or not bvec_path.exists():
        raise FileNotFoundError(
            f"bvals/bvecs not found in {dwi_dir} for {stem}"
        )

    logger.info(f"[{subject_id}] Loading dMRI: {dwi_path.name}")

    # Step 1: Load data
    img = nib.load(str(dwi_path))
    data = np.asarray(img.dataobj, dtype=np.float32)  # float32: ~4GB vs ~8GB
    affine = img.affine
    bvals, bvecs = read_bvals_bvecs(str(bval_path), str(bvec_path))
    gtab = gradient_table(bvals, bvecs=bvecs)

    logger.info(f"[{subject_id}] dMRI: shape={data.shape}, "
                f"b-values={np.unique(bvals.astype(int))}, "
                f"{len(bvals)} directions")

    # Step 2: Fit DTI model for FA map
    logger.info(f"[{subject_id}] Fitting DTI model...")
    tensor_model = TensorModel(gtab)
    tensor_fit = tensor_model.fit(data)
    fa = np.nan_to_num(tensor_fit.fa, nan=0.0, posinf=0.0, neginf=0.0)

    # Step 3: Create brain mask from FA
    mask = fa > 0.1

    # Step 4: Compute peaks for tracking (CSA-ODF model)
    logger.info(f"[{subject_id}] Computing fiber orientations...")
    from dipy.data import default_sphere
    csa_model = CsaOdfModel(gtab, sh_order_max=6)
    csa_peaks = peaks_from_model(
        csa_model, data, sphere=default_sphere,
        relative_peak_threshold=0.5,
        min_separation_angle=25,
        mask=mask,
    )

    # Save shape before freeing the 4D volume
    volume_shape = data.shape[:3]
    # Free 4D dMRI volume (~4GB) — no longer needed after peak extraction
    del data, tensor_model, tensor_fit, csa_model

    # Step 5: Deterministic tracking
    logger.info(f"[{subject_id}] Running fiber tracking...")
    stopping_criterion = ThresholdStoppingCriterion(fa, 0.15)

    # Seed from high-FA voxels
    from dipy.tracking.utils import seeds_from_mask
    seeds = seeds_from_mask(fa > 0.3, affine, density=1)
    logger.info(f"[{subject_id}] Seeds: {len(seeds)}")

    streamline_gen = LocalTracking(
        csa_peaks, stopping_criterion, seeds, affine,
        step_size=0.5, max_cross=1,
    )
    streamlines = Streamlines(streamline_gen)
    n_streamlines = len(streamlines)
    logger.info(f"[{subject_id}] Generated {n_streamlines} streamlines")

    if n_streamlines < 100:
        raise ValueError(f"Too few streamlines ({n_streamlines}) for connectome")

    # Step 6: Build connectivity matrix
    # Create a simplified parcellation by dividing the brain into N_REGIONS zones
    # based on spatial coordinates (since we don't have FreeSurfer parcellation)
    matrix = _streamlines_to_matrix(streamlines, volume_shape, affine)

    logger.info(f"[{subject_id}] Tractography connectome built: "
                f"{n_streamlines} streamlines → {N_REGIONS}x{N_REGIONS} matrix")
    return matrix


def _streamlines_to_matrix(
    streamlines, volume_shape: tuple, affine: np.ndarray
) -> np.ndarray:
    """Convert streamlines to a connectivity matrix.

    Divides the brain volume into N_REGIONS spatial zones and counts
    streamlines connecting each pair of zones. This is an approximation —
    production version should use FreeSurfer/FastSurfer parcellation.
    """
    from dipy.tracking.utils import connectivity_matrix

    # Create a simple spatial parcellation label volume
    # Divide into grid: ~4x5x4 = 80 zones ≈ N_REGIONS (82)
    nx, ny, nz = 4, 5, 4  # 80 zones (close to 82)
    label_vol = np.zeros(volume_shape[:3], dtype=np.int16)

    sx = volume_shape[0] // nx
    sy = volume_shape[1] // ny
    sz = volume_shape[2] // nz

    label = 1
    for ix in range(nx):
        for iy in range(ny):
            for iz in range(nz):
                # Last slab extends to volume boundary (no orphan voxels)
                x0 = ix * sx
                x1 = volume_shape[0] if ix == nx - 1 else (ix + 1) * sx
                y0 = iy * sy
                y1 = volume_shape[1] if iy == ny - 1 else (iy + 1) * sy
                z0 = iz * sz
                z1 = volume_shape[2] if iz == nz - 1 else (iz + 1) * sz
                label_vol[x0:x1, y0:y1, z0:z1] = label
                label += 1
                if label > N_REGIONS:
                    break
            if label > N_REGIONS:
                break
        if label > N_REGIONS:
            break

    # Compute connectivity matrix using dipy (returns scipy sparse matrix)
    matrix = connectivity_matrix(
        streamlines, affine, label_vol,
        return_mapping=False,
    )

    # Convert sparse to dense ndarray
    if hasattr(matrix, "toarray"):
        matrix = matrix.toarray()
    matrix = np.asarray(matrix, dtype=np.float64)

    # Remove label 0 (background) row and column
    if matrix.shape[0] > 1:
        matrix = matrix[1:, 1:]

    # Ensure correct size (may have fewer labels than N_REGIONS)
    actual_size = matrix.shape[0]
    if actual_size < N_REGIONS:
        padded = np.zeros((N_REGIONS, N_REGIONS), dtype=matrix.dtype)
        padded[:actual_size, :actual_size] = matrix
        matrix = padded
    elif actual_size > N_REGIONS:
        matrix = matrix[:N_REGIONS, :N_REGIONS]

    # Make symmetric and normalize
    matrix = (matrix + matrix.T) / 2
    np.fill_diagonal(matrix, 0)
    max_val = matrix.max()
    if max_val > 0:
        matrix = matrix / max_val

    return matrix.astype(np.float64)


def _synthetic_connectome(
    morphometrics: dict | None, subject_id: str
) -> np.ndarray:
    """Generate a biologically plausible synthetic connectome.

    Uses known properties of human brain connectivity:
    - Small-world architecture (high clustering, short path length)
    - Homotopic connections (L↔R homologues strongly connected)
    - Distance-dependent decay (nearby regions more connected)
    - Hub regions (precuneus, superior frontal, insula)

    If morphometrics are available, modulates connectivity strength
    by brain volume (atrophy reduces connectivity).
    """
    # Subject-specific deterministic seed (hashlib is consistent across runs,
    # unlike Python's hash() which is randomized per process)
    import hashlib
    seed = int(hashlib.md5(subject_id.encode()).hexdigest(), 16) % (2**31) if subject_id else 42
    rng = np.random.RandomState(seed)
    matrix = np.zeros((N_REGIONS, N_REGIONS), dtype=np.float64)

    for i in range(N_REGIONS):
        for j in range(i + 1, N_REGIONS):
            ri, rj = _DK_REGIONS[i], _DK_REGIONS[j]

            # Extract region base names (strip hemisphere prefix)
            ri_base = ri.split("-", 1)[1] if "-" in ri else ri
            rj_base = rj.split("-", 1)[1] if "-" in rj else rj
            ri_hemi = ri.split("-", 1)[0] if "-" in ri else ""
            rj_hemi = rj.split("-", 1)[0] if "-" in rj else ""

            # Base connection probability
            prob = 0.15

            # Homotopic boost: L↔R homologues are strongly connected
            if ri_base == rj_base and ri_hemi != rj_hemi:
                prob = 0.9

            # Same hemisphere boost
            elif ri_hemi == rj_hemi:
                prob = 0.25

            # Hub regions boost
            hubs = {"precuneus", "superiorfrontal", "insula", "posteriorcingulate"}
            if ri_base in hubs or rj_base in hubs:
                prob = min(prob * 1.5, 0.95)

            # Generate connection
            if rng.random() < prob:
                strength = rng.exponential(0.3) + 0.1
                # Homotopic connections are stronger
                if ri_base == rj_base and ri_hemi != rj_hemi:
                    strength *= 2.0
                matrix[i, j] = strength
                matrix[j, i] = strength

    # Modulate by brain volume if available (atrophy = weaker connections)
    if morphometrics:
        vol = morphometrics.get("total_brain_volume_cm3", 1200)
        # Scale factor: 1.0 at 1200 cm³, reduced with atrophy
        scale = min(vol / 1200.0, 1.2)
        matrix *= scale

    # Normalize to 0-1 range
    max_val = matrix.max()
    if max_val > 0:
        matrix /= max_val

    return matrix


def _compute_network_metrics(matrix: np.ndarray, subject_id: str) -> dict:
    """Compute network metrics from connectivity matrix.

    Implemented metrics:
    - Node degree (mean)
    - Density (proportion of possible edges)
    - Clustering coefficient (segregation, vectorized A^3 method)
    - Hub nodes (top 5 by degree centrality)

    Future: global efficiency, small-worldness index
    """
    # Binary adjacency (threshold at 0.1)
    threshold = 0.1
    adj = (matrix > threshold).astype(int)
    n = adj.shape[0]

    # Node degree
    degrees = adj.sum(axis=1)
    mean_degree = float(degrees.mean())

    # Density
    n_edges = int(adj.sum()) // 2
    max_edges = n * (n - 1) // 2
    density = n_edges / max_edges if max_edges > 0 else 0.0

    # Clustering coefficient — vectorized via matrix multiplication
    A = adj.astype(np.float64)
    triangles_per_node = np.diag(A @ A @ A) / 2
    possible_per_node = degrees * (degrees - 1) / 2
    clustering = np.divide(
        triangles_per_node, possible_per_node,
        out=np.zeros(n, dtype=np.float64),
        where=possible_per_node > 0,
    )
    mean_clustering = float(clustering.mean())

    # Hub nodes (top 5 by degree)
    top_indices = np.argsort(degrees)[-5:][::-1]
    hubs = [
        {
            "region": _DK_REGIONS[i] if i < len(_DK_REGIONS) else f"region_{i}",
            "degree": int(degrees[i]),
        }
        for i in top_indices
    ]

    metrics = {
        "n_nodes": n,
        "n_edges": n_edges,
        "density": round(density, 4),
        "mean_degree": round(mean_degree, 2),
        "mean_clustering_coefficient": round(mean_clustering, 4),
        "hub_nodes": hubs,
    }

    logger.info(f"[{subject_id}] Network: {n_edges} edges, "
                f"density={density:.3f}, clustering={mean_clustering:.3f}")
    return metrics
