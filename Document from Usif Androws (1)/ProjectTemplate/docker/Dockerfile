FROM python:3.11-slim

ENV PYTHONPATH=/app

WORKDIR /app

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src/
COPY templates ./templates/
COPY static ./static/
COPY ../.env .

CMD ["python", "src/main.py"]
