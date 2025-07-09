# Docker Setup for CogView4-FastAPI

This document explains how to run the CogView4-FastAPI application using Docker with multi-stage builds for optimal performance and security.

## Prerequisites

- Docker installed on your system
- Docker Compose (usually comes with Docker Desktop)
- At least 8GB of RAM available for the container
- CogView4 model files (see Model Setup section)

## Multi-Stage Build Benefits

The Dockerfile uses a multi-stage build approach that provides:

- **Smaller final image size** - Build dependencies are not included in the runtime image
- **Better security** - Reduced attack surface by excluding build tools
- **Faster builds** - Better layer caching and optimization
- **Non-root user** - Application runs as a dedicated user for security

## Quick Start

### 1. Build and Run with Docker Compose (Recommended)

```bash
# Clone the repository (if not already done)
git clone <your-repo-url>
cd CogView4-FastAPI

# Create necessary directories
mkdir -p logs static/images

# Update the model path in docker-compose.yml
# Edit the volume mount: - /path/to/your/models:/gm-models:ro

# Build and start the container
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 2. Run with Docker directly

```bash
# Build the image (multi-stage build)
docker buildx build --platform amd64 -t  registry.aimall.ai-links.com/ailinks/aigc-image:v0.1.5 .

# Run the container
# don't limit cpu, which are needed by quatinization
chmod -R 777 $(pwd)/static/images
docker stop aigc-image; docker rm aigc-image
docker run -d \
  --name aigc-image \
  -p 8000:8000 \
  --gpus 3 \
  --env NUM_WORKER_PROCESSES=3 \
  -v /gm-models:/gm-models:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/static/images:/app/static/images \
  --memory=128g \
  registry.aimall.ai-links.com/ailinks/aigc-image:v0.1.5
```

### 3. Build specific stages (for development)

```bash

# Build only the builder stage for development
docker build --target builder -t cogview4-builder .

# Build runtime stage (default)
docker build --target runtime -t cogview4-fastapi .
```

## Model Setup

The application expects the CogView4 model to be available at `/gm-models/CogView4-6B` inside the container.

### Option 1: Mount existing model directory
```bash
# If you have the model locally
docker run -v /path/to/your/models:/gm-models:ro ...
```

### Option 2: Download model inside container
```bash
# Run container with interactive shell
docker run -it --rm cogview4-fastapi /bin/bash

# Inside container, download the model
# (You'll need to implement the download logic based on your model source)
```

## Environment Variables

You can customize the application behavior using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `NUM_WORKER_PROCESSES` | 1 | Number of worker processes |
| `MAX_TOTAL_PIXELS` | 4194304 | Maximum total pixels per request |
| `MODEL_PATH` | `/gm-models/CogView4-6B` | Path to the CogView4 model |
| `ENABLE_PROMPT_BATCHING` | true | Enable prompt batching |
| `BATCH_TIMEOUT` | 0.5 | Batch timeout in seconds |
| `MAX_BATCH_SIZE` | 8 | Maximum batch size |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FILE` | `/app/logs/cogview4_api.log` | Log file path |

## Volume Mounts

The following directories should be mounted for persistence:

- **Models**: `/gm-models` (read-only) - Contains the CogView4 model files
- **Logs**: `/app/logs` - Application logs
- **Gallery Images**: `/app/static/images` - Generated images for the gallery

## Security Features

The multi-stage build includes several security enhancements:

- **Non-root user**: Application runs as `appuser` instead of root
- **Minimal runtime dependencies**: Only necessary libraries are included
- **Read-only model mount**: Model files are mounted as read-only
- **No new privileges**: Container cannot gain additional privileges
- **Temporary filesystem**: `/tmp` is mounted as tmpfs for security

## Health Check

The container includes a health check that verifies the API is responding:

```bash
# Check container health
docker ps

# View health check logs
docker inspect cogview4-fastapi | grep -A 10 "Health"
```

## Monitoring and Logs

```bash
# View container logs
docker logs cogview4-fastapi

# Follow logs in real-time
docker logs -f cogview4-fastapi

# Access container shell (as appuser)
docker exec -it cogview4-fastapi /bin/bash

# Check resource usage
docker stats cogview4-fastapi
```

## Resource Requirements

- **Memory**: Minimum 4GB, recommended 8GB+
- **CPU**: Multi-core recommended for better performance (2-4 cores)
- **Storage**: At least 10GB for the container and model files

## Troubleshooting

### Container won't start
```bash
# Check container logs
docker logs cogview4-fastapi

# Check if model path is correct
docker exec -it cogview4-fastapi ls -la /gm-models

# Check user permissions
docker exec -it cogview4-fastapi whoami
```

### Out of memory errors
```bash
# Increase memory limit
docker run --memory=12g --cpus=6.0 ...
```

### Model not found
```bash
# Verify model path
docker exec -it cogview4-fastapi ls -la /gm-models/CogView4-6B

# Check volume mount
docker inspect cogview4-fastapi | grep -A 5 "Mounts"
```

### Permission issues
```bash
# Check file ownership
docker exec -it cogview4-fastapi ls -la /app

# Fix permissions if needed
docker exec -it cogview4-fastapi chown -R appuser:appuser /app/logs
```

### Port already in use
```bash
# Use different port
docker run -p 8001:8000 ...
```

## Production Deployment

For production deployment, consider:

1. **Using a reverse proxy** (nginx, traefik)
2. **Setting up proper logging** with log aggregation
3. **Implementing monitoring** (Prometheus, Grafana)
4. **Using secrets management** for sensitive configuration
5. **Setting up backup** for the gallery images

### Example with nginx reverse proxy

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  cogview4-api:
    build:
      context: .
      target: runtime
    container_name: cogview4-fastapi
    expose:
      - "8000"
    environment:
      - NUM_WORKER_PROCESSES=2
    volumes:
      - /path/to/models:/gm-models:ro
      - ./logs:/app/logs
      - ./static/images:/app/static/images
    deploy:
      resources:
        limits:
          memory: 12G
          cpus: '6.0'
    security_opt:
      - no-new-privileges:true
    networks:
      - cogview4-network

  nginx:
    image: nginx:alpine
    container_name: cogview4-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - cogview4-api
    networks:
      - cogview4-network

networks:
  cogview4-network:
    driver: bridge
```

## Security Considerations

1. **Non-root execution** - Application runs as dedicated user
2. **Read-only model mounts** - Model files cannot be modified
3. **Minimal attack surface** - Only runtime dependencies included
4. **Resource limits** - Prevents resource exhaustion attacks
5. **No privilege escalation** - Container cannot gain additional privileges
6. **Regular security updates** - Keep base images updated

## Performance Optimization

1. **Use GPU acceleration** if available:
   ```bash
   docker run --gpus all ...
   ```

2. **Optimize worker processes** based on your hardware:
   ```bash
   docker run -e NUM_WORKER_PROCESSES=2 ...
   ```

3. **Use SSD storage** for better I/O performance

4. **Monitor resource usage**:
   ```bash
   docker stats cogview4-fastapi
   ```

5. **Tune memory and CPU limits**:
   ```bash
   docker run --memory=12g --cpus=6.0 ...
   ```

## Build Optimization

The multi-stage build provides several optimization opportunities:

```bash
# Build with specific target
docker build --target builder -t cogview4-builder .

# Build with build cache
docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t cogview4-fastapi .

# Use BuildKit for faster builds
DOCKER_BUILDKIT=1 docker build -t cogview4-fastapi .
``` 