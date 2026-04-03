"""E2E test for the preprocessing pipeline using sample data.

Validates the full pipeline: input validation → brain extraction (fallback) →
morphometrics extraction. Uses sample T1w MRI from data/sample/.

Run: pytest tests/test_pipeline.py -v
"""

from pathlib import Path

import pytest

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"
T1_FILES = list(SAMPLE_DIR.glob("sub-*/anat/*_T1w.nii.gz"))


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path / "output"


@pytest.mark.skipif(not T1_FILES, reason="No sample T1w data available")
class TestPreprocessingPipeline:
    """Test suite for the preprocessing pipeline."""

    def test_bids_file_discovery(self):
        """Verify BIDS utility finds sample T1w files."""
        from synapse_d.utils.bids import find_t1w_files

        files = find_t1w_files(SAMPLE_DIR)
        assert len(files) >= 1, "Should find at least 1 T1w file in sample data"
        for f in files:
            assert f.name.endswith("_T1w.nii.gz")

    def test_subject_id_extraction(self):
        """Verify subject ID extraction from BIDS paths."""
        from synapse_d.utils.bids import get_subject_id

        sid = get_subject_id(T1_FILES[0])
        assert sid.startswith("sub-"), f"Expected sub-*, got {sid}"

    def test_nifti_loading(self):
        """Verify NIfTI files can be loaded and inspected."""
        from synapse_d.utils.bids import get_voxel_info, load_nifti

        img = load_nifti(T1_FILES[0])
        info = get_voxel_info(img)
        assert len(info["shape"]) == 3, "T1w should be 3D"
        assert all(s > 0 for s in info["shape"]), "All dimensions should be positive"
        assert all(v > 0 for v in info["voxel_size"]), "All voxel sizes should be positive"

    def test_pipeline_with_fallback(self, output_dir):
        """Run full pipeline with fallback brain extraction (no HD-BET/ANTs/FastSurfer).

        This test validates the pipeline logic without external tool dependencies.
        """
        from synapse_d.pipeline.preprocessing import PreprocessingPipeline

        pipeline = PreprocessingPipeline(output_dir=output_dir, device="cpu")
        result = pipeline.run(T1_FILES[0])

        assert result.subject_id.startswith("sub-")
        assert result.success, f"Pipeline should succeed with fallback. Errors: {result.errors}"
        assert result.brain_extracted is not None
        assert result.brain_extracted.exists()
        assert result.brain_mask is not None
        assert result.brain_mask.exists()
        assert "total_brain_volume_cm3" in result.morphometrics
        assert result.morphometrics["total_brain_volume_cm3"] > 0


@pytest.mark.skipif(not T1_FILES, reason="No sample T1w data available")
class TestBrainAge:
    """Test suite for Brain Age prediction."""

    def test_brain_age_prediction(self, output_dir):
        """Run Brain Age prediction on sample data.

        Uses fallback brain extraction, then predicts Brain Age with SFCN.
        """
        from synapse_d.models.brain_age import BrainAgePredictor
        from synapse_d.pipeline.preprocessing import PreprocessingPipeline

        # First, extract brain
        pipeline = PreprocessingPipeline(output_dir=output_dir, device="cpu")
        preproc = pipeline.run(T1_FILES[0])
        assert preproc.brain_extracted is not None

        # Predict brain age
        predictor = BrainAgePredictor(device="cpu")
        result = predictor.predict(preproc.brain_extracted, chronological_age=30.0)

        assert 0 < result.predicted_age < 120, f"Predicted age {result.predicted_age} out of range"
        assert 0 <= result.confidence <= 1
        assert len(result.age_distribution) == 40
        assert result.brain_age_gap is not None


class TestAPI:
    """Test suite for FastAPI endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient

        from synapse_d.api.main import app
        return TestClient(app)

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_list_subjects_empty(self, client):
        response = client.get("/api/v1/subjects")
        assert response.status_code == 200

    @pytest.mark.skipif(not T1_FILES, reason="No sample T1w data available")
    def test_upload_and_analyze(self, client):
        """E2E test: upload MRI → analyze → get results."""
        # Upload
        with open(T1_FILES[0], "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": (T1_FILES[0].name, f, "application/octet-stream")},
            )
        assert response.status_code == 200
        upload_data = response.json()
        subject_id = upload_data["subject_id"]

        # Analyze
        response = client.post(f"/api/v1/analyze/{subject_id}?chronological_age=30")
        assert response.status_code == 200
        job_data = response.json()
        job_id = job_data["job_id"]

        # Get results
        response = client.get(f"/api/v1/results/{job_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert result["result"]["preprocessing"]["success"] is True
