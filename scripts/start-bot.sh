#!/bin/bash
# scripts/start-bot.sh

# This script now expects the Python module path as the first argument (e.g., src.app.bots.peter_bot)
# and the bot's specific dependencies as a comma-separated string for the second argument (e.g., "mongodb:27017,orchestrator:5003")

set -e # Exit immediately if a command exits with a non-zero status.

PYTHON_MODULE=$1
SERVICE_DEPENDENCIES=$2 # Comma-separated list of host:port dependencies

if [ -z "$PYTHON_MODULE" ] || [ -z "$SERVICE_DEPENDENCIES" ]; then
  echo "Usage: $0 <python_module_path> <service_dependencies>"
  echo "Example: $0 src.app.bots.peter_bot mongodb:27017,orchestrator:5003"
  exit 1
fi

# --- Dependency Check Function ---
wait_for_service() {
  local HOST_PORT=$1
  local HOST=$(echo $HOST_PORT | cut -d: -f1)
  local PORT=$(echo $HOST_PORT | cut -d: -f2)
  local RETRIES=30 # ~5 minutes with 10s sleep
  local COUNT=0

  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Waiting for $HOST:$PORT to be available..."
  until nc -z -w5 $HOST $PORT; do # -w5 for 5 second timeout per attempt
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $RETRIES ]; then
      echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ Service $HOST:$PORT did not become available after $RETRIES attempts. Exiting."
      exit 1
    fi
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Still waiting for $HOST:$PORT... (attempt $COUNT/$RETRIES)"
    sleep 10
  done
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ $HOST:$PORT is available"
}

# --- Check and Wait for All Dependencies ---
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Checking service dependencies: $SERVICE_DEPENDENCIES"
IFS=',' read -ra ADDR <<< "$SERVICE_DEPENDENCIES"
for SERVICE_HOST_PORT in "${ADDR[@]}"; do
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Checking dependency: $SERVICE_HOST_PORT"
  wait_for_service "$SERVICE_HOST_PORT"

  # Special handling for orchestrator to wait for its /health endpoint
  if [[ "$SERVICE_HOST_PORT" == *"orchestrator"* ]]; then
    ORCH_HEALTH_URL="http://${SERVICE_HOST_PORT}/health"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] Waiting for $ORCH_HEALTH_URL to be available..."
    # Use curl with retry and timeout for the health check
    RETRIES=30 # ~5 minutes with 10s sleep
    COUNT=0
    until curl --output /dev/null --silent --head --fail -m 5 "$ORCH_HEALTH_URL"; do
        COUNT=$((COUNT + 1))
        if [ $COUNT -ge $RETRIES ]; then
          echo "[$(date +'%Y-%m-%d %H:%M:%S')] ❌ Orchestrator health check at $ORCH_HEALTH_URL failed after $RETRIES attempts. Exiting."
          exit 1
        fi
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] Still waiting for $ORCH_HEALTH_URL... (attempt $COUNT/$RETRIES)"
        sleep 10
    done
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ✓ $ORCH_HEALTH_URL is available"
  fi
done

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Waiting additional 10 seconds for service stabilization..."
sleep 10

echo "[$(date +'%Y-%m-%d %H:%M:%S')] All dependencies are ready. Starting bot service for $PYTHON_MODULE..."

# Execute the Python module directly. Python's -m flag runs library module as a script.
# This will invoke the if __name__ == '__main__' block in the specified bot's Python file.
exec python -u -m "$PYTHON_MODULE" 