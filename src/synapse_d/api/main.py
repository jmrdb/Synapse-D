"""Synapse-D API Server.

FastAPI application providing REST endpoints for MRI upload,
preprocessing pipeline execution, and Brain Age prediction.
"""

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

# In-memory job store (replace with DB in production)
_jobs: dict[str, dict] = {}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


@app.post("/api/v1/upload")
async def upload_mri(file: UploadFile = File(...)):
    """Upload a T1-weighted MRI NIfTI file.

    Accepts .nii or .nii.gz files. Returns a subject_id for tracking.

    Args:
        file: NIfTI file upload.

    Returns:
        JSON with subject_id and upload status.
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
async def start_analysis(subject_id: str, chronological_age: float | None = None):
    """Start preprocessing + Brain Age analysis for an uploaded MRI.

    This triggers the async pipeline: HD-BET → ANTs → FastSurfer → SFCN Brain Age.

    Args:
        subject_id: Subject ID from upload response.
        chronological_age: Optional actual age for Brain Age Gap calculation.

    Returns:
        JSON with job_id and status.
    """
    # Find the uploaded file
    subject_dir = settings.upload_dir / subject_id / "anat"
    if not subject_dir.exists():
        raise HTTPException(status_code=404, detail=f"Subject {subject_id} not found")

    nifti_files = list(subject_dir.glob(f"{subject_id}_T1w*"))
    if not nifti_files:
        raise HTTPException(status_code=404, detail="No T1w file found for subject")

    t1_path = nifti_files[0]
    job_id = uuid.uuid4().hex[:12]

    # Run synchronously for now (async Celery integration in production)
    _jobs[job_id] = {"status": "running", "subject_id": subject_id}

    try:
        result = _run_pipeline(t1_path, chronological_age)
        _jobs[job_id] = {
            "status": "completed",
            "subject_id": subject_id,
            "result": result,
        }
    except Exception as e:
        _jobs[job_id] = {
            "status": "failed",
            "subject_id": subject_id,
            "error": str(e),
        }

    return {"job_id": job_id, "status": _jobs[job_id]["status"]}


@app.get("/api/v1/results/{job_id}")
async def get_results(job_id: str):
    """Get analysis results for a completed job.

    Args:
        job_id: Job ID from analyze response.

    Returns:
        JSON with full analysis results including Brain Age and morphometrics.
    """
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[job_id]
    if job["status"] == "running":
        return {"job_id": job_id, "status": "running"}
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=job.get("error", "Unknown error"))

    return {"job_id": job_id, **job}


@app.get("/api/v1/subjects")
async def list_subjects():
    """List all uploaded subjects.

    Returns:
        JSON with list of subject IDs and their analysis status.
    """
    subjects = []
    if settings.upload_dir.exists():
        for d in sorted(settings.upload_dir.iterdir()):
            if d.is_dir() and d.name.startswith("sub-"):
                subjects.append({
                    "subject_id": d.name,
                    "has_t1": bool(list((d / "anat").glob("*_T1w*"))) if (d / "anat").exists() else False,
                })
    return {"subjects": subjects}


def _run_pipeline(t1_path: Path, chronological_age: float | None = None) -> dict:
    """Execute the full analysis pipeline synchronously.

    Args:
        t1_path: Path to T1w NIfTI file.
        chronological_age: Optional actual age.

    Returns:
        Dict with preprocessing and brain age results.
    """
    from synapse_d.models.brain_age import BrainAgePredictor
    from synapse_d.pipeline.preprocessing import PreprocessingPipeline

    # Step 1: Preprocessing
    pipeline = PreprocessingPipeline()
    preproc_result = pipeline.run(t1_path)

    result = {
        "preprocessing": {
            "success": preproc_result.success,
            "brain_extracted": str(preproc_result.brain_extracted) if preproc_result.brain_extracted else None,
            "registered": str(preproc_result.registered) if preproc_result.registered else None,
            "segmentation": str(preproc_result.segmentation) if preproc_result.segmentation else None,
            "morphometrics": preproc_result.morphometrics,
            "errors": preproc_result.errors,
        },
    }

    # Step 2: Brain Age prediction (if brain extraction succeeded)
    if preproc_result.brain_extracted:
        try:
            predictor = BrainAgePredictor()
            age_result = predictor.predict(
                preproc_result.brain_extracted,
                chronological_age=chronological_age,
            )
            result["brain_age"] = {
                "predicted_age": round(age_result.predicted_age, 1),
                "confidence": round(age_result.confidence, 3),
                "brain_age_gap": round(age_result.brain_age_gap, 1) if age_result.brain_age_gap is not None else None,
            }
        except Exception as e:
            result["brain_age"] = {"error": str(e)}

    return result
