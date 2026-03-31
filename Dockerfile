# Default: docker.io. If your docker.io mirror/proxy is flaky, override base image registry:
#   docker build --build-arg PYTHON_BUILDER_IMAGE=public.ecr.aws/docker/library/python:3.11-slim -t dental-booking-backend:local .
ARG PYTHON_BUILDER_IMAGE=python:3.11-slim
FROM ${PYTHON_BUILDER_IMAGE} AS builder

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir "poetry>=1.8.0,<3" && \
    poetry config virtualenvs.create false

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx,sys; r=httpx.get('http://localhost:8000/health', timeout=5); sys.exit(0 if r.status_code==200 else 1)"

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
