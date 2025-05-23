#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with color
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if required commands exist
check_requirements() {
    log "Checking system requirements..."
    
    local required_commands=("docker" "docker-compose")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [ ${#missing_commands[@]} -ne 0 ]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        log_error "Please install Docker and Docker Compose before continuing."
        exit 1
    fi
    
    log "✓ All requirements satisfied"
}

# Create .env file from example if it doesn't exist
setup_env_file() {
    log "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f "docker/env.example" ]; then
            cp docker/env.example .env
            log "✓ Created .env file from example"
            log_warning "Please edit .env file with your actual Discord bot tokens and configuration"
            log_warning "Required variables to update:"
            log_warning "  - DISCORD_BOT_TOKEN_PETER"
            log_warning "  - DISCORD_BOT_TOKEN_BRIAN"
            log_warning "  - DISCORD_BOT_TOKEN_STEWIE"
            log_warning "  - DEFAULT_DISCORD_CHANNEL_ID"
            log_warning "  - Bot mention strings (will be auto-generated after first run)"
        else
            log_error "docker/env.example not found. Cannot create .env file."
            exit 1
        fi
    else
        log "✓ .env file already exists"
    fi
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    cd docker
    docker-compose build --no-cache
    cd ..
    log "✓ Docker images built successfully"
}

# Start services with proper order
start_services() {
    log "Starting services..."
    cd docker
    
    # Start MongoDB first
    log "Starting MongoDB..."
    docker-compose up -d mongodb
    
    # Wait for MongoDB to be ready
    log "Waiting for MongoDB to be ready..."
    sleep 10
    
    # Start orchestrator
    log "Starting orchestrator..."
    docker-compose up -d orchestrator
    
    # Wait for orchestrator to be ready
    log "Waiting for orchestrator to be ready..."
    sleep 20
    
    # Start all bot services
    log "Starting bot services..."
    docker-compose up -d peter brian stewie
    
    cd ..
    log "✓ All services started"
}

# Check service health
check_health() {
    log "Checking service health..."
    cd docker
    
    local services=("mongodb" "orchestrator" "peter" "brian" "stewie")
    local healthy_services=()
    local unhealthy_services=()
    
    sleep 30  # Give services time to start
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up (healthy)\|Up [0-9]"; then
            healthy_services+=("$service")
        else
            unhealthy_services+=("$service")
        fi
    done
    
    if [ ${#healthy_services[@]} -gt 0 ]; then
        log "✓ Healthy services: ${healthy_services[*]}"
    fi
    
    if [ ${#unhealthy_services[@]} -gt 0 ]; then
        log_warning "Unhealthy services: ${unhealthy_services[*]}"
        log_warning "Check logs with: docker-compose logs <service_name>"
    fi
    
    cd ..
}

# Show logs
show_logs() {
    log "Showing recent logs..."
    cd docker
    docker-compose logs --tail=50
    cd ..
}

# Main execution
main() {
    log "Starting Discord Bot System Setup"
    log "================================="
    
    check_requirements
    setup_env_file
    
    # Check if .env has been configured
    if grep -q "your_.*_token_here" .env 2>/dev/null; then
        log_error "Please configure your .env file with actual values before proceeding"
        log_error "Edit .env and replace placeholder values with your Discord bot tokens"
        exit 1
    fi
    
    build_images
    start_services
    check_health
    
    log "================================="
    log "Setup complete! 🎉"
    log ""
    log_info "Next steps:"
    log_info "1. Check service status: docker-compose ps"
    log_info "2. View logs: docker-compose logs -f <service_name>"
    log_info "3. Stop services: docker-compose down"
    log_info "4. Update bot mention strings in .env after bots are online"
    log ""
    log_info "Access points:"
    log_info "- Orchestrator: http://localhost:5003/health"
    log_info "- Peter Bot: http://localhost:5005/health"
    log_info "- Brian Bot: http://localhost:5002/health"
    log_info "- Stewie Bot: http://localhost:5004/health"
    log_info "- MongoDB: localhost:27017"
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "logs")
        show_logs
        ;;
    "health")
        check_health
        ;;
    "stop")
        log "Stopping all services..."
        cd docker && docker-compose down
        log "✓ All services stopped"
        ;;
    "restart")
        log "Restarting services..."
        cd docker && docker-compose restart
        log "✓ Services restarted"
        ;;
    *)
        echo "Usage: $0 [setup|logs|health|stop|restart]"
        exit 1
        ;;
esac 