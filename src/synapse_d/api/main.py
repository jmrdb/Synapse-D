"""Synapse-D API Server.

FastAPI application providing REST endpoints for MRI upload,
preprocessing pipeline execution, and Brain Age prediction.

Job state is managed via Celery's Redis result backend instead of
in-memory dicts, so state survives API server restarts.
"""

import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from synapse_d import __version__
from synapse_d.config import settings

# Upload size limit: 2GB (T1w MRI typically 10-200MB)
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024

# Subject ID format: sub- followed by exactly 8 hex chars
_SUBJECT_ID_RE = re.compile(r"^sub-[a-f0-9]{8}$")

app = FastAPI(
    title="Synapse-D Brain Digital Twin API",
    description="Structural MRI-based brain development and degeneration prediction",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve processed NIfTI files for Niivue frontend rendering
# WARNING: No authentication — any user can access any subject's files via /files/
# This is acceptable for local demo/RUO use. Production SaaS deployment MUST add
# per-subject authentication middleware before this mount.
settings.output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(settings.output_dir)), name="files")


def _validate_subject_id(subject_id: str) -> str:
    """Validate subject_id format to prevent path traversal attacks.

    Args:
        subject_id: Must match 'sub-[a-f0-9]{8}'.

    Raises:
        HTTPException: 400 if format is invalid.
    """
    if not _SUBJECT_ID_RE.match(subject_id):
        raise HTTPException(status_code=400, detail="Invalid subject_id format")
    return subject_id


def _run_sync(
    t1_path: Path | None,
    chronological_age: float | None,
    sex: str | None = None,
    flair_path: Path | None = None,
    swi_path: Path | None = None,
) -> dict:
    """Execute pipeline synchronously and return unified response.

    Used for sync=True requests and Celery fallback.
    """
    from synapse_d.api.tasks import run_pipeline

    result = run_pipeline(t1_path, chronological_age, sex, flair_path, swi_path)
    return {
        "job_id": uuid.uuid4().hex[:12],
        "status": "completed",
        "result": _sanitize_result(result),
    }


def _sanitize_result(result: dict) -> dict:
    """Remove server-internal paths from pipeline results.

    Converts absolute paths to relative URLs for frontend consumption.
    """
    preproc = result.get("preprocessing", {})
    output_dir_str = str(settings.output_dir)

    for key in ("brain_extracted", "registered", "segmentation"):
        path_str = preproc.get(key)
        if path_str and output_dir_str in path_str:
            # Convert "/app/data/processed/sub-xx/anat/file.nii.gz"
            # to "/files/sub-xx/anat/file.nii.gz"
            relative = path_str.split(output_dir_str)[-1].lstrip("/")
            preproc[f"{key}_url"] = f"/files/{relative}"
        preproc.pop(key, None)  # Remove absolute path

    result["preprocessing"] = preproc

    # Sanitize paths in WMH and microbleeds results
    for section in ("wmh", "microbleeds"):
        data = result.get(section, {})
        if isinstance(data, dict) and "segmentation_path" in data:
            seg_path = data["segmentation_path"]
            if seg_path and output_dir_str in str(seg_path):
                relative = str(seg_path).split(output_dir_str)[-1].lstrip("/")
                data["segmentation_url"] = f"/files/{relative}"
            data.pop("segmentation_path", None)

    return result


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


