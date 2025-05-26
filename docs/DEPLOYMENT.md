# Deployment Guide - Discord Family Guy Bot

This guide covers deploying the Discord Family Guy Bot system in production environments.

## 🏗️ Architecture Summary

The system consists of 8 main services:
- **Discord Handler** (5004) - Manages Discord interactions
- **Orchestrator** (5003) - Central LLM brain and conversation coordination
- **RAG Retriever** (5005) - Real-time context retrieval
- **Peter Config** (5006) - Peter Griffin character configuration
- **Brian Config** (5007) - Brian Griffin character configuration  
- **Stewie Config** (5008) - Stewie Griffin character configuration
- **RAG Crawler** (5009) - Web scraping and vector database population
- **MongoDB** (27017) - Database
- **ChromaDB** (Shared Volume) - Vector store for RAG system
- **Ollama** (11434, External) - Local LLM service

## 🚀 Production Deployment

### Option 1: Docker Compose (Recommended for Small-Medium Scale)

#### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 2+ CPU cores

#### Steps

1. **Clone and Setup:**
   ```bash
   git clone <repository-url>
   cd discord-pg-bot
   cp .env.example .env
   ```

2. **Configure Environment:**
   ```env
   # Production settings - Discord Bot Tokens
   DISCORD_BOT_TOKEN_PETER=your_peter_token
   DISCORD_BOT_TOKEN_BRIAN=your_brian_token
   DISCORD_BOT_TOKEN_STEWIE=your_stewie_token
   DEFAULT_DISCORD_CHANNEL_ID=your_channel_id
   
   # Local LLM Configuration
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_MODEL=mistral-nemo
   
   # RAG System
   RAG_RETRIEVER_API_URL=http://rag-retriever:5005/retrieve
   RAG_CRAWLER_API_URL=http://rag-crawler:5009
   FANDOM_WIKI_START_URL=https://familyguy.fandom.com/wiki/Main_Page
   FANDOM_WIKI_MAX_PAGES=100
   
   # Enhanced Organic Conversations
   ENABLE_FOLLOW_UP_CONVERSATIONS=true
   FOLLOW_UP_DELAY_SECONDS=3.0
   MIN_TIME_BETWEEN_FOLLOW_UPS=30.0
   CONVERSATION_SILENCE_THRESHOLD_MINUTES=30
   MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS=10
   
   # Quality Control & Fine-Tuning
   FINE_TUNING_ENABLED=true
   QUALITY_CONTROL_ENABLED=true
   ADAPTIVE_QUALITY_CONTROL_ENABLED=true
   ADAPTIVE_CONTEXT_WEIGHTING_ENABLED=true
   ADAPTIVE_ANTI_HALLUCINATION_ENABLED=true
   
   # Adaptive Quality Thresholds
   COLD_START_THRESHOLD=30.0
   WARM_CONVERSATION_THRESHOLD=60.0
   HOT_CONVERSATION_THRESHOLD=75.0
   
   # Conversation State Boundaries
   CONVERSATION_HISTORY_COLD_LIMIT=6
   CONVERSATION_HISTORY_WARM_LIMIT=20
   
   # Legacy settings (fallbacks)
   OPTIMIZATION_THRESHOLD=0.7
   QUALITY_CONTROL_MIN_RATING=70.0
   
   # Database
   MONGO_URI=mongodb://admin:your_secure_password@mongodb:27017/?authSource=admin
   ```

3. **Deploy:**
   ```bash
   # Production deployment
   docker-compose -f docker/docker-compose.yml up -d
   
   # Check status
   docker-compose -f docker/docker-compose.yml ps
   ```

4. **Verify Deployment:**
   ```bash
   # Health checks
   curl http://localhost:5003/health  # Orchestrator
   curl http://localhost:5004/health  # Discord Handler
   curl http://localhost:5005/health  # RAG Retriever
   curl http://localhost:5006/health  # Peter Config
   curl http://localhost:5007/health  # Brian Config
   curl http://localhost:5008/health  # Stewie Config
   curl http://localhost:5009/health  # RAG Crawler
   
   # Verify Ollama is accessible
   curl http://localhost:11434/api/version
   
   # Check system status
   curl http://localhost:5003/fine_tuning_stats
   curl http://localhost:5003/quality_control_status
   curl http://localhost:5003/organic_conversation_status
   ```

### Option 2: Kubernetes (Recommended for Large Scale)

#### Prerequisites
- Kubernetes cluster 1.20+
- kubectl configured
- Helm 3.0+ (optional)

#### Kubernetes Manifests

1. **Namespace:**
   ```yaml
   # k8s/namespace.yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: discord-bot
   ```

