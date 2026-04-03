# Synapse-D Brain Digital Twin Platform
# Multi-stage build: backend (Python/FastAPI) + GPU support

FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime AS base

LABEL maintainer="Synapse-D Team"
LABEL description="Brain Digital Twin - Structural MRI preprocessing and AI prediction"

# System dependencies for neuroimaging
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[gpu]" 2>/dev/null || pip install --no-cache-dir .

# Application code
COPY src/ src/

EXPOSE 8000

CMD ["uvicorn", "synapse_d.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
