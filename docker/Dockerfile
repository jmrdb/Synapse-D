# Synapse-D Brain Digital Twin Platform
# CPU build — compatible with Mac Silicon (ARM64) and x86

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

# Install application
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "synapse_d.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
