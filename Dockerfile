FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "digital_brain.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
