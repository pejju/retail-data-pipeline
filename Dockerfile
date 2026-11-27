# Image for running the ETL pipeline once, end to end.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so Docker can cache this layer between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY SQL/ SQL/

ENV PYTHONPATH=/app/src
CMD ["python", "-m", "retail_pipeline.run_pipeline"]