@app.post("/api/v1/upload")
async def upload_mri(
    file: UploadFile = File(...),
    modality: str = "T1w",
    subject_id: str | None = None,
):
    """Upload an MRI NIfTI file.

    Supports multiple modalities: T1w, T2w, FLAIR, SWI, DWI, dMRI.
    To add another modality to an existing subject, pass the subject_id.

    Args:
        file: NIfTI file (.nii or .nii.gz, max 2GB).
        modality: MRI modality (default: T1w).
            - T1w: structural (cortical thickness, Brain Age)
            - FLAIR: white matter lesions (WMH)
            - SWI: microbleeds (CMB)
            - DWI: clinical stroke detection (1-3 directions)
            - dMRI: research tractography (30+ directions, requires bvals/bvecs)
        subject_id: Existing subject ID to add modality to. If omitted, creates new.
    """
    if not file.filename or not (
        file.filename.endswith(".nii") or file.filename.endswith(".nii.gz")
    ):
        raise HTTPException(status_code=400, detail="Only .nii or .nii.gz files accepted")

    # Validate and normalize modality
    valid_modalities = {"T1w", "T2w", "FLAIR", "DWI", "dMRI", "SWI"}
    mod = modality.upper().replace("-", "").replace("_", "")
    _modality_map = {
        "T1": "T1w", "T1W": "T1w", "T1WEIGHTED": "T1w",
        "T2": "T2w", "T2W": "T2w", "T2WEIGHTED": "T2w",
        "FLAIR": "FLAIR", "T2FLAIR": "FLAIR",
        "DWI": "DWI",                          # Clinical DWI (stroke, 1-3 dir)
        "DMRI": "dMRI", "DTI": "dMRI",         # Research dMRI (tractography, 30+ dir)
        "HARDI": "dMRI", "DIFFUSION": "dMRI",
        "SWI": "SWI", "SUSCEPTIBILITY": "SWI",
    }
    modality = _modality_map.get(mod, modality)
    if modality not in valid_modalities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid modality '{modality}'. Supported: {', '.join(valid_modalities)}",
        )

    # Check Content-Length header first to reject oversized uploads early
    if file.size and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 2GB)")

    # Read with size tracking to prevent memory exhaustion
    chunks = []
    total = 0
    while chunk := await file.read(8 * 1024 * 1024):  # 8MB chunks
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 2GB)")
        chunks.append(chunk)
    content = b"".join(chunks)

    # Create or reuse subject
    if subject_id:
        _validate_subject_id(subject_id)
    else:
        subject_id = f"sub-{uuid.uuid4().hex[:8]}"

    subject_dir = settings.upload_dir / subject_id / "anat"
    subject_dir.mkdir(parents=True, exist_ok=True)

    suffix = ".nii.gz" if file.filename.endswith(".nii.gz") else ".nii"
    save_path = subject_dir / f"{subject_id}_{modality}{suffix}"
    save_path.write_bytes(content)

    return {
        "subject_id": subject_id,
        "modality": modality,
        "filename": file.filename,
        "size_mb": round(len(content) / 1024 / 1024, 2),
    }


@app.post("/api/v1/analyze/{subject_id}")
async def start_analysis(
    subject_id: str,
    chronological_age: float | None = None,
    sex: str | None = None,
    sync: bool = False,
):
    """Start preprocessing + Brain Age analysis for an uploaded MRI.

    By default dispatches to Celery worker (async). If Redis/Celery is
    unavailable or sync=True, falls back to synchronous execution.

    Args:
        subject_id: Subject ID from upload.
        chronological_age: Actual age for Brain Age Gap and normative comparison.
        sex: Biological sex ('M' or 'F') for sex-specific normative comparison.
        sync: Force synchronous execution.
    """
    _validate_subject_id(subject_id)
    if sex is not None and sex.upper() not in ("M", "F"):
        raise HTTPException(status_code=400, detail="sex must be 'M' or 'F'")
    if sex:
        sex = sex.upper()

    subject_dir = settings.upload_dir / subject_id / "anat"
    if not subject_dir.exists():
        raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")

    # Find available modalities
    t1_files = list(subject_dir.glob(f"{subject_id}_T1w*"))
    flair_files = list(subject_dir.glob(f"{subject_id}_FLAIR*"))
    swi_files = list(subject_dir.glob(f"{subject_id}_SWI*"))

    if not t1_files and not flair_files and not swi_files:
        raise HTTPException(status_code=404, detail="No MRI files found for subject")

    t1_path = t1_files[0] if t1_files else None
    flair_path = flair_files[0] if flair_files else None
    swi_path = swi_files[0] if swi_files else None

    # Synchronous execution (dev/test or Celery unavailable)
    if sync:
        return _run_sync(t1_path, chronological_age, sex, flair_path, swi_path)

    # Async execution via Celery
    try:
        from synapse_d.api.tasks import analyze_mri_task

        task = analyze_mri_task.delay(
            str(t1_path) if t1_path else None,
            chronological_age,
            sex,
            str(flair_path) if flair_path else None,
            str(swi_path) if swi_path else None,
        )
        return {"job_id": task.id, "status": "submitted"}
    except Exception:
        return _run_sync(t1_path, chronological_age, sex, flair_path, swi_path)


@app.get("/api/v1/results/{job_id}")
async def get_results(job_id: str):
    """Get analysis results for a job.

    Checks Celery result backend (Redis) for job state and results.
    """
    try:
        from synapse_d.api.tasks import celery_app

        task_result = celery_app.AsyncResult(job_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Result backend unavailable")

    if task_result.state == "PENDING":
        return {"job_id": job_id, "status": "pending"}
    elif task_result.state == "PREPROCESSING":
        return {
            "job_id": job_id,
            "status": "processing",
            "detail": task_result.info.get("step", "unknown") if task_result.info else None,
        }
    elif task_result.state == "SUCCESS":
        return {
            "job_id": job_id,
            "status": "completed",
            "result": _sanitize_result(task_result.result),
        }
    elif task_result.state == "FAILURE":
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(task_result.result),
        }
    else:
        return {"job_id": job_id, "status": task_result.state.lower()}


