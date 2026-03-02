# ============================================
# PARKING MANAGEMENT SYSTEM - BACKEND DOCKERFILE
# ============================================
# Multi-stage Docker build for production and development
# ============================================

# ---------- Base Stage ----------
# Shared base for all stages
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

# Set working directory
WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 --gid 1001 appuser

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---------- Builder Stage ----------
# Install Python dependencies
FROM base AS builder

# Copy requirements files
COPY requirements.txt requirements-dev.txt ./

# Create virtual environment and install dependencies
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip setuptools wheel && \
    /venv/bin/pip install -r requirements.txt && \
    if [ -f requirements-dev.txt ]; then /venv/bin/pip install -r requirements-dev.txt; fi

# ---------- Development Stage ----------
# For local development with hot reload
FROM base AS development

# Copy virtual environment from builder
COPY --from=builder /venv /venv

# Add venv to PATH
ENV PATH="/venv/bin:$PATH"

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    postgresql-client \
    redis-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Expose development port
EXPOSE 8000 8001 5678

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command for development
CMD ["uvicorn", "parking-api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- Test Stage ----------
# For running tests
FROM development AS test

# Copy test configuration
COPY pytest.ini ./
COPY .coveragerc ./

# Copy source code
COPY . .

# Run tests
CMD ["pytest", "tests/", "-v", "--cov=.", "--cov-report=html", "--cov-report=xml"]

# ---------- Production Stage ----------
# Production-ready image
FROM base AS production

# Copy virtual environment from builder
COPY --from=builder /venv /venv

# Add venv to PATH
ENV PATH="/venv/bin:$PATH"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads && \
    chown -R appuser:appuser /app/logs /app/uploads

# Security hardening
RUN apt-get update && apt-get install -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && find /venv -type d -name "tests" -exec rm -rf {} + \
    && find /venv -type d -name "docs" -exec rm -rf {} + \
    && find /venv -type f -name "*.pyc" -delete \
    && find /venv -type f -name "*.pyo" -delete \
    && find /venv -type f -name "*.c" -delete \
    && find /venv -type f -name "*.h" -delete

# Remove unnecessary packages
RUN apt-get remove -y gcc && apt-get autoremove -y

# Copy production entrypoint
COPY docker-entrypoint.prod.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Expose production port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Default command for production
CMD ["uvicorn", "parking-api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ---------- CI Stage ----------
# For CI/CD pipelines
FROM production AS ci

# Install CI tools
RUN pip install pytest pytest-cov pytest-xdist pytest-html

# Copy test configuration
COPY pytest.ini ./
COPY .coveragerc ./

# Default command for CI
CMD ["pytest", "tests/", "-v", "--cov=.", "--cov-report=xml", "--junitxml=test-results.xml"]

# ---------- Migration Stage ----------
# For running database migrations
FROM production AS migration

# Copy migration scripts
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Default command for migrations
CMD ["alembic", "upgrade", "head"]

# ---------- Debug Stage ----------
# For debugging with debugpy
FROM development AS debug

# Install debugpy
RUN pip install debugpy

# Expose debug port
EXPOSE 5678

# Command with debugger
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "-m", "uvicorn", "parking-api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------- Profiling Stage ----------
# For performance profiling
FROM production AS profiling

# Install profiling tools
RUN pip install py-spy memray

# Create profiling directory
RUN mkdir -p /app/profiles && chown appuser:appuser /app/profiles

# Command with profiling
CMD ["python", "-m", "memray", "run", "-o", "/app/profiles/profile.bin", "-m", "uvicorn", "parking-api.main:app", "--host", "0.0.0.0", "--port", "8000"]