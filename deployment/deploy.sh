#!/bin/bash

# Microservices Architecture Deployment Script
# Deploys the new microservices-based Discord Family Guy bot system

set -e  # Exit on any error

echo "🚀 Starting Microservices Architecture Deployment"
echo "=================================================="

# Configuration
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Pre-deployment checks
print_status "Running pre-deployment checks..."

# Check if Docker is installed and running
if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    print_error "Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Determine Docker Compose command
if command_exists docker-compose; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

print_success "Docker and Docker Compose are available"

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    print_warning ".env file not found. Creating template..."
    cat > "$ENV_FILE" << EOF
# Discord Bot Tokens
DISCORD_BOT_TOKEN_PETER=your_peter_token_here
DISCORD_BOT_TOKEN_BRIAN=your_brian_token_here
DISCORD_BOT_TOKEN_STEWIE=your_stewie_token_here

# Ollama Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-nemo

# MongoDB Configuration
MONGO_URI=mongodb://admin:adminpassword@mongodb:27017/?authSource=admin
MONGO_DB_NAME=discord_bot_conversations

# Redis/KeyDB Configuration
REDIS_URL=redis://keydb:6379

# Service Ports
LLM_SERVICE_PORT=5001
CONVERSATION_COORDINATOR_PORT=5002
QUALITY_CONTROL_PORT=5003
FINE_TUNING_PORT=5004
MESSAGE_ROUTER_PORT=5005
CHARACTER_CONFIG_PORT=5006
RAG_RETRIEVER_PORT=5007
RAG_CRAWLER_PORT=5009
PETER_DISCORD_PORT=5011
BRIAN_DISCORD_PORT=5012
STEWIE_DISCORD_PORT=5013

# Cache TTL Settings (in seconds)
LLM_RESPONSE_CACHE_TTL=3600
CHARACTER_CONFIG_CACHE_TTL=86400
ROUTING_CACHE_TTL=300

# Embeddings Model
EMBEDDINGS_MODEL_NAME=all-MiniLM-L6-v2
EOF
    print_warning "Please edit $ENV_FILE with your actual configuration before proceeding."
    read -p "Press Enter to continue after editing the .env file..."
fi

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Docker Compose file not found: $COMPOSE_FILE"
    exit 1
fi

print_success "Configuration files found"

# Function to wait for service health
wait_for_service() {
    local service_name=$1
    local health_url=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" >/dev/null 2>&1; then
            print_success "$service_name is healthy"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to become healthy after $((max_attempts * 2)) seconds"
    return 1
}

# Deployment phases
print_status "Phase 1: Stopping existing services..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" down --remove-orphans

print_status "Phase 2: Building new microservices..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" build --no-cache

print_status "Phase 3: Starting infrastructure services..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d mongodb keydb keydb-commander

# Wait for infrastructure
print_status "Waiting for infrastructure services to be ready..."
sleep 10

print_status "Phase 4: Starting core microservices..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d llm-service character-config rag-retriever rag-crawler

# Wait for core services
print_status "Waiting for core services to be ready..."
sleep 15

print_status "Phase 5: Starting message router..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d message-router

# Wait for message router
print_status "Waiting for message router to be ready..."
sleep 10

print_status "Phase 6: Starting Discord handlers..."
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d peter-discord brian-discord stewie-discord

print_success "All services started!"

# Health checks
print_status "Phase 7: Running health checks..."

# Define services and their health endpoints
declare -A HEALTH_ENDPOINTS=(
    ["MongoDB"]="http://localhost:27017"
    ["KeyDB"]="http://localhost:6379"
    ["LLM Service"]="http://localhost:5001/health"
    ["Character Config"]="http://localhost:5006/health"
    ["Message Router"]="http://localhost:5005/health"
    ["RAG Retriever"]="http://localhost:5007/health"
    ["RAG Crawler"]="http://localhost:5009/health"
    ["Peter Discord"]="http://localhost:5011/health"
    ["Brian Discord"]="http://localhost:5012/health"
    ["Stewie Discord"]="http://localhost:5013/health"
)

# Wait a bit for all services to fully start
sleep 20

# Check health of HTTP services
for service in "LLM Service" "Character Config" "Message Router" "RAG Retriever" "RAG Crawler" "Peter Discord" "Brian Discord" "Stewie Discord"; do
    if wait_for_service "$service" "${HEALTH_ENDPOINTS[$service]}"; then
        print_success "$service is running"
    else
        print_warning "$service may not be fully ready"
    fi
done

# Show running services
print_status "Current service status:"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" ps

# Show service logs (last 10 lines each)
print_status "Recent service logs:"
echo "===================="
for service in llm-service character-config message-router; do
    echo -e "\n${BLUE}=== $service ===${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs --tail=5 "$service" 2>/dev/null || echo "No logs available"
done

# Final instructions
echo ""
echo "🎉 Microservices Architecture Deployment Complete!"
echo "=================================================="
echo ""
echo "📋 Service URLs:"
echo "  • LLM Service:        http://localhost:5001"
echo "  • Character Config:   http://localhost:5006"
echo "  • Message Router:     http://localhost:5005"
echo "  • RAG Retriever:      http://localhost:5007"
echo "  • RAG Crawler:        http://localhost:5009"
echo "  • Peter Discord:      http://localhost:5011"
echo "  • Brian Discord:      http://localhost:5012"
echo "  • Stewie Discord:     http://localhost:5013"
echo "  • KeyDB Commander:    http://localhost:8081"
echo ""
echo "🧪 To test the architecture:"
echo "  python test_microservices_architecture.py"
echo ""
echo "📊 To view logs:"
echo "  $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f [service-name]"
echo ""
echo "🛑 To stop all services:"
echo "  $DOCKER_COMPOSE -f $COMPOSE_FILE down"
echo ""
echo "📈 To monitor service health:"
echo "  curl http://localhost:5005/services/health"
echo ""

# Optional: Run tests
read -p "Would you like to run the test suite now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Running microservices test suite..."
    if command_exists python3; then
        python3 test_microservices_architecture.py
    elif command_exists python; then
        python test_microservices_architecture.py
    else
        print_warning "Python not found. Please run the tests manually:"
        echo "  python test_microservices_architecture.py"
    fi
fi

print_success "Deployment script completed!" 