2. **ConfigMap:**
   ```yaml
   # k8s/configmap.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: discord-bot-config
     namespace: discord-bot
   data:
     DISCORD_HANDLER_PORT: "5001"
     ORCHESTRATOR_PORT: "5003"
     PETER_BOT_PORT: "5005"
     BRIAN_BOT_PORT: "5006"
     STEWIE_BOT_PORT: "5007"
     MONGO_DB_NAME: "discord_bot_conversations"
   ```

3. **Secrets:**
   ```yaml
   # k8s/secrets.yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: discord-bot-secrets
     namespace: discord-bot
   type: Opaque
   data:
     OPENAI_API_KEY: <base64-encoded-key>
     DISCORD_BOT_TOKEN_PETER: <base64-encoded-token>
     DISCORD_BOT_TOKEN_BRIAN: <base64-encoded-token>
     DISCORD_BOT_TOKEN_STEWIE: <base64-encoded-token>
     MONGO_URI: <base64-encoded-uri>
   ```

4. **MongoDB Deployment:**
   ```yaml
   # k8s/mongodb.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: mongodb
     namespace: discord-bot
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: mongodb
     template:
       metadata:
         labels:
           app: mongodb
       spec:
         containers:
         - name: mongodb
           image: mongo:5.0
           ports:
           - containerPort: 27017
           env:
           - name: MONGO_INITDB_ROOT_USERNAME
             value: admin
           - name: MONGO_INITDB_ROOT_PASSWORD
             valueFrom:
               secretKeyRef:
                 name: discord-bot-secrets
                 key: MONGO_PASSWORD
           volumeMounts:
           - name: mongodb-storage
             mountPath: /data/db
         volumes:
         - name: mongodb-storage
           persistentVolumeClaim:
             claimName: mongodb-pvc
   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: mongodb
     namespace: discord-bot
   spec:
     selector:
       app: mongodb
     ports:
     - port: 27017
       targetPort: 27017
   ```

5. **Character API Deployments:**
   ```yaml
   # k8s/character-apis.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: peter-api
     namespace: discord-bot
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: peter-api
     template:
       metadata:
         labels:
           app: peter-api
       spec:
         containers:
         - name: peter-api
           image: discord-bot/peter:latest
           ports:
           - containerPort: 5005
           envFrom:
           - configMapRef:
               name: discord-bot-config
           - secretRef:
               name: discord-bot-secrets
           resources:
             requests:
               memory: "512Mi"
               cpu: "250m"
             limits:
               memory: "1Gi"
               cpu: "500m"
           livenessProbe:
             httpGet:
               path: /health
               port: 5005
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health
               port: 5005
             initialDelaySeconds: 5
             periodSeconds: 5
   ---
   apiVersion: v1
   kind: Service
   metadata:
     name: peter-api
     namespace: discord-bot
   spec:
     selector:
       app: peter-api
     ports:
     - port: 5005
       targetPort: 5005
   ```

6. **Deploy to Kubernetes:**
   ```bash
   # Apply all manifests
   kubectl apply -f k8s/
   
   # Check deployment status
   kubectl get pods -n discord-bot
   kubectl get services -n discord-bot
   
   # Check logs
   kubectl logs -f deployment/discord-handler -n discord-bot
   ```

### Option 3: Cloud Deployment (AWS/GCP/Azure)

#### AWS ECS with Fargate

