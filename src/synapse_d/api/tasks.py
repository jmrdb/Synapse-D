"""Celery async task definitions.

Wraps the preprocessing pipeline and Brain Age prediction as
background tasks for non-blocking API responses.
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
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3000,  # 50 min soft limit
)


@celery_app.task(bind=True, name="synapse_d.analyze_mri")
def analyze_mri(self, t1_path_str: str, chronological_age: float | None = None) -> dict:
    """Run full MRI analysis pipeline as async Celery task.

    Args:
        t1_path_str: String path to T1w NIfTI file.
        chronological_age: Optional actual age for Brain Age Gap.

    Returns:
        Dict with preprocessing and brain age results.
    """
    from synapse_d.api.main import _run_pipeline

    t1_path = Path(t1_path_str)
    self.update_state(state="PREPROCESSING", meta={"step": "brain_extraction"})

    result = _run_pipeline(t1_path, chronological_age)
    return result
