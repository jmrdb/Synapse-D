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
    t1_path: Path | None,
    chronological_age: float | None = None,
    sex: str | None = None,
    flair_path: Path | str | None = None,
    swi_path: Path | str | None = None,
) -> dict:
    """Execute the full analysis pipeline.

    Runs T1 pipeline (brain extraction, segmentation, Brain Age) and
    optionally FLAIR/WMH and SWI/CMB pipelines if data is available.

    Args:
        t1_path: Path to T1w NIfTI file (None if only FLAIR/SWI analysis).
        chronological_age: Optional actual age.
        sex: Optional biological sex ('M' or 'F') for normative comparison.
        flair_path: Optional path to T2-FLAIR NIfTI for WMH segmentation.
        swi_path: Optional path to SWI NIfTI for microbleed detection.

    Returns:
        Dict with preprocessing, brain age, WMH, and normative results.
    """
    from synapse_d.models.brain_age import BrainAgePredictor
    from synapse_d.pipeline.preprocessing import PreprocessingPipeline

    if isinstance(flair_path, str):
        flair_path = Path(flair_path) if flair_path else None
    if isinstance(swi_path, str):
        swi_path = Path(swi_path) if swi_path else None

    if not t1_path and not flair_path and not swi_path:
        raise ValueError("At least one modality (T1, FLAIR, or SWI) must be provided")

    # T1 pipeline
    pipeline = PreprocessingPipeline()
    if t1_path:
        preproc_result = pipeline.run(t1_path if isinstance(t1_path, Path) else Path(t1_path))
    else:
        # FLAIR-only analysis — create minimal result
        from synapse_d.pipeline.preprocessing import PreprocessingResult
        preproc_result = PreprocessingResult(
            subject_id=Path(str(flair_path or swi_path)).name.split("_")[0] if (flair_path or swi_path) else "unknown",
            success=True,
        )

    warnings = list(preproc_result.errors)
    if preproc_result.used_fallback:
        warnings.insert(0, "FALLBACK: Approximate brain extraction used (HD-BET not available)")

    tier = preproc_result.resolution_info.get("tier", "basic")  # fail-safe default

    result = {
        "subject_id": preproc_result.subject_id,
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

    # Step 3: WMH segmentation (if FLAIR available) — runs BEFORE normative
    if flair_path and flair_path.exists():
        try:
            from synapse_d.pipeline.wmh import segment_wmh

            wmh_result = segment_wmh(flair_path)
            result["wmh"] = wmh_result.to_dict()
        except Exception as e:
            logger.error(f"WMH segmentation failed: {e}")
            from synapse_d.pipeline.wmh import WMHResult
            result["wmh"] = WMHResult(
                success=False, errors=[f"WMH segmentation failed: {type(e).__name__}"]
            ).to_dict()

    # Step 3b: CMB detection from SWI (if available)
    if swi_path and swi_path.exists():
        try:
            from synapse_d.pipeline.microbleed import detect_microbleeds

            cmb_result = detect_microbleeds(swi_path)
            result["microbleeds"] = cmb_result.to_dict()
        except Exception as e:
            logger.error(f"CMB detection failed: {e}")
            result["microbleeds"] = {
                "success": False, "cmb_count": 0,
                "errors": [f"CMB detection failed: {type(e).__name__}"],
            }

    # Step 4: Normative comparison (if age provided and morphometrics available)
    # Merge WMH + CMB into morphometrics for unified normative comparison
    morpho_for_norm = dict(preproc_result.morphometrics)
    if "wmh" in result and isinstance(result["wmh"], dict) and "wmh_volume_ml" in result["wmh"]:
        morpho_for_norm["wmh_volume_ml"] = result["wmh"]["wmh_volume_ml"]
    if "microbleeds" in result and isinstance(result["microbleeds"], dict):
        morpho_for_norm["cmb_count"] = result["microbleeds"].get("cmb_count", 0)
    if chronological_age is not None and morpho_for_norm:
        try:
            from synapse_d.models.normative import compare_normative

            raw_field = preproc_result.scanner_info.get("field_strength_t", 0.0)
            try:
                field_t = float(raw_field)
            except (TypeError, ValueError):
                logger.warning(f"Invalid field_strength_t: {raw_field!r}, defaulting to 0.0")
                field_t = 0.0
            norm_result = compare_normative(
                morphometrics=morpho_for_norm,
                age=chronological_age,
                sex=sex or "M",
                field_strength_t=float(field_t),
                subject_id=preproc_result.subject_id,
            )
            result["normative"] = norm_result.summary

            # Step 4b: AD/MCI risk assessment (uses normative z-scores)
            try:
                from synapse_d.models.ad_risk import assess_ad_risk

                scores = norm_result.summary.get("scores", [])
                if scores:
                    brain_age_data = result.get("brain_age", {})
                    gap = brain_age_data.get("brain_age_gap") if isinstance(brain_age_data, dict) else None
                    ad_result = assess_ad_risk(
                        normative_scores=scores,
                        brain_age_gap=gap,
                        age=chronological_age,
                        subject_id=preproc_result.subject_id,
                    )
                    result["ad_risk"] = ad_result.to_dict()
            except Exception as e:
                logger.error(f"AD risk assessment failed: {e}")
                result["ad_risk"] = {"error": "AD risk assessment failed"}
        except Exception as e:
            result["normative"] = {"error": str(e)}

    # Step 5: Structural connectome generation (dMRI tractography or synthetic)
    try:
        from synapse_d.pipeline.connectome import generate_connectome

        # Search for dMRI (tractography-capable, 30+ directions) data
        # DWI (clinical stroke, 1-3 directions) is NOT used for tractography
        dmri_path = None
        # Build search directories from any available modality path
        ref_path = t1_path or flair_path or swi_path
        search_dirs = []
        if ref_path:
            ref = Path(str(ref_path))
            search_dirs.append(ref.parent)                # anat/
            search_dirs.append(ref.parent.parent / "dwi") # dwi/

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            # First: explicit dMRI files
            for candidate in search_dir.glob("*_dMRI*"):
                if candidate.suffix in (".gz", ".nii"):
                    dmri_path = candidate
                    break
            if dmri_path:
                break
            # Second: dwi files but only if they have 30+ directions (bval check)
            for candidate in search_dir.glob("*_dwi.nii.gz"):
                bval = candidate.with_name(candidate.name.replace(".nii.gz", ".bval"))
                if not bval.exists():
                    bval = candidate.with_name(candidate.name.replace(".nii.gz", ".bvals"))
                if bval.exists():
                    n_dirs = len(bval.read_text().split())
                    if n_dirs >= 30:
                        dmri_path = candidate
                        break
            if dmri_path:
                break

        connectome = generate_connectome(
            dwi_path=dmri_path,
            morphometrics=preproc_result.morphometrics,
            subject_id=preproc_result.subject_id,
        )
        if connectome.success:
            result["connectome"] = connectome.to_dict()
    except Exception as e:
        logger.warning(f"Connectome generation failed: {e}")

    # Step 6: Save longitudinal timepoint (auto-accumulate for time series)
    try:
        from synapse_d.models.longitudinal import save_timepoint

        brain_path = str(preproc_result.brain_extracted) if preproc_result.brain_extracted else None
        tp = save_timepoint(
            subject_id=preproc_result.subject_id,
            analysis_result=result,
            age_at_scan=chronological_age,
            brain_extracted_path=brain_path,
        )
        # Surface identity check result in API response
        id_check = tp.metadata.get("identity_check")
        if id_check:
            result["identity_check"] = id_check
    except Exception as e:
        logger.warning(f"Failed to save longitudinal timepoint: {e}")

    return result


@celery_app.task(bind=True, name="synapse_d.analyze_mri")
def analyze_mri_task(
    self,
    t1_path_str: str | None,
    chronological_age: float | None = None,
    sex: str | None = None,
    flair_path_str: str | None = None,
    swi_path_str: str | None = None,
) -> dict:
    """Celery task: run full MRI analysis pipeline asynchronously.

    Args:
        t1_path_str: String path to T1w NIfTI file.
        chronological_age: Optional actual age for Brain Age Gap.
        sex: Optional biological sex.
        flair_path_str: Optional FLAIR NIfTI for WMH analysis.
        swi_path_str: Optional SWI NIfTI for microbleed detection.

    Returns:
        Dict with preprocessing, brain age, WMH, CMB, and normative results.
    """
    self.update_state(state="PREPROCESSING", meta={"step": "brain_extraction"})
    t1 = Path(t1_path_str) if t1_path_str else None
    flair = Path(flair_path_str) if flair_path_str else None
    swi = Path(swi_path_str) if swi_path_str else None
    return run_pipeline(t1, chronological_age, sex, flair, swi)
