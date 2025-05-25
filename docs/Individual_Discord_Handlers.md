# Individual Discord Handlers Architecture

## Overview

The Discord bot system has been refactored from a single `discord-handler` service managing all three Discord bots to **individual Discord handler services** - one for each character (Peter, Brian, and Stewie).

## Architecture Changes

### Before (Single Handler)
```
┌─────────────────────────────────────┐
│        discord-handler              │
│  ┌─────────┬─────────┬─────────┐    │
│  │ Peter   │ Brian   │ Stewie  │    │
│  │ Client  │ Client  │ Client  │    │
│  └─────────┴─────────┴─────────┘    │
│         (Threading conflicts)       │
└─────────────────────────────────────┘
```

### After (Individual Handlers)
```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│peter-discord│  │brian-discord│  │stewie-discord│
│             │  │             │  │             │
│ Peter Client│  │ Brian Client│  │Stewie Client│
│             │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Benefits

### 🔧 **Eliminates Threading Conflicts**
- Each Discord client runs in its own isolated process
- No more race conditions between multiple Discord clients
- No more "cannot unpack non-iterable Client object" errors

### 🛡️ **Better Fault Tolerance**
- If one bot fails, the others continue working
- Independent health checks per bot
- Isolated error handling

### 🔍 **Easier Debugging**
- Separate logs for each Discord bot
- Clear service boundaries
- Simpler troubleshooting

### 📈 **Better Scalability**
- Can scale individual bots independently
- Resource allocation per bot
- Independent deployment cycles

### 🎯 **Simpler Architecture**
- One Discord client per service
- Cleaner code organization
- Reduced complexity

## Services

### Peter Discord Handler (`peter-discord`)
- **Port**: 5011
- **Container**: `peter-discord`
- **Dockerfile**: `docker/Dockerfile.peter_discord`
- **Service**: `src/app/discord_handler/peter_discord_service.py`

### Brian Discord Handler (`brian-discord`)
- **Port**: 5012
- **Container**: `brian-discord`
- **Dockerfile**: `docker/Dockerfile.brian_discord`
- **Service**: `src/app/discord_handler/brian_discord_service.py`

### Stewie Discord Handler (`stewie-discord`)
- **Port**: 5013
- **Container**: `stewie-discord`
- **Dockerfile**: `docker/Dockerfile.stewie_discord`
- **Service**: `src/app/discord_handler/stewie_discord_service.py`

## API Endpoints

Each Discord handler provides the same API:

### Health Check
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy|degraded|unhealthy",
  "service": "PeterDiscordHandler",
  "timestamp": "2024-01-01T12:00:00",
  "discord_client": {
    "logged_in": true,
    "discord_ready": true,
    "custom_ready": true,
    "status": "ready",
    "user_id": 123456789,
    "username": "Peter Griffin"
  }
}
```

### Send Message
```bash
POST /send_message
```

**Request:**
```json
{
  "channel_id": "123456789",
  "message_content": "Holy crap! This is working!"
}
```

**Response:**
```json
{
  "status": "Message sent successfully"
}
```

### Bot Information
```bash
GET /bot_info
```

**Response:**
```json
{
  "id": 123456789,
  "username": "Peter Griffin",
  "mention": "<@123456789>",
  "ready": true
}
```

## Environment Variables

### New Variables (Required)
```env
# Individual Discord Handler URLs
PETER_DISCORD_URL=http://peter-discord:5011/send_message
BRIAN_DISCORD_URL=http://brian-discord:5012/send_message
STEWIE_DISCORD_URL=http://stewie-discord:5013/send_message

# Discord Bot Tokens (unchanged)
DISCORD_BOT_TOKEN_PETER=your_peter_token
DISCORD_BOT_TOKEN_BRIAN=your_brian_token
DISCORD_BOT_TOKEN_STEWIE=your_stewie_token

# Bot Mention Strings (unchanged)
PETER_BOT_MENTION_STRING=<@peter_bot_id>
BRIAN_BOT_MENTION_STRING=<@brian_bot_id>
STEWIE_BOT_MENTION_STRING=<@stewie_bot_id>
```

### Removed Variables
```env
# These are no longer needed
DISCORD_HANDLER_URL=...
PETER_BOT_DISCORD_SEND_API_URL=...
BRIAN_BOT_DISCORD_SEND_API_URL=...
STEWIE_BOT_DISCORD_SEND_API_URL=...
```

## Migration Guide

### Automatic Migration
Run the migration script to automatically update your configuration:

```bash
python scripts/migrate_to_individual_discord_handlers.py
```

### Manual Migration

