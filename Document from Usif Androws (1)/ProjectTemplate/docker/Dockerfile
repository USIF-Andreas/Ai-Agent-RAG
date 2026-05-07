FROM python:3.11-slim

ENV PYTHONPATH=/app

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src/
COPY templates ./templates/
COPY static ./static/
COPY ../.env .

# Healthcheck to ensure container is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "src/main.py"]
