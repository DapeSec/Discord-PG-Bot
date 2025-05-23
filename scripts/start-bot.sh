#!/bin/bash
set -e

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a URL is reachable
wait_for_url() {
    local url=$1
    local timeout=${2:-60}
    local start_time=$(date +%s)
    
    log "Waiting for $url to be available..."
    
    while true; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            log "✓ $url is available"
            break
        fi
        
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $timeout ]; then
            log "✗ Timeout waiting for $url (${timeout}s)"
            exit 1
        fi
        
        log "⏳ Waiting for $url... (${elapsed}s elapsed)"
        sleep 2
    done
}

# Function to check if a port is open
wait_for_port() {
    local host=$1
    local port=$2
    local timeout=${3:-60}
    local start_time=$(date +%s)
    
    log "Waiting for $host:$port to be available..."
    
    while true; do
        if nc -z "$host" "$port" 2>/dev/null; then
            log "✓ $host:$port is available"
            break
        fi
        
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $timeout ]; then
            log "✗ Timeout waiting for $host:$port (${timeout}s)"
            exit 1
        fi
        
        log "⏳ Waiting for $host:$port... (${elapsed}s elapsed)"
        sleep 2
    done
}

# Validate required environment variables
required_vars=("ORCHESTRATOR_API_URL" "MONGO_URI")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        log "ERROR: Required environment variable $var is not set"
        exit 1
    fi
done

# Wait for MongoDB
log "Checking MongoDB connectivity..."
wait_for_port mongodb 27017

# Wait for Orchestrator
log "Checking Orchestrator connectivity..."
orchestrator_host=$(echo "$ORCHESTRATOR_API_URL" | sed 's|http://||' | cut -d: -f1)
orchestrator_port=$(echo "$ORCHESTRATOR_API_URL" | sed 's|http://||' | cut -d: -f2 | cut -d/ -f1)
wait_for_port "$orchestrator_host" "$orchestrator_port"

# Wait for Orchestrator health endpoint
orchestrator_health_url=$(echo "$ORCHESTRATOR_API_URL" | sed 's|/orchestrate|/health|')
wait_for_url "$orchestrator_health_url"

# Additional wait for service stabilization
log "Waiting additional 10 seconds for service stabilization..."
sleep 10

log "All dependencies are ready. Starting bot service..."

# Execute the command passed as arguments
exec "$@" 