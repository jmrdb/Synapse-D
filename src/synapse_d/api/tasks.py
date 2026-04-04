"""Celery async task definitions.

Wraps the preprocessing pipeline and Brain Age prediction as
background tasks for non-blocking API responses.
MRI 전처리는 수 분~1시간 소요되므로 반드시 비동기로 실행해야
API 서버의 응답 불능(Timeout)을 방지할 수 있다.
"""

from pathlib import Path

from celery import Celery

from synapse_d.config import settings

celery_app = Celery(
    "synapse_d",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    result_expires=86400,  # 결과 24시간 보관 (Redis)
)


def run_pipeline(t1_path: Path, chronological_age: float | None = None) -> dict:
    """Execute the full analysis pipeline.

    Separated from API layer so it can be called from both
    Celery workers (production) and synchronous tests.

    Args:
        t1_path: Path to T1w NIfTI file.
        chronological_age: Optional actual age.

    Returns:
        Dict with preprocessing and brain age results.
    """
    from synapse_d.models.brain_age import BrainAgePredictor
    from synapse_d.pipeline.preprocessing import PreprocessingPipeline

    pipeline = PreprocessingPipeline()
    preproc_result = pipeline.run(t1_path)

    warnings = list(preproc_result.errors)
    if preproc_result.used_fallback:
        warnings.insert(0, "FALLBACK: Approximate brain extraction used (HD-BET not available)")

    result = {
        "preprocessing": {
            "success": preproc_result.success,
            "used_fallback": preproc_result.used_fallback,
            "brain_extracted": str(preproc_result.brain_extracted) if preproc_result.brain_extracted else None,
            "registered": str(preproc_result.registered) if preproc_result.registered else None,
            "segmentation": str(preproc_result.segmentation) if preproc_result.segmentation else None,
            "morphometrics": preproc_result.morphometrics,
            "scanner_info": preproc_result.scanner_info,
            "errors": warnings,
        },
    }

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
                "brain_age_gap": (
                    round(age_result.brain_age_gap, 1)
                    if age_result.brain_age_gap is not None
                    else None
                ),
            }
        except Exception as e:
            result["brain_age"] = {"error": str(e)}

    # Step 3: Normative comparison (if age provided and morphometrics available)
    if chronological_age and preproc_result.morphometrics:
        try:
            from synapse_d.models.normative import compare_normative

            norm_result = compare_normative(
                morphometrics=preproc_result.morphometrics,
                age=chronological_age,
                subject_id=preproc_result.subject_id,
            )
            result["normative"] = norm_result.summary
        except Exception as e:
            result["normative"] = {"error": str(e)}

    return result


@celery_app.task(bind=True, name="synapse_d.analyze_mri")
def analyze_mri_task(
    self, t1_path_str: str, chronological_age: float | None = None
) -> dict:
    """Celery task: run full MRI analysis pipeline asynchronously.

    Called by the API server via .delay(). Progress is tracked via
    Celery's result backend (Redis), eliminating the need for
    in-memory job state on the API server.

    Args:
        t1_path_str: String path to T1w NIfTI file.
        chronological_age: Optional actual age for Brain Age Gap.

    Returns:
        Dict with preprocessing and brain age results.
    """
    self.update_state(state="PREPROCESSING", meta={"step": "brain_extraction"})
    return run_pipeline(Path(t1_path_str), chronological_age)
