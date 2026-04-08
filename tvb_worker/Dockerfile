# TVB Worker — GPLv3 isolated container
# This container runs TVB (The Virtual Brain) brain simulation engine.
# IMPORTANT: TVB is GPLv3 licensed. This container is intentionally
# separated from the main Synapse-D codebase (proprietary) to prevent
# GPL license contamination. Communication is via REST API only.

FROM python:3.10-slim

RUN pip install --no-cache-dir \
    tvb-library \
    fastapi \
    uvicorn[standard] \
    numpy \
    scipy

WORKDIR /app
COPY app.py .

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
