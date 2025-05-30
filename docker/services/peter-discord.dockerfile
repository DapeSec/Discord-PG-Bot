# Peter Discord Handler Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements/discord-handlers.txt .
RUN pip install --no-cache-dir -r discord-handlers.txt

# Copy source code
COPY src/ ./src/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 6011

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:6011/health || exit 1

# Run with Gunicorn for production - Single worker for Discord bot to avoid conflicts
CMD ["gunicorn", "--bind", "0.0.0.0:6011", "--workers", "1", "--timeout", "120", "src.services.peter_discord.server:app"] 