@app.get("/api/v1/subjects")
async def list_subjects():
    """List all uploaded subjects."""
    subjects = []
    if settings.upload_dir.exists():
        for d in sorted(settings.upload_dir.iterdir()):
            if d.is_dir() and _SUBJECT_ID_RE.match(d.name):
                has_t1 = (
                    bool(list((d / "anat").glob("*_T1w*")))
                    if (d / "anat").exists()
                    else False
                )
                subjects.append({"subject_id": d.name, "has_t1": has_t1})
    return {"subjects": subjects}


@app.get("/api/v1/subject/{subject_id}/results")
async def get_subject_results(subject_id: str):
    """Get the latest analysis results for a subject.

    Reconstructs results from processed outputs: morphometrics, brain age,
    WMH, microbleeds, connectome, normative comparison, and AD risk.
    """
    _validate_subject_id(subject_id)

    from synapse_d.models.longitudinal import _load_record

    # Load latest timepoint data
    timepoints = _load_record(subject_id)
    if not timepoints:
        from fastapi import HTTPException as HE
        raise HE(status_code=404, detail=f"No analysis results for {subject_id}")

    latest = timepoints[-1]

    # Build result summary from timepoint + metadata
    result: dict = {
        "subject_id": subject_id,
        "session_id": latest.session_id,
        "scan_date": latest.scan_date,
        "age_at_scan": latest.age_at_scan,
        "tier": latest.tier,
        "brain_volume_cm3": latest.brain_volume_cm3,
        "hippocampus_mm3": latest.hippocampus_mm3,
        "cortical_thickness_mm": latest.cortical_thickness_mm,
    }

    # Brain Age
    if latest.brain_age is not None:
        result["brain_age"] = {
            "predicted_age": latest.brain_age,
            "brain_age_gap": latest.brain_age_gap,
        }

    # Metadata (scanner, identity check, etc.)
    result["metadata"] = latest.metadata

    # Try to load additional results from processed directory
    import json
    result_file = settings.output_dir / subject_id / "latest_result.json"
    if result_file.exists():
        try:
            saved = json.loads(result_file.read_text())
            for key in ("wmh", "microbleeds", "normative", "ad_risk", "connectome"):
                if key in saved:
                    result[key] = saved[key]
        except (json.JSONDecodeError, OSError):
            pass

    # Sanitize paths + remove large data not needed by frontend
    output_dir_str = str(settings.output_dir)
    for section in ("wmh", "microbleeds"):
        data = result.get(section, {})
        if isinstance(data, dict) and "segmentation_path" in data:
            data.pop("segmentation_path", None)
    conn = result.get("connectome", {})
    if isinstance(conn, dict):
        conn.pop("connectivity_matrix", None)
        conn.pop("region_labels", None)

    return result


@app.get("/api/v1/subject/{subject_id}/report")
async def get_subject_report(subject_id: str):
    """Generate and return an HTML analysis report for a subject.

    Returns a self-contained HTML report with charts, metrics, and
    clinical interpretation. Can be opened in browser or printed to PDF.
    """
    _validate_subject_id(subject_id)

    import json
    result_file = settings.output_dir / subject_id / "latest_result.json"
    if not result_file.exists():
        raise HTTPException(status_code=404, detail=f"No analysis results for {subject_id}")

    try:
        result = json.loads(result_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read results: {e}")

    from synapse_d.report.generator import generate_report
    from fastapi.responses import HTMLResponse

    html = generate_report(result, subject_id)
    return HTMLResponse(content=html)


@app.get("/api/v1/longitudinal/{subject_id}")
async def get_longitudinal_data(subject_id: str):
    """Get longitudinal analysis data for a subject.

    Returns time-series data for brain volume, hippocampal volume,
    cortical thickness, and Brain Age Gap across all analysis sessions.
    Includes annualized change rates and comparison against expected aging.
    """
    _validate_subject_id(subject_id)

    from synapse_d.models.longitudinal import get_longitudinal

    result = get_longitudinal(subject_id)
    return {
        "subject_id": subject_id,
        "timepoint_count": len(result.timepoints),
        "summary": result.summary,
    }
