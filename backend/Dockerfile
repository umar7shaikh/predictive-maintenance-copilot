# Backend image: FastAPI app, Celery worker, and MLflow server all run from this image.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first for better layer caching.
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default command runs the API; compose overrides it for the worker / mlflow services.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
