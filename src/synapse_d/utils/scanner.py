"""MRI scanner metadata extraction.

Extracts scanner manufacturer, model, and field strength from:
1. BIDS JSON sidecar files (preferred — standardized metadata)
2. NIfTI header description field (fallback — limited info)

Scanner metadata is essential for:
- Statistical harmonization (neuroHarmonize/ComBat, Phase 2)
- Quality control and reproducibility tracking
- Identifying scanner-driven measurement bias (11-19% for volumes)

Reference: Bosco et al., 2023 (PMID: 37126963)
"""

import json
from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
from loguru import logger


@dataclass
class ScannerInfo:
    """MRI scanner metadata.

    Attributes:
        manufacturer: Scanner manufacturer (e.g., 'Siemens', 'GE', 'Philips').
        model: Scanner model name (e.g., 'Prisma', 'Discovery MR750').
        field_strength_t: Magnetic field strength in Tesla (e.g., 1.5, 3.0).
        sequence: Acquisition sequence (e.g., 'MPRAGE', 'SPGR').
        site_id: Acquisition site identifier (for multi-site harmonization).
        source: Where the metadata was extracted from.
    """

    manufacturer: str = "unknown"
    model: str = "unknown"
    field_strength_t: float = 0.0
    sequence: str = "unknown"
    site_id: str = "unknown"
    source: str = "none"

    def to_dict(self) -> dict:
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "field_strength_t": self.field_strength_t,
            "sequence": self.sequence,
            "site_id": self.site_id,
            "source": self.source,
        }


def extract_scanner_info(nifti_path: Path) -> ScannerInfo:
    """Extract scanner metadata from BIDS sidecar JSON or NIfTI header.

    Looks for a JSON sidecar file with the same name as the NIfTI
    (BIDS convention), then falls back to NIfTI header fields.

    Args:
        nifti_path: Path to .nii or .nii.gz file.

    Returns:
        ScannerInfo with available metadata.
    """
    info = ScannerInfo()

    # Try BIDS JSON sidecar first (most reliable)
    json_path = _find_bids_sidecar(nifti_path)
    if json_path:
        info = _parse_bids_json(json_path)
        if info.manufacturer != "unknown":
            return info

    # Fallback: NIfTI header
    info = _parse_nifti_header(nifti_path)
    return info


def _find_bids_sidecar(nifti_path: Path) -> Path | None:
    """Find BIDS JSON sidecar for a NIfTI file.

    BIDS convention: sub-01_T1w.nii.gz → sub-01_T1w.json
    """
    stem = nifti_path.name
    for suffix in [".nii.gz", ".nii"]:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    json_path = nifti_path.parent / f"{stem}.json"
    return json_path if json_path.exists() else None


def _parse_bids_json(json_path: Path) -> ScannerInfo:
    """Parse BIDS JSON sidecar for scanner metadata.

    BIDS standard fields:
    - Manufacturer: "Siemens", "GE", "Philips"
    - ManufacturersModelName: "Prisma", "Discovery MR750"
    - MagneticFieldStrength: 3.0
    - PulseSequenceType / SequenceName: "MPRAGE"
    - InstitutionName: site identifier
    """
    try:
        data = json.loads(json_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to parse BIDS JSON {json_path}: {e}")
        return ScannerInfo()

    def _safe_float(val: object, default: float = 0.0) -> float:
        try:
            return float(val)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    info = ScannerInfo(
        manufacturer=_normalize_manufacturer(data.get("Manufacturer", "unknown")),
        model=data.get("ManufacturersModelName", "unknown"),
        field_strength_t=_safe_float(data.get("MagneticFieldStrength", 0)),
        sequence=data.get("PulseSequenceType",
                         data.get("SequenceName",
                         data.get("ScanningSequence", "unknown"))),
        site_id=data.get("InstitutionName",
                        data.get("InstitutionAddress", "unknown")),
        source="bids_json",
    )
    logger.info(f"Scanner: {info.manufacturer} {info.model} "
                f"{info.field_strength_t}T [{info.source}]")
    return info


def _parse_nifti_header(nifti_path: Path) -> ScannerInfo:
    """Extract limited scanner info from NIfTI header description field.

    NIfTI headers have a 80-char 'descrip' field that sometimes contains
    scanner info. This is unreliable but better than nothing.
    """
    try:
        img = nib.load(str(nifti_path))
        header = img.header
        raw = header.get("descrip", b"") if hasattr(header, "get") else b""
        descrip = raw.decode("utf-8", errors="replace").strip() if isinstance(raw, bytes) else str(raw).strip()
    except Exception:
        return ScannerInfo(source="none")

    info = ScannerInfo(source="nifti_header")

    # Try to detect manufacturer from description
    descrip_lower = descrip.lower()
    if "siemens" in descrip_lower:
        info.manufacturer = "Siemens"
    elif "ge " in descrip_lower or "general electric" in descrip_lower:
        info.manufacturer = "GE"
    elif "philips" in descrip_lower:
        info.manufacturer = "Philips"

    # Try to detect field strength
    for token in descrip.split():
        if token.endswith("T") and token[:-1].replace(".", "").isdigit():
            info.field_strength_t = float(token[:-1])
            break

    if info.manufacturer != "unknown":
        logger.info(f"Scanner (from NIfTI header): {info.manufacturer} "
                    f"{info.field_strength_t}T")
    else:
        logger.info("Scanner metadata not available in NIfTI header")

    return info


def _normalize_manufacturer(raw: str) -> str:
    """Normalize manufacturer name to standard form.

    Different DICOM encodings may use variations like
    'SIEMENS', 'Siemens', 'SIEMENS HEALTHINEERS', etc.
    """
    raw_lower = raw.lower().strip()
    if "siemens" in raw_lower:
        return "Siemens"
    if raw_lower in ("ge", "ge medical systems", "ge healthcare") or "general electric" in raw_lower:
        return "GE"
    if "philips" in raw_lower:
        return "Philips"
    if "canon" in raw_lower or "toshiba" in raw_lower:
        return "Canon"
    if "hitachi" in raw_lower:
        return "Hitachi"
    if "bruker" in raw_lower:
        return "Bruker"
    return raw if raw else "unknown"
