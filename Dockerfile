# Multi-stage build for CogView4-FastAPI

# Stage 1: Build stage
FROM python:3.10-slim AS base

# Set environment variables for build
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

FROM base AS builder
# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install -i https://mirrors.aliyun.com/pypi/simple  --no-cache-dir --upgrade pip wheel setuptools

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install -i https://mirrors.aliyun.com/pypi/simple  --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM base AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/static/images /app/logs \
    && chown -R appuser:appuser /app

# Set permissions for executable files
RUN chmod +x run_server.py start_server.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Set default environment variables
ENV NUM_WORKER_PROCESSES=1
ENV MAX_TOTAL_PIXELS=4194304
ENV MODEL_PATH=/gm-models/CogView4-6B
ENV ENABLE_PROMPT_BATCHING=true
ENV BATCH_TIMEOUT=0.5
ENV MAX_BATCH_SIZE=8
ENV LOG_LEVEL=INFO
ENV LOG_FILE=/app/logs/cogview4_api.log

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "run_server.py"] 