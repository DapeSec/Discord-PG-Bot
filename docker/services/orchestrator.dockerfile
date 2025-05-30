FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/orchestrator.txt .
RUN pip install --no-cache-dir -r orchestrator.txt

# Copy source code
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 6008

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:6008/health || exit 1

# Run the service with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:6008", "--workers", "1", "--timeout", "120", "--preload", "src.services.orchestrator.server:app"] 