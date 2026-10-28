# InfraGuard Production Dockerfile
# Multi-Infrastructure AI Monitoring & Predictive Maintenance Platform

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered streaming logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    INFRAGUARD_ENV=production

# Install system dependencies for image processing and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user for container security
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install Python dependencies with layer caching
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application directories and files
COPY backend /app/backend
COPY frontend /app/frontend
COPY models /app/models
COPY docs /app/docs

# Copy sample data directory structure (excluding active databases)
COPY data/sample /app/data/sample

# Create and set permissions for runtime storage directories
RUN mkdir -p /app/data/uploads /app/data/processed /app/data/datasets && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose standard application port
EXPOSE 8000

# Container healthcheck verifying the InfraGuard operational health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Launch application using dynamic shell port binding for cloud platforms
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