1. **Stop existing services:**
   ```bash
   docker-compose down
   ```

2. **Update your `.env` file:**
   ```bash
   # Remove old variables
   # DISCORD_HANDLER_URL=...
   # PETER_BOT_DISCORD_SEND_API_URL=...
   # BRIAN_BOT_DISCORD_SEND_API_URL=...
   # STEWIE_BOT_DISCORD_SEND_API_URL=...

   # Add new variables
   PETER_DISCORD_URL=http://peter-discord:5011/send_message
   BRIAN_DISCORD_URL=http://brian-discord:5012/send_message
   STEWIE_DISCORD_URL=http://stewie-discord:5013/send_message
   ```

3. **Rebuild and start:**
   ```bash
   docker-compose up --build
   ```

4. **Verify services:**
   ```bash
   curl http://localhost:5011/health  # Peter Discord
   curl http://localhost:5012/health  # Brian Discord
   curl http://localhost:5013/health  # Stewie Discord
   curl http://localhost:5003/health  # Orchestrator
   ```

## Docker Compose Changes

The `docker-compose.yml` now includes three separate Discord handler services:

```yaml
services:
  peter-discord:
    build:
      dockerfile: docker/Dockerfile.peter_discord
    ports:
      - "5011:5011"
    environment:
      - PETER_DISCORD_PORT=5011
      - DISCORD_BOT_TOKEN_PETER=${DISCORD_BOT_TOKEN_PETER}

  brian-discord:
    build:
      dockerfile: docker/Dockerfile.brian_discord
    ports:
      - "5012:5012"
    environment:
      - BRIAN_DISCORD_PORT=5012
      - DISCORD_BOT_TOKEN_BRIAN=${DISCORD_BOT_TOKEN_BRIAN}

  stewie-discord:
    build:
      dockerfile: docker/Dockerfile.stewie_discord
    ports:
      - "5013:5013"
    environment:
      - STEWIE_DISCORD_PORT=5013
      - DISCORD_BOT_TOKEN_STEWIE=${DISCORD_BOT_TOKEN_STEWIE}
```

## Orchestrator Integration

The orchestrator has been updated to communicate with individual Discord handlers:

```python
BOT_CONFIGS = {
    "Peter": {
        "discord_send_api": "http://peter-discord:5011/send_message",
        "mention": PETER_BOT_MENTION_STRING
    },
    "Brian": {
        "discord_send_api": "http://brian-discord:5012/send_message",
        "mention": BRIAN_BOT_MENTION_STRING
    },
    "Stewie": {
        "discord_send_api": "http://stewie-discord:5013/send_message",
        "mention": STEWIE_BOT_MENTION_STRING
    }
}
```

## Monitoring

### Health Checks
Each service has independent health checks:

```bash
# Check all Discord handlers
for port in 5011 5012 5013; do
  echo "Checking port $port..."
  curl -s http://localhost:$port/health | jq '.status'
done
```

### Logs
View logs for individual services:

```bash
# Peter Discord logs
docker logs peter-discord

# Brian Discord logs
docker logs brian-discord

# Stewie Discord logs
docker logs stewie-discord
```

## Troubleshooting

### Common Issues

1. **Service not starting:**
   ```bash
   # Check logs
   docker logs peter-discord
   
   # Check if token is set
   docker exec peter-discord env | grep DISCORD_BOT_TOKEN_PETER
   ```

2. **Health check failing:**
   ```bash
   # Check Discord client status
   curl http://localhost:5011/health | jq '.discord_client'
   ```

3. **Message sending fails:**
   ```bash
   # Test send message endpoint
   curl -X POST http://localhost:5011/send_message \
     -H "Content-Type: application/json" \
     -d '{"channel_id":"123456789","message_content":"Test"}'
   ```

### Recovery Steps

1. **Restart individual service:**
   ```bash
   docker-compose restart peter-discord
   ```

2. **Rebuild specific service:**
   ```bash
   docker-compose up --build peter-discord
   ```

3. **Check orchestrator connectivity:**
   ```bash
   docker exec orchestrator curl http://peter-discord:5011/health
   ```

## Performance Considerations

- **Memory**: Each Discord handler uses ~50-100MB RAM
- **CPU**: Minimal CPU usage per handler
- **Network**: Internal Docker network communication
- **Startup**: Services start independently, improving overall startup time

## Future Enhancements

- **Load Balancing**: Can add multiple instances per bot
- **Circuit Breakers**: Implement circuit breaker pattern for resilience
- **Metrics**: Add Prometheus metrics per Discord handler
- **Auto-scaling**: Scale individual handlers based on load 