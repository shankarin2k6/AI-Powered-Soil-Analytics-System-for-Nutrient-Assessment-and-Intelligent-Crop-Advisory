# Soil Analytics API (FastAPI). Built by docker-compose.prod.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# libgomp1 is needed by XGBoost; curl-free image, health checks use Python
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# No PyTorch here: the image model runs on ONNX Runtime (small), so the image stays light enough for a 512 MB server
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh .
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh   # in case the file was saved with Windows line endings

# the trained models: copied in (soil_cnn.onnx etc. are small); docker-compose.prod.yml can also mount the folder over this one
COPY models ./models
RUN useradd --create-home --uid 10001 app && mkdir -p /app/uploads /app/models && chown -R app:app /app
USER app
EXPOSE 8000
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
