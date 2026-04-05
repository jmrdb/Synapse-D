"""Celery async task definitions.

Wraps the preprocessing pipeline and Brain Age prediction as
background tasks for non-blocking API responses.
MRI 전처리는 수 분~1시간 소요되므로 반드시 비동기로 실행해야
API 서버의 응답 불능(Timeout)을 방지할 수 있다.
"""

from pathlib import Path

from celery import Celery
from loguru import logger

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


def run_pipeline(
    t1_path: Path,
    chronological_age: float | None = None,
    sex: str | None = None,
) -> dict:
    """Execute the full analysis pipeline.

    Separated from API layer so it can be called from both
    Celery workers (production) and synchronous tests.

    Args:
        t1_path: Path to T1w NIfTI file.
        chronological_age: Optional actual age.
        sex: Optional biological sex ('M' or 'F') for normative comparison.

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

    tier = preproc_result.resolution_info.get("tier", "basic")  # fail-safe default

    result = {
        "preprocessing": {
            "success": preproc_result.success,
            "used_fallback": preproc_result.used_fallback,
            "brain_extracted": str(preproc_result.brain_extracted) if preproc_result.brain_extracted else None,
            "registered": str(preproc_result.registered) if preproc_result.registered else None,
            "segmentation": str(preproc_result.segmentation) if preproc_result.segmentation else None,
            "morphometrics": preproc_result.morphometrics,
            "scanner_info": preproc_result.scanner_info,
            "resolution": preproc_result.resolution_info,
            "errors": warnings,
        },
    }

    # Step 2: Brain Age — FULL and STANDARD only (BASIC: MAE 7-10yr, unreliable)
    if preproc_result.brain_extracted and tier != "basic":
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
            logger.error(f"Brain age prediction failed: {e}")
            result["brain_age"] = {"error": "Brain age prediction failed"}
    elif tier == "basic":
        result["brain_age"] = {
            "blocked": True,
            "reason": "해상도 부족 (>3mm): Brain Age 예측은 1.5mm 이하 T1에서만 제공",
        }

    # Step 3: Normative comparison (if age provided and morphometrics available)
    if chronological_age is not None and preproc_result.morphometrics:
        try:
            from synapse_d.models.normative import compare_normative

            raw_field = preproc_result.scanner_info.get("field_strength_t", 0.0)
            try:
                field_t = float(raw_field)
            except (TypeError, ValueError):
                logger.warning(f"Invalid field_strength_t: {raw_field!r}, defaulting to 0.0")
                field_t = 0.0
            norm_result = compare_normative(
                morphometrics=preproc_result.morphometrics,
                age=chronological_age,
                sex=sex or "M",
                field_strength_t=float(field_t),
                subject_id=preproc_result.subject_id,
            )
            result["normative"] = norm_result.summary
        except Exception as e:
            result["normative"] = {"error": str(e)}

    # Step 4: Save longitudinal timepoint (auto-accumulate for time series)
    try:
        from synapse_d.models.longitudinal import save_timepoint

        save_timepoint(
            subject_id=preproc_result.subject_id,
            analysis_result=result,
            age_at_scan=chronological_age,
        )
    except Exception as e:
        logger.warning(f"Failed to save longitudinal timepoint: {e}")

    return result


@celery_app.task(bind=True, name="synapse_d.analyze_mri")
def analyze_mri_task(
    self,
    t1_path_str: str,
    chronological_age: float | None = None,
    sex: str | None = None,
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
    return run_pipeline(Path(t1_path_str), chronological_age, sex)
