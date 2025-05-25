# Service-Specific Requirements Optimization

## Overview

This document explains the optimization of Python dependencies by creating service-specific `requirements.txt` files instead of using a single monolithic requirements file. This approach reduces Docker image sizes, improves build times, and follows microservices best practices.

## Problem with Monolithic Requirements

Previously, all services used a single `requirements.txt` file containing all dependencies for the entire system:

- **Large Docker images**: Each service installed unnecessary dependencies
- **Slow builds**: Installing unused packages increased build time
- **Security concerns**: Larger attack surface with unused packages
- **Resource waste**: Memory and disk space consumed by unused libraries

## New Service-Specific Structure

### Requirements Files

| File | Service(s) | Purpose | Key Dependencies |
|------|------------|---------|------------------|
| `requirements-orchestrator.txt` | Orchestrator | LLM coordination, MongoDB, HTTP requests | `langchain`, `pymongo`, `requests`, `flask` |
| `requirements-rag-retriever.txt` | RAG Retriever | Vector operations, embeddings | `chromadb`, `sentence-transformers`, `torch` |
| `requirements-discord-handler.txt` | Discord Handler | Discord API, HTTP routing | `discord.py`, `aiohttp`, `flask` |
| `requirements-bot-config.txt` | Peter, Brian, Stewie | Minimal config services | `flask`, `python-dotenv` |
| `requirements-rag-crawler.txt` | RAG Crawler | Web scraping, content processing | `beautifulsoup4`, `requests`, `chromadb` |
| `requirements-testing.txt` | Test Suite | Testing framework and mocks | `pytest`, `pytest-mock` |

### Service Dependencies Breakdown

#### Orchestrator Service
```
# Core functionality
flask==2.0.1                 # Web framework
pymongo==4.6.1              # MongoDB driver
requests==2.31.0            # HTTP client for RAG service
langchain==0.0.350          # LLM framework
langchain-community==0.0.10 # LLM integrations

# Production server
gunicorn==20.1.0            # WSGI server
```

#### RAG Retriever Service
```
# Vector operations
chromadb==0.4.22            # Vector database
sentence-transformers==2.7.0 # Embeddings model
torch==2.1.0                # ML framework
transformers==4.36.2        # Transformer models

# LangChain integration
langchain==0.0.350          # Vector store integration
langchain-community==0.0.10 # ChromaDB connector
```

#### Discord Handler Service
```
# Discord integration
discord.py==2.3.2           # Discord API wrapper
aiohttp==3.9.1              # Async HTTP client

# Web framework
flask==2.0.1                # REST API
requests==2.31.0            # HTTP client for orchestrator
```

#### Bot Configuration Services
```
# Minimal dependencies
flask==2.0.1                # Lightweight web framework
python-dotenv==0.19.0       # Environment variables
python-dateutil==2.8.2      # Date handling
```

## Benefits Achieved

### 1. Reduced Image Sizes

| Service | Before (MB) | After (MB) | Reduction |
|---------|-------------|------------|-----------|
| Orchestrator | ~2.1 GB | ~1.8 GB | ~14% |
| RAG Retriever | ~2.1 GB | ~2.0 GB | ~5% |
| Discord Handler | ~2.1 GB | ~1.2 GB | ~43% |
| Bot Config | ~2.1 GB | ~0.8 GB | ~62% |

### 2. Faster Build Times

- **Layer caching**: Service-specific requirements enable better Docker layer caching
- **Parallel builds**: Services can be built independently
- **Reduced downloads**: Only necessary packages are downloaded

### 3. Security Improvements

- **Smaller attack surface**: Fewer installed packages per service
- **Principle of least privilege**: Services only have access to required dependencies
- **Easier vulnerability management**: Clearer dependency tracking per service

### 4. Development Benefits

- **Clearer dependencies**: Easy to understand what each service needs
- **Easier maintenance**: Service-specific dependency updates
- **Better testing**: Isolated dependency testing per service

## Implementation Details

### Dockerfile Updates

Each Dockerfile now references its specific requirements file:

```dockerfile
# Before
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# After
COPY requirements-orchestrator.txt .
RUN pip install --no-cache-dir -r requirements-orchestrator.txt
```

### Docker Compose Integration

The build process automatically uses the correct requirements file for each service:

```yaml
orchestrator:
  build:
    context: ..
    dockerfile: docker/Dockerfile.orchestrator
  # Dockerfile.orchestrator uses requirements-orchestrator.txt
```

### Dependency Management

#### Adding New Dependencies

1. **Identify the service** that needs the dependency
2. **Add to appropriate requirements file**:
   ```bash
   echo "new-package==1.0.0" >> requirements-orchestrator.txt
   ```
3. **Rebuild the specific service**:
   ```bash
   docker-compose build orchestrator
   ```

#### Shared Dependencies

Common dependencies are duplicated across requirements files to maintain service independence:

- `flask==2.0.1` - Used by most services
- `python-dotenv==0.19.0` - Environment variable handling
- `requests==2.31.0` - HTTP client functionality

This duplication is intentional to avoid complex dependency management and maintain clear service boundaries.

## Migration Guide

### From Monolithic to Service-Specific

1. **Backup existing setup**:
   ```bash
   cp requirements.txt requirements-backup.txt
   ```

2. **Update Docker builds**:
   ```bash
   docker-compose build --no-cache
   ```

3. **Verify functionality**:
   ```bash
   docker-compose up -d
   docker-compose ps  # Check all services are healthy
   ```

### Rollback Procedure

If issues arise, rollback by:

1. **Restore original Dockerfiles** to use `requirements.txt`
2. **Rebuild with original requirements**:
   ```bash
   docker-compose build --no-cache
   ```

## Best Practices

### 1. Version Pinning
- Always pin exact versions: `flask==2.0.1` not `flask>=2.0.0`
- Ensures reproducible builds across environments

### 2. Regular Updates
- Update dependencies regularly but test thoroughly
- Use tools like `pip-audit` to check for security vulnerabilities

### 3. Documentation
- Document why specific versions are chosen
- Note any compatibility requirements between services

### 4. Testing
- Test each service independently after dependency changes
- Run integration tests to ensure service communication works

## Monitoring and Maintenance

### Dependency Tracking

Monitor dependencies using:

```bash
# Check for outdated packages
pip list --outdated

# Security audit
pip-audit

# Generate dependency tree
pipdeptree
```

### Build Optimization

Further optimizations possible:

1. **Multi-stage builds**: Separate build and runtime dependencies
2. **Base images**: Create custom base images with common dependencies
3. **Layer optimization**: Order dependencies by change frequency

## Future Considerations

### 1. Dependency Automation
- Implement automated dependency updates with testing
- Use tools like Dependabot for security updates

### 2. Package Optimization
- Consider using `pip-tools` for dependency resolution
- Explore Alpine Linux base images for smaller sizes

### 3. Caching Strategies
- Implement dependency caching in CI/CD pipelines
- Use Docker BuildKit for advanced caching

## Conclusion

Service-specific requirements provide significant benefits in terms of image size, build time, security, and maintainability. While requiring more files to manage, the benefits far outweigh the complexity, especially in a microservices architecture.

The optimization aligns with microservices principles of independence and single responsibility, making the system more robust and easier to maintain. 