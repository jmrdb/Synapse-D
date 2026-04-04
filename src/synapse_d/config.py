"""Platform configuration.

Global settings for Synapse-D platform, loaded from environment variables.
Docker 환경에서는 SYNAPSE_DATA_DIR=/app/data 로 설정하여
API와 Worker가 동일한 볼륨을 참조하도록 한다.
"""

from pathlib import Path

from pydantic_settings import BaseSettings


def _default_data_dir() -> Path:
    """Determine default data directory based on environment."""
    # Docker: /app/data (mounted volume)
    docker_path = Path("/app/data")
    if docker_path.exists():
        return docker_path
    # Local dev: project_root/data
    return Path(__file__).resolve().parent.parent.parent / "data"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Paths — override with SYNAPSE_DATA_DIR in Docker
    data_dir: Path = _default_data_dir()

    @property
    def sample_dir(self) -> Path:
        return self.data_dir / "sample"

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "processed"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # GPU
    device: str = "cpu"

    # Pipeline
    mni_template: str = "MNI152_T1_1mm"
    fastsurfer_sid_prefix: str = "synapse"

    model_config = {"env_prefix": "SYNAPSE_"}


settings = Settings()