1. **Create Task Definitions:**
   ```json
   {
     "family": "discord-handler",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "512",
     "memory": "1024",
     "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "discord-handler",
         "image": "your-registry/discord-handler:latest",
         "portMappings": [
           {
             "containerPort": 5001,
             "protocol": "tcp"
           }
         ],
         "environment": [
           {
             "name": "DISCORD_HANDLER_PORT",
             "value": "5001"
           }
         ],
         "secrets": [
           {
             "name": "DISCORD_BOT_TOKEN_PETER",
             "valueFrom": "arn:aws:secretsmanager:region:account:secret:discord-tokens"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/discord-bot",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

2. **Create ECS Service:**
   ```bash
   aws ecs create-service \
     --cluster discord-bot-cluster \
     --service-name discord-handler \
     --task-definition discord-handler:1 \
     --desired-count 2 \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
   ```

## 🔧 Configuration Management

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `OPENAI_API_KEY` | Yes | OpenAI API key | - |
| `DISCORD_BOT_TOKEN_PETER` | Yes | Peter bot token | - |
| `DISCORD_BOT_TOKEN_BRIAN` | Yes | Brian bot token | - |
| `DISCORD_BOT_TOKEN_STEWIE` | Yes | Stewie bot token | - |
| `DISCORD_HANDLER_PORT` | No | Discord Handler port | 5001 |
| `ORCHESTRATOR_PORT` | No | Orchestrator port | 5003 |
| `PETER_BOT_PORT` | No | Peter API port | 5005 |
| `BRIAN_BOT_PORT` | No | Brian API port | 5006 |
| `STEWIE_BOT_PORT` | No | Stewie API port | 5007 |
| `MONGO_URI` | Yes | MongoDB connection string | - |
| `MONGO_DB_NAME` | No | Database name | discord_bot_conversations |

### Security Configuration

1. **Discord Bot Permissions:**
   - Send Messages
   - Read Message History
   - Use Slash Commands
   - Embed Links
   - Attach Files

2. **Network Security:**
   ```yaml
   # Only expose necessary ports
   ports:
     - "5001:5001"  # Discord Handler only
   
   # Internal service communication
   networks:
     - bot_network
   ```

3. **Database Security:**
   ```env
   # Use strong passwords
   MONGO_URI=mongodb://admin:very_secure_password@mongodb:27017/?authSource=admin
   
   # Enable authentication
   MONGO_INITDB_ROOT_USERNAME=admin
   MONGO_INITDB_ROOT_PASSWORD=very_secure_password
   ```

## 📊 Monitoring & Observability

### Health Checks

All services provide health endpoints:
```bash
# Automated health check script
#!/bin/bash
services=("5001" "5003" "5005" "5006" "5007")
for port in "${services[@]}"; do
  if curl -f "http://localhost:$port/health" > /dev/null 2>&1; then
    echo "Service on port $port: HEALTHY"
  else
    echo "Service on port $port: UNHEALTHY"
  fi
done
```

### Logging

1. **Centralized Logging (ELK Stack):**
   ```yaml
   # docker-compose.override.yml
   version: '3.8'
   services:
     discord-handler:
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

2. **Log Aggregation:**
   ```bash
   # Fluentd configuration for log forwarding
   docker run -d \
     --name fluentd \
     -p 24224:24224 \
     -v /var/log:/fluentd/log \
     fluent/fluentd:latest
   ```

### Metrics Collection

1. **Prometheus Integration:**
   ```python
   # Add to each service
   from prometheus_client import Counter, Histogram, generate_latest
   
   REQUEST_COUNT = Counter('requests_total', 'Total requests')
   REQUEST_LATENCY = Histogram('request_duration_seconds', 'Request latency')
   
   @app.route('/metrics')
   def metrics():
       return generate_latest()
   ```

2. **Grafana Dashboard:**
   ```json
   {
     "dashboard": {
       "title": "Discord Bot Metrics",
       "panels": [
         {
           "title": "Request Rate",
           "type": "graph",
           "targets": [
             {
               "expr": "rate(requests_total[5m])"
             }
           ]
         }
       ]
     }
   }
   ```

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy Discord Bot

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest
    - name: Run tests
      run: pytest tests/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build Docker images
      run: |
        docker build -f docker/Dockerfile.discord_handler -t discord-bot/discord-handler:${{ github.sha }} .
        docker build -f docker/Dockerfile.orchestrator -t discord-bot/orchestrator:${{ github.sha }} .
        docker build -f docker/Dockerfile.bot -t discord-bot/character-api:${{ github.sha }} .
    
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push discord-bot/discord-handler:${{ github.sha }}
        docker push discord-bot/orchestrator:${{ github.sha }}
        docker push discord-bot/character-api:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to production
      run: |
        # Update Kubernetes deployment
        kubectl set image deployment/discord-handler discord-handler=discord-bot/discord-handler:${{ github.sha }}
        kubectl set image deployment/orchestrator orchestrator=discord-bot/orchestrator:${{ github.sha }}
        kubectl set image deployment/peter-api peter-api=discord-bot/character-api:${{ github.sha }}
        kubectl set image deployment/brian-api brian-api=discord-bot/character-api:${{ github.sha }}
        kubectl set image deployment/stewie-api stewie-api=discord-bot/character-api:${{ github.sha }}
