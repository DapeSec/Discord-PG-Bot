# Discord Family Guy Bot - Updated Docker Architecture

## 🚀 **Architecture Overview**

The Docker setup has been **completely redesigned** for the new local Mistral architecture:

### **Key Changes from Previous Version:**

✅ **Local Mistral LLM** (mistral-nemo) instead of external OpenAI APIs  
✅ **Centralized LLM Processing** in orchestrator service  
✅ **Lightweight Character Services** (config/metadata only)  
✅ **Enhanced RAG System** with Family Guy wiki integration  
✅ **Supervised Fine-Tuning System** with quality control  
✅ **Enhanced Organic Conversation Coordination** with follow-up responses  

## 🐳 **Service Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Discord        │    │   Orchestrator   │    │   MongoDB       │
│  Handler        │◄──►│   (LLM Brain)    │◄──►│   Database      │
│  Port: 5004     │    │   Port: 5003     │    │   Port: 27017   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
            ┌───────▼──┐ ┌─────▼───┐ ┌────▼────┐
            │  Peter   │ │  Brian  │ │ Stewie  │
            │ Config   │ │ Config  │ │ Config  │
            │ :5006    │ │ :5007   │ │ :5008   │
            └──────────┘ └─────────┘ └─────────┘

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  RAG Retriever  │    │   RAG Crawler    │    │   ChromaDB      │
│  (Real-time)    │◄──►│   (Batch)        │◄──►│  Vector Store   │
│  Port: 5005     │    │   Port: 5009     │    │  (Shared Vol)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        ▲                        ▲
        │                        │
        └────────────────────────┼─────────── Orchestrator
                                 │
                        ┌────────▼────────┐
                        │  Family Guy     │
                        │  Fandom Wiki    │
                        │  (External)     │
                        └─────────────────┘
```

## 🏃‍♂️ **Quick Start**

### **Prerequisites:**
1. **Docker & Docker Compose** installed
2. **Ollama running locally** with mistral-nemo model:
   ```bash
   ollama serve
   ollama pull mistral-nemo
   ```
3. **Discord bot tokens** for Peter, Brian, and Stewie

### **Setup:**

1. **Clone and navigate to the `docker` directory:**
   ```bash
   git clone <your-repo>
   cd discord-pg-bot/docker
   ```

2. **Ensure `.env.example` exists:**
   - The deployment script `deploy.sh` (and good practice) relies on a `.env.example` file in this `docker/` directory to create your `.env` file.
   - If it doesn't exist, please create `docker/.env.example`. You can use the "Environment Configuration" section below as a template for its content.

3. **Run the deployment script:**
   - This script will check prerequisites, help you set up your `.env` file, build images, and start the services.
   ```bash
   # Make it executable if needed (on Linux/macOS)
   # chmod +x deploy.sh 
   ./deploy.sh
   ```
   - The script will guide you if your `.env` file is missing or needs configuration.

4. **After `deploy.sh` completes successfully, check health (optional, as script does this):**
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

## ⚙️ **Environment Configuration**

Create a `.env` file with these key settings:

```bash
# === REQUIRED DISCORD TOKENS ===
DISCORD_BOT_TOKEN_PETER=your_peter_token
DISCORD_BOT_TOKEN_BRIAN=your_brian_token  
DISCORD_BOT_TOKEN_STEWIE=your_stewie_token
DEFAULT_DISCORD_CHANNEL_ID=your_channel_id

# === LOCAL MISTRAL CONFIGURATION ===
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-nemo

# === FINE-TUNING SYSTEM ===
FINE_TUNING_ENABLED=true
QUALITY_CONTROL_ENABLED=true
OPTIMIZATION_THRESHOLD=0.7

# === RAG SYSTEM ===
FANDOM_WIKI_START_URL=https://familyguy.fandom.com/wiki/Main_Page
FANDOM_WIKI_MAX_PAGES=100

# === ENHANCED ORGANIC CONVERSATIONS ===
ENABLE_FOLLOW_UP_CONVERSATIONS=true
FOLLOW_UP_DELAY_SECONDS=3.0
MIN_TIME_BETWEEN_FOLLOW_UPS=30.0
CONVERSATION_SILENCE_THRESHOLD_MINUTES=30
MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS=10
```

## 📊 **Service Details**

### **Orchestrator (Main LLM Brain)**
- **Purpose:** All character response generation, conversation coordination
- **Technology:** Python, LangChain, Ollama integration
- **Resources:** High CPU/Memory (handles all LLM processing)
- **Features:** RAG, fine-tuning, quality control, enhanced organic conversations with follow-ups

### **Character Services (Lightweight)**
- **Purpose:** Serve character metadata and configuration only
- **Technology:** Minimal Flask apps (no LLM dependencies)
- **Resources:** Low CPU/Memory (just config APIs)
- **Size:** ~200MB each (vs 2GB+ in old architecture)

### **Discord Handler**
- **Purpose:** Discord API interactions, message routing
- **Technology:** Discord.py, webhook management
- **Integration:** Routes all conversations through orchestrator

### **MongoDB**
- **Purpose:** Conversation history, fine-tuning data, performance metrics
- **Features:** Session management, RAG storage, quality ratings

## 💬 **System Interaction Flow**

This section describes how the services interact during typical operations.

### **1. User Sends a Message to a Bot in Discord:**

   ```mermaid
   sequenceDiagram
       participant User
       participant Discord
       participant Discord Handler (DH)
       participant Orchestrator (ORCH)
       participant Ollama (Local LLM)
       participant Character Config (CC - Peter/Brian/Stewie)
       participant MongoDB (DB)

       User->>Discord: Sends message (e.g., "@Peter what's up?")
       Discord->>DH: Forwards message event
       DH->>ORCH: POST /orchestrate (user_query, channel_id, initiator_bot_name, etc.)
       ORCH->>DB: Load conversation history & session
       ORCH->>Ollama: (Internally) Retrieve RAG context if applicable
       ORCH->>CC: GET /character_info (for prompt enrichment - less frequent, cached)
       ORCH->>Ollama: Generate response (prompt + history + RAG context + char info)
       ORCH->>DB: Save new response to history
       ORCH->>DB: Record auto-assessment (fine-tuning)
       ORCH->>DH: Returns generated response & speaker
       DH->>Discord: Sends message as the chosen bot (e.g., Peter)
       Discord->>User: Displays Peter's response
   ```

   **Detailed Steps:**
   1. **User Message**: A user sends a message in a Discord channel, potentially mentioning a bot (e.g., Peter).
   2. **Discord Event**: Discord sends an event to the `Discord Handler` service.
   3. **Relay to Orchestrator**: The `Discord Handler` identifies the target bot(s) and user query. It then makes an HTTP POST request to the `Orchestrator`'s `/orchestrate` endpoint.
   4. **Orchestrator Processing**: The `Orchestrator` takes over:
      a. **Load History**: Retrieves the current conversation session and history from `MongoDB`.
      b. **RAG Context (Optional)**: If the RAG system is enabled, the `Orchestrator` queries the vector store (ChromaDB, whose data is persisted via a Docker volume) for relevant context from the Family Guy wiki based on the user query.
      c. **Select Speaker**: Intelligently determines which character should respond next (based on direct mentions, conversation flow, or LLM-based coordination).
      d. **Fetch Character Config (Infrequent)**: The detailed character prompts are already in the Orchestrator. It might occasionally fetch updated non-critical metadata from the Character Config services (Peter, Brian, Stewie) if that system were extended, but core personality/prompt data is internal to Orchestrator for performance.
      e. **Generate Response**: Constructs a prompt for the selected character using their base prompt, the conversation history, any RAG context, and the user's input. This prompt is sent to the local `Ollama (mistral-nemo)` LLM for response generation.
      f. **Quality Control & Fine-Tuning**: The response is assessed for quality. This assessment and the response itself are logged in `MongoDB` for the fine-tuning system.
      g. **Save Response**: The generated response is saved to `MongoDB` as part of the conversation history.
   5. **Response to Discord Handler**: The `Orchestrator` sends the generated text and the speaking character back to the `Discord Handler`.
   6. **Send to Discord**: The `Discord Handler` uses the appropriate bot token to send the message to the Discord channel.
   7. **User Sees Response**: The user sees the bot's message in Discord.

### **2. Organically Initiated Conversation:**

   ```mermaid
   sequenceDiagram
       participant Organic Conversation Monitor (in ORCH)
       participant Orchestrator (ORCH)
       participant Ollama (Local LLM)
       participant Discord Handler (DH)
       participant Discord
       participant MongoDB (DB)

       Organic Conversation Monitor->>ORCH: Trigger: Should start organic conversation?
       ORCH->>DB: Load recent channel activity
       ORCH->>Ollama: (Internally) Select initiator bot & generate starter message
       Note over ORCH, DH: Orchestrator calls its own /orchestrate endpoint
       ORCH->>DH: POST /orchestrate (starter_message, channel_id, selected_bot, is_new_conversation=true)
       DH->>Discord: Sends starter message from selected bot
       Discord->>User: User sees new conversation starter
   ```
   **Detailed Steps:**
   1. **Monitoring**: The `Orchestrator` has an internal `Organic Conversation Monitor` that periodically checks if conditions are met to start a new conversation (e.g., prolonged silence, specific conversation cues).
   2. **Context Analysis**: It analyzes recent messages in `MongoDB` for the target channel.
   3. **Initiator Selection & Starter Generation**: If criteria are met:
      a. The `Orchestrator` uses its LLM (`Ollama`) to intelligently select which character (Peter, Brian, or Stewie) should initiate.
      b. It then generates an in-character conversation starter for that bot, potentially using RAG context for inspiration.
   4. **Internal Orchestration Call**: The `Orchestrator` effectively calls its *own* `/orchestrate` endpoint, providing the generated starter message as if it were a user query, and marking it as a new, organically initiated conversation.
   5. **Standard Flow**: From this point, the flow is similar to a user-initiated message: the `Orchestrator` sends the message details to the `Discord Handler`.
   6. **Send to Discord**: The `Discord Handler` sends the starter message to the designated Discord channel using the selected bot's token.
   7. **User Sees Starter**: Users in the channel see a new conversation started by one of the bots.

## 🔧 **Development Commands**

```bash
# View all service logs
docker-compose logs -f

# Restart specific service
docker-compose restart orchestrator

# View orchestrator logs only
docker-compose logs -f orchestrator

# Rebuild after code changes
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check service health
curl http://localhost:5003/health  # Orchestrator
curl http://localhost:5004/health  # Discord Handler
curl http://localhost:5005/health  # RAG Retriever
curl http://localhost:5006/health  # Peter Config
curl http://localhost:5007/health  # Brian Config
curl http://localhost:5008/health  # Stewie Config
curl http://localhost:5009/health  # RAG Crawler

# View fine-tuning statistics
curl http://localhost:5003/fine_tuning_stats
```

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **"Connection to Ollama failed"**
   ```bash
   # Ensure Ollama is running and accessible
   ollama serve
   curl http://localhost:11434/api/version
   ```

2. **"mistral-nemo model not found"**
   ```bash
   ollama pull mistral-nemo
   ollama list  # Verify model is installed
   ```

3. **Character services unhealthy**
   ```bash
   # Check if they can reach each other
   docker-compose exec orchestrator curl http://peter:5005/health
   ```

4. **MongoDB connection errors**
   ```bash
   # Restart MongoDB
   docker-compose restart mongodb
   ```

### **Performance Optimization:**

1. **For RTX 4070 Super:**
   - Ensure Docker has access to GPU
   - Monitor GPU memory usage during operation
   - Consider adjusting `OLLAMA_NUM_PARALLEL` if needed

2. **Memory Usage:**
   - Orchestrator: 4-8GB (handles all LLM processing)
   - Character services: 100-200MB each
   - Total system: ~6-10GB

## 📈 **Monitoring & Management**

### **Health Endpoints:**
- Orchestrator: `http://localhost:5003/health`
- Discord Handler: `http://localhost:5004/health`
- RAG Retriever: `http://localhost:5005/health`
- Peter Config: `http://localhost:5006/health`
- Brian Config: `http://localhost:5007/health`
- Stewie Config: `http://localhost:5008/health`
- RAG Crawler: `http://localhost:5009/health`

### **Fine-Tuning Management:**
- Stats: `http://localhost:5003/fine_tuning_stats`
- Quality Control: `http://localhost:5003/quality_control_status`
- Performance Reports: `http://localhost:5003/optimization_report`

### **Enhanced Organic Conversations:**
- Status & Configuration: `http://localhost:5003/organic_conversation_status`

### **RAG System:**
- Trigger Wiki Crawl: `POST http://localhost:5003/crawl/trigger`
- Crawl Status: `GET http://localhost:5003/crawl/status`

## 🔄 **Migration from OpenAI Architecture**

If upgrading from the old OpenAI-based system:

1. **Remove old environment variables:**
   - `OPENAI_API_KEY`
   - Individual bot LLM API URLs
   - External API configurations

2. **Add new variables:**
   - `OLLAMA_BASE_URL` and `OLLAMA_MODEL`
   - Fine-tuning system configuration
   - RAG system settings

3. **Update Docker setup:**
   ```bash
   docker-compose down --volumes  # Clean slate
   docker-compose build --no-cache
   docker-compose up -d
   ```

## 🎯 **Benefits of New Architecture**

- **🏠 Fully Local:** No external API dependencies or costs
- **⚡ RTX 4070 Optimized:** Tuned for your specific GPU
- **🧠 Smarter Characters:** Enhanced with Family Guy knowledge
- **📊 Quality Control:** Automatic response quality monitoring
- **🔧 Self-Improving:** Supervised fine-tuning system
- **💾 Lightweight:** Character services use 90% less resources
- **🌱 Organic:** Natural conversation flow without rigid scripting

---

**Need help?** Check the logs with `docker-compose logs -f` or open an issue! 