"""Platform configuration.

Global settings for Synapse-D platform, loaded from environment variables.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = base_dir / "data"
    sample_dir: Path = data_dir / "sample"
    upload_dir: Path = data_dir / "raw"
    output_dir: Path = data_dir / "processed"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # GPU
    device: str = "cpu"  # "cpu" or "cuda"

    # Pipeline
    mni_template: str = "MNI152_T1_1mm"
    fastsurfer_sid_prefix: str = "synapse"

    model_config = {"env_prefix": "SYNAPSE_"}


settings = Settings()