```

## 🔧 Scaling Strategies

### Horizontal Scaling

1. **Character APIs:**
   ```yaml
   # Scale character APIs independently
   docker-compose -f docker/docker-compose.yml up -d --scale peter=3 --scale brian=2 --scale stewie=2
   ```

2. **Load Balancing:**
   ```nginx
   # nginx.conf
   upstream character_apis {
       server peter-1:5005;
       server peter-2:5005;
       server peter-3:5005;
   }
   
   server {
       listen 80;
       location /peter/ {
           proxy_pass http://character_apis;
       }
   }
   ```

### Vertical Scaling

1. **Resource Limits:**
   ```yaml
   services:
     orchestrator:
       deploy:
         resources:
           limits:
             cpus: '2.0'
             memory: 4G
           reservations:
             cpus: '1.0'
             memory: 2G
   ```

2. **Gunicorn Workers:**
   ```bash
   # Increase workers based on CPU cores
   gunicorn --workers $((2 * $(nproc) + 1)) --preload app:app
   ```

## 🛡️ Security Best Practices

### Container Security

1. **Non-root User:**
   ```dockerfile
   RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
   USER appuser
   ```

2. **Minimal Base Images:**
   ```dockerfile
   FROM python:3.9-slim  # Instead of full python image
   ```

3. **Security Scanning:**
   ```bash
   # Scan images for vulnerabilities
   docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
     aquasec/trivy image discord-bot/orchestrator:latest
   ```

### Network Security

1. **Internal Networks:**
   ```yaml
   networks:
     bot_network:
       driver: bridge
       internal: true  # No external access
   ```

2. **Firewall Rules:**
   ```bash
   # Only allow necessary ports
   ufw allow 5001/tcp  # Discord Handler only
   ufw deny 5003,5005,5006,5007/tcp  # Internal services
   ```

## 🔄 Backup & Recovery

### Database Backup

1. **Automated Backups:**
   ```bash
   #!/bin/bash
   # backup.sh
   DATE=$(date +%Y%m%d_%H%M%S)
   docker exec mongodb mongodump --authenticationDatabase admin \
     -u admin -p adminpassword --out /backup/mongodb_$DATE
   
   # Upload to S3
   aws s3 cp /backup/mongodb_$DATE s3://discord-bot-backups/
   ```

2. **Backup Schedule:**
   ```cron
   # Crontab entry
   0 2 * * * /path/to/backup.sh
   ```

### Disaster Recovery

1. **Recovery Procedure:**
   ```bash
   # Restore from backup
   docker exec mongodb mongorestore --authenticationDatabase admin \
     -u admin -p adminpassword /backup/mongodb_20231201_020000
   ```

2. **High Availability:**
   ```yaml
   # MongoDB replica set
   services:
     mongodb-primary:
       image: mongo:5.0
       command: mongod --replSet rs0
     mongodb-secondary:
       image: mongo:5.0
       command: mongod --replSet rs0
   ```

## 📋 Maintenance

### Regular Tasks

1. **Log Rotation:**
   ```bash
   # Rotate Docker logs
   docker system prune -f
   docker volume prune -f
   ```

2. **Health Monitoring:**
   ```bash
   # Check service health
   docker-compose -f docker/docker-compose.yml ps
   curl -f http://localhost:5001/health || echo "Discord Handler unhealthy"
   ```

3. **Performance Monitoring:**
   ```bash
   # Monitor resource usage
   docker stats --no-stream
   ```

### Updates

1. **Rolling Updates:**
   ```bash
   # Update one service at a time
   docker-compose -f docker/docker-compose.yml up -d --no-deps orchestrator
   docker-compose -f docker/docker-compose.yml up -d --no-deps peter
   ```

2. **Database Migrations:**
   ```python
   # migration_script.py
   from pymongo import MongoClient
   
   def migrate_v1_to_v2():
       client = MongoClient(MONGO_URI)
       db = client[MONGO_DB_NAME]
       # Perform migration
   ```

## 🚨 Troubleshooting

### Common Issues

1. **Service Won't Start:**
   ```bash
   # Check logs
   docker-compose -f docker/docker-compose.yml logs service-name
   
   # Check resource usage
   docker system df
   free -h
   ```

2. **High Memory Usage:**
   ```bash
   # Monitor memory per service
   docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
   
   # Restart services if needed
   docker-compose -f docker/docker-compose.yml restart
   ```

3. **Database Connection Issues:**
   ```bash
   # Test MongoDB connection
   docker exec mongodb mongosh --authenticationDatabase admin \
     -u admin -p adminpassword --eval "db.adminCommand('ping')"
   ```

### Performance Issues

1. **Slow Response Times:**
   - Check OpenAI API rate limits
   - Monitor database query performance
   - Increase Gunicorn workers
   - Scale character APIs horizontally

2. **High CPU Usage:**
   - Profile application performance
   - Optimize database queries
   - Implement response caching
   - Scale vertically or horizontally

---

This deployment guide provides comprehensive instructions for deploying the Discord Family Guy Bot in various production environments. Choose the deployment option that best fits your scale and infrastructure requirements. 