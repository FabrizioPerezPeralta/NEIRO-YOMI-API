FROM python:3.12-slim

WORKDIR /app

# Install system audio libraries and FFmpeg for high-fidelity audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    flac \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code into /app
COPY . .

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

# Support dynamic PORT assignment for Railway, Render, Fly.io, and Cloud Run
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
