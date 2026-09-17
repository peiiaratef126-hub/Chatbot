# ==============================================================================
# Multi-Stage Dockerfile for Hugging Face Spaces & Render Deployment
# Default Exposed Port: 7860 (Hugging Face Spaces standard)
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build essentials
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.11-slim AS runner

# Create non-root user with UID 1000 for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder --chown=user:user /root/.local /home/user/.local

# Copy application source code and sample data
COPY --chown=user:user app /app/app
COPY --chown=user:user scripts /app/scripts

USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
