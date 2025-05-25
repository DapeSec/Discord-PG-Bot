#!/bin/bash

# Discord Family Guy Bot - Deployment Script for New Local Mistral Architecture
# This script helps migrate from the old OpenAI architecture to the new local setup

set -e  # Exit on any error

echo "🚀 Discord Family Guy Bot - Local Mistral Deployment"
echo "================================================="

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

# Check prerequisites
print_status "Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Docker and Docker Compose are installed"

# Check Ollama
print_status "Checking Ollama connection..."
if curl -s http://localhost:11434/api/version &> /dev/null; then
    print_success "Ollama is running"
    
    # Check for mistral-nemo model
    if ollama list | grep -q "mistral-nemo"; then
        print_success "mistral-nemo model is available"
    else
        print_warning "mistral-nemo model not found"
        echo "Pulling mistral-nemo model (this may take a while)..."
        ollama pull mistral-nemo
        print_success "mistral-nemo model downloaded"
    fi
else
    print_error "Ollama is not running or not accessible at localhost:11434"
    echo "Please ensure Ollama is running with: ollama serve"
    exit 1
fi

# Check for environment file
if [ ! -f ".env" ]; then
    print_warning ".env file not found"
    
    if [ -f ".env.example" ]; then
        print_status "Creating .env from template..."
        cp .env.example .env
        print_warning "Please edit .env file with your Discord bot tokens before continuing"
        print_status "Required variables to set:"
        echo "  - DISCORD_BOT_TOKEN_PETER"
        echo "  - DISCORD_BOT_TOKEN_BRIAN"
        echo "  - DISCORD_BOT_TOKEN_STEWIE"
        echo "  - DEFAULT_DISCORD_CHANNEL_ID"
        echo ""
        read -p "Press Enter when you've configured the .env file..."
    else
        print_error ".env.example template not found. Please create .env manually."
        exit 1
    fi
else
    print_success ".env file found"
fi

# Validate environment file
print_status "Validating environment configuration..."
source .env

required_vars=(
    "DISCORD_BOT_TOKEN_PETER"
    "DISCORD_BOT_TOKEN_BRIAN"
    "DISCORD_BOT_TOKEN_STEWIE"
    "DEFAULT_DISCORD_CHANNEL_ID"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] || [ "${!var}" = "your_${var,,}_here" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo "Please update your .env file and run this script again."
    exit 1
fi

print_success "Environment configuration is valid"

# Clean up old containers if they exist
print_status "Cleaning up any existing containers..."
docker-compose down --volumes 2>/dev/null || true

# Build and start services
print_status "Building Docker images..."
docker-compose build --no-cache

print_status "Starting services..."
docker-compose up -d

# Wait for services to start
print_status "Waiting for services to start..."
sleep 10

# Check service health
print_status "Checking service health..."
services=("orchestrator:5003" "peter:5005" "brian:5006" "stewie:5007")
all_healthy=true

for service in "${services[@]}"; do
    name="${service%%:*}"
    port="${service##*:}"
    
    if curl -s -f http://localhost:${port}/health > /dev/null; then
        print_success "${name} service is healthy"
    else
        print_error "${name} service is not responding"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    print_success "All services are running successfully!"
    echo ""
    echo "🎉 Deployment Complete!"
    echo "===================="
    echo ""
    echo "Services are running at:"
    echo "  📊 Orchestrator: http://localhost:5003/health"
    echo "  👨 Peter Config: http://localhost:5005/health"
    echo "  🐕 Brian Config: http://localhost:5006/health"
    echo "  👶 Stewie Config: http://localhost:5007/health"
    echo ""
    echo "Management endpoints:"
    echo "  📈 Fine-tuning stats: http://localhost:5003/fine_tuning_stats"
    echo "  🎛️ Quality control: http://localhost:5003/quality_control_status"
    echo "  📊 Performance reports: http://localhost:5003/optimization_report"
    echo ""
    echo "To monitor logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
    echo ""
    print_success "Your Family Guy bots are ready to chat! 🎭"
else
    print_error "Some services failed to start. Check logs with: docker-compose logs"
    echo ""
    echo "Common troubleshooting steps:"
    echo "1. Ensure Ollama is running: ollama serve"
    echo "2. Check if mistral-nemo model is available: ollama list"
    echo "3. Verify your .env file has correct Discord tokens"
    echo "4. Check Docker logs: docker-compose logs -f"
    exit 1
fi 