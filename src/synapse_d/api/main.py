"""Synapse-D API Server.

FastAPI application providing REST endpoints for MRI upload,
preprocessing pipeline execution, and Brain Age prediction.

Job state is managed via Celery's Redis result backend instead of
in-memory dicts, so state survives API server restarts.
"""

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from synapse_d import __version__
from synapse_d.config import settings

app = FastAPI(
    title="Synapse-D Brain Digital Twin API",
    description="Structural MRI-based brain development and degeneration prediction",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve processed NIfTI files for Niivue frontend rendering
settings.output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(settings.output_dir)), name="files")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


@app.post("/api/v1/upload")
async def upload_mri(file: UploadFile = File(...)):
    """Upload a T1-weighted MRI NIfTI file.

    Accepts .nii or .nii.gz files. Returns a subject_id for tracking.
    """
    if not file.filename or not (
        file.filename.endswith(".nii") or file.filename.endswith(".nii.gz")
    ):
        raise HTTPException(status_code=400, detail="Only .nii or .nii.gz files accepted")

    subject_id = f"sub-{uuid.uuid4().hex[:8]}"
    subject_dir = settings.upload_dir / subject_id / "anat"
    subject_dir.mkdir(parents=True, exist_ok=True)

    suffix = ".nii.gz" if file.filename.endswith(".nii.gz") else ".nii"
    save_path = subject_dir / f"{subject_id}_T1w{suffix}"

    content = await file.read()
    save_path.write_bytes(content)

    return {
        "subject_id": subject_id,
        "filename": file.filename,
        "size_mb": round(len(content) / 1024 / 1024, 2),
        "path": str(save_path),
    }


@app.post("/api/v1/analyze/{subject_id}")
async def start_analysis(
    subject_id: str,
    chronological_age: float | None = None,
    sync: bool = False,
):
    """Start preprocessing + Brain Age analysis for an uploaded MRI.

    By default dispatches to Celery worker (async). If Redis/Celery is
    unavailable or sync=True, falls back to synchronous execution.

    Args:
        subject_id: Subject ID from upload response.
        chronological_age: Optional actual age for Brain Age Gap.
        sync: Force synchronous execution (for testing/dev).
    """
    subject_dir = settings.upload_dir / subject_id / "anat"
    if not subject_dir.exists():
        raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")

    nifti_files = list(subject_dir.glob(f"{subject_id}_T1w*"))
    if not nifti_files:
        raise HTTPException(status_code=404, detail="No T1w file found for subject")

    t1_path = nifti_files[0]

    if sync:
        # Synchronous execution (dev/test mode)
        from synapse_d.api.tasks import run_pipeline

        result = run_pipeline(t1_path, chronological_age)
        job_id = uuid.uuid4().hex[:12]
        return {"job_id": job_id, "status": "completed", "result": result}

    # Async execution via Celery
    try:
        from synapse_d.api.tasks import analyze_mri_task

        task = analyze_mri_task.delay(str(t1_path), chronological_age)
        return {"job_id": task.id, "status": "submitted"}
    except Exception:
        # Celery/Redis unavailable — fallback to sync
        from synapse_d.api.tasks import run_pipeline

        result = run_pipeline(t1_path, chronological_age)
        job_id = uuid.uuid4().hex[:12]
        return {"job_id": job_id, "status": "completed", "result": result}


@app.get("/api/v1/results/{job_id}")
async def get_results(job_id: str):
    """Get analysis results for a job.

    Checks Celery result backend (Redis) for job state and results.
    Possible statuses: PENDING, PREPROCESSING, SUCCESS, FAILURE.
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
            "result": task_result.result,
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
            if d.is_dir() and d.name.startswith("sub-"):
                has_t1 = (
                    bool(list((d / "anat").glob("*_T1w*")))
                    if (d / "anat").exists()
                    else False
                )
                subjects.append({"subject_id": d.name, "has_t1": has_t1})
    return {"subjects": subjects}
