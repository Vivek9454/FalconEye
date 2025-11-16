# Multi-stage build for FalconEye
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p clips faces/images static

# Expose port
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:3001/mobile/status')" || exit 1

# Default command (can be overridden)
CMD ["python", "backend.py"]

# Production stage with Gunicorn
FROM base as production

RUN pip install --no-cache-dir gunicorn

# Use Gunicorn for production
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3001", "--timeout", "120", "--access-logfile", "-", "backend:app"]

