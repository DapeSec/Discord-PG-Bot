# RAG Crawler Service Dockerfile
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

# Copy requirements and install Python dependencies
COPY requirements/rag-crawler.txt .
RUN pip install --no-cache-dir -r rag-crawler.txt

# Copy source code
COPY src/ ./src/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 6009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:6009/health || exit 1

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:6009", "--workers", "1", "--timeout", "120", "src.services.rag_crawler.server:app"] 