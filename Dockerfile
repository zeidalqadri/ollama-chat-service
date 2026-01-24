FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .
COPY static static/

# Create data directory for SQLite
RUN mkdir -p /app/data /app/stream_cache

# Environment
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8501"]
