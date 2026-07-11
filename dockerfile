# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --- test stage: this is what CI runs ---
FROM base AS test
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN pytest

# --- runtime stage: what you'd actually deploy ---
FROM base AS runtime
COPY src ./src
COPY config ./config
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]