# Dockerfile for FreelanceMCP Web Dashboard
# Multi-stage build for optimal image size

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy all application source files
COPY freelance_server.py .
COPY search_gigs.py .
COPY freelance_api_clients.py .
COPY freelance_client.py .
COPY automation.py .
COPY ai_features.py .
COPY web_ui.py .
COPY core/        ./core/
COPY utils/       ./utils/
COPY database/    ./database/
COPY mcp_extensions/ ./mcp_extensions/
COPY dashboard/   ./dashboard/

# Runtime data directory (bids.json / status.json written here)
RUN mkdir -p /app/data

# Runtime flags
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_ENV=dev

# Dashboard server port
EXPOSE 8080

# Health check — verify the HTTP server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/status')"

# Start the web dashboard (serves UI + manages search_gigs.py subprocess)
CMD ["python", "web_ui.py"]

# Labels for metadata
LABEL maintainer="Freelance MCP Team"
LABEL version="2.0.0"
LABEL description="Freelance MCP Server - AI-powered freelance gig aggregator"
