# Synapse-D Brain Digital Twin Platform
# CPU build with HD-BET — proper skull stripping for clinical precision

FROM python:3.11-slim AS base

LABEL maintainer="Synapse-D Team"
LABEL description="Brain Digital Twin - Structural MRI preprocessing and AI prediction"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget libgl1-mesa-dri libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PyTorch CPU (smaller image, ARM64 compatible)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu 2>/dev/null \
    || pip install --no-cache-dir torch torchvision

# Install HD-BET for clinical-grade brain extraction (Apache 2.0)
# HD-BET provides accurate skull stripping — critical for all downstream analyses
RUN pip install --no-cache-dir hd-bet

# Pre-download HD-BET model weights so first run doesn't need internet
# HD-BET downloads weights to ~/.cache on first use
RUN python -c "from HD_BET.utils import maybe_download_parameters; maybe_download_parameters()" 2>/dev/null \
    || echo "HD-BET weights will download on first use"

# Install application
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "synapse_d.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
