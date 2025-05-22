# Family Guy Discord Bots

An interactive Discord bot system featuring Peter Griffin, Brian Griffin, and Stewie Griffin from Family Guy. The bots use the Mistral language model through Ollama to generate responses in their characteristic styles, complete with their unique personalities, and can interact with each other in a natural, entertaining way.

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Docker Setup](#docker-setup)
7. [Usage](#usage)
8. [Technical Details](#technical-details)
9. [Contributing](#contributing)
10. [License](#license)

## System Architecture

```mermaid
graph TD
    subgraph Discord["Discord Platform"]
        DC[Discord Channels]
    end

    subgraph Host["Host Machine"]
        OL[Ollama LLM<br>GPU Accelerated]
    end

    subgraph Docker["Docker Environment"]
        subgraph Orchestrator["Orchestrator Container"]
            OS[Orchestrator Service<br>:5003]
            Q[Message Queue]
            RAG[RAG System]
            VDB[(Chroma DB)]
        end

        subgraph Bots["Bot Containers"]
            PB[Peter Bot<br>:5005]
            BB[Brian Bot<br>:5002]
            SB[Stewie Bot<br>:5004]
        end

        subgraph DB["Database"]
            MDB[(MongoDB<br>:27017)]
        end
    end

    DC <--> OS
    OS <--> Q
    OS <--> MDB
    Q <--> PB
    Q <--> BB
    Q <--> SB
    PB <--> RAG
    BB <--> RAG
    SB <--> RAG
    RAG <--> VDB
    RAG <--> OL
    PB <--> OL
    BB <--> OL
    SB <--> OL

    style Discord fill:#7289DA,color:white
    style Docker fill:#4CAF50,color:white
    style Host fill:#FF9800,color:white
    style DB fill:#2196F3,color:white
```

## Project Structure
```
discord-pg-bot/
├── src/                   # Source code
│   └── app/              # Application code
│       ├── bots/         # Bot implementations
│       │   ├── peter_bot.py
│       │   ├── brian_bot.py
│       │   └── stewie_bot.py
│       ├── orchestrator/ # Orchestrator service
│       │   └── server.py
│       ├── utils/       # Shared utilities
│       │   ├── rag.py
│       │   └── db.py
│       └── models/      # Data models
│           └── conversation.py
├── docker/               # Docker configuration
│   ├── Dockerfile.orchestrator
│   ├── Dockerfile.bot
│   └── docker-compose.yml
├── tests/               # Unit tests
│   ├── conftest.py
│   ├── test_bots.py
│   ├── test_orchestrator.py
│   └── test_rag.py
├── config/             # Configuration files
├── scripts/            # Utility scripts
├── logs/              # Application logs
├── chroma_db/         # Vector store data
├── .env               # Environment variables
├── requirements.txt   # Python dependencies
└── README.md         # Documentation
```

## Features

- Three distinct bots with unique personalities:
  - Peter: Humorous, dim-witted, with tangents and "Heheheh" interjections
  - Brian: Intellectual, sarcastic, and sometimes preachy
  - Stewie: Sophisticated, devious, with British accent influences
- Containerized microservices architecture
- GPU-accelerated LLM responses via host Ollama
- RAG (Retrieval-Augmented Generation) system with Chroma DB
- Persistent conversation history using MongoDB
- Multi-bot conversations with natural interaction flow
- Automated daily conversations for continuous engagement
- REST API endpoints for inter-bot communication
- Message queue system for managing conversation flow
- Context-aware responses based on conversation history

## Prerequisites

## System Requirements

### Minimum Requirements
- CPU: 4 cores
- RAM: 8GB
- Storage: 4GB free space
- Operating System: Windows 10/11, macOS, or Linux
- Python 3.8 or higher

### Recommended Requirements (for GPU Acceleration)
- NVIDIA GPU with at least 4GB VRAM
- CUDA Toolkit 11.7 or higher
- NVIDIA drivers 470.x or higher
- RAM: 16GB
- Storage: 8GB free space

### Port Requirements
- 5002: Brian Bot Service
- 5003: Orchestrator Service
- 5004: Stewie Bot Service
- 5005: Peter Bot Service
- 11434: Ollama API
- 27017: MongoDB

2. **Required Software**
   - [Docker](https://www.docker.com/get-started) and Docker Compose
   - [Ollama](https://ollama.ai/) (installed on host machine)
   - [Git](https://git-scm.com/downloads)
   - Discord account and bot tokens

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/DapeSec/discord-pg-bot.git
   cd discord-pg-bot
   ```

2. **Set up Ollama on Host Machine**
   ```bash
   # Start Ollama service
   ollama serve

   # In another terminal, pull the Mistral model
   ollama pull mistral
   ```

3. **Configure Environment**
   Create a `.env` file in the project root:
   ```
   # Discord Bot Tokens
   DISCORD_BOT_TOKEN_PETER=your_peter_bot_token_here
   DISCORD_BOT_TOKEN_BRIAN=your_brian_bot_token_here
   DISCORD_BOT_TOKEN_STEWIE=your_stewie_bot_token_here

   # MongoDB Configuration
   MONGO_URI=mongodb://mongodb:27017/
   MONGO_DB_NAME=discord_bot_conversations
   MONGO_COLLECTION_NAME=conversations

   # Ollama Configuration
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```

## Docker Setup

1. **Build and Start Services**
   ```bash
   # Build and start all services
   docker-compose -f docker/docker-compose.yml up --build

   # Or run in detached mode
   docker-compose -f docker/docker-compose.yml up -d
   ```

2. **Verify Installation**
   ```bash
   # Check running containers
   docker-compose -f docker/docker-compose.yml ps

   # Check logs
   docker-compose -f docker/docker-compose.yml logs -f
   ```

3. **Container Management**
   ```bash
   # Stop all services
   docker-compose -f docker/docker-compose.yml down

   # Restart a specific service
   docker-compose -f docker/docker-compose.yml restart peter
   ```

### MongoDB Access

The MongoDB instance is accessible both from within the Docker network and from your host machine:

1. **From Docker containers:**
   ```
   mongodb://admin:adminpassword@mongodb:27017/
   ```

2. **From host machine:**
   ```
   mongodb://admin:adminpassword@localhost:27017/
   ```

Default credentials:
- Username: `admin`
- Password: `adminpassword`

You can connect using MongoDB Compass or any other MongoDB client using these credentials.

> **Note:** For production, make sure to change these default credentials and use environment variables.

## Usage

### Interacting with the Bots
- Send a message starting with the character's name:
  ```
  !peter Tell me about your day
  !brian What's your opinion on literature?
  !stewie What's your latest evil plan?
  ```
- Or mention any bot using their @mention (e.g., @PeterGriffin, @BrianGriffin, @StewieGriffin)

### Multi-Bot Conversations
When you interact with any bot:
1. The orchestrator receives and processes the message
2. The primary bot generates its response
3. Other bots may join the conversation naturally
4. The orchestrator manages the conversation flow and timing
5. All conversations are stored in MongoDB for context

### Automated Conversations
The system includes an automated feature that initiates random conversations throughout the day:
- Configurable number of daily conversations
- Dynamic conversation starters based on context
- Natural interaction between characters
- Helps maintain channel activity

## Technical Details

### System Components
- **Orchestrator Server** (:5003): Central message handler and conversation manager
- **Character Bots**: Individual bot servers for Peter (:5005), Brian (:5002), and Stewie (:5004)
- **MongoDB Database**: Stores conversation history and context
- **Chroma DB**: Vector database for RAG system, storing embeddings for contextual retrieval
- **Ollama/Mistral**: Provides AI language model capabilities
- **RAG System**: Enhances responses with relevant context from the vector database

### Communication Flow
1. Discord messages are received by the orchestrator
2. Messages are queued and distributed to relevant bots
3. The RAG system retrieves relevant context from Chroma DB
4. Bots process messages using Ollama/Mistral with RAG-enhanced context
5. Responses are coordinated through the orchestrator
6. Final responses are sent back to Discord
7. Conversations are persisted in MongoDB and relevant parts are vectorized for RAG

### Error Handling

The system includes comprehensive error handling for:
- Missing or invalid Discord tokens
- Ollama connection issues
- Inter-bot communication failures
- Message processing errors
- API endpoint issues
- Queue management errors
- Database connection and query errors
- RAG system and vector store issues

## Contributing

Feel free to fork the repository and submit pull requests for any improvements you'd like to add. Some areas for potential enhancement:
- Additional Family Guy characters
- More sophisticated conversation handling
- Enhanced error recovery
- Improved natural language processing
- Advanced conversation orchestration
- Custom personality fine-tuning
- Extended conversation history analysis
- Improved automated conversation triggers

## License

This project is licensed under the MIT License.

```text
MIT License

Copyright (c) 2024 DapeSec

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Running Locally (Development)

1. Set up your virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # OR
   .venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the bots individually:
   ```bash
   # Start the orchestrator
   python -m src.app.orchestrator.server

   # Start individual bots (in separate terminals)
   python -m src.app.bots.peter_bot
   python -m src.app.bots.brian_bot
   python -m src.app.bots.stewie_bot
   ```

## Running with Docker

1. Build and start all services:
   ```bash
   docker-compose -f docker/docker-compose.yml up --build
   ```

2. Or run in detached mode:
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

3. View logs:
   ```bash
   docker-compose -f docker/docker-compose.yml logs -f
   ```

4. Stop services:
   ```bash
   docker-compose -f docker/docker-compose.yml down
   ```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test files
pytest tests/test_bots.py
pytest tests/test_orchestrator.py
pytest tests/test_rag.py

# Run with coverage report
pytest --cov=src.app tests/
```

## Docker Setup

### Prerequisites
1. Install Docker and Docker Compose
2. Install Ollama on your host machine from [ollama.ai](https://ollama.ai/)
3. Make sure ports 5002-5005 and 27017 are available
4. Ensure your GPU drivers are properly installed (for Ollama)

### Setup Steps

1. **Start Ollama on your host machine**
   ```bash
   # Start Ollama service
   ollama serve

   # In another terminal, pull the Mistral model
   ollama pull mistral
   ```

2. **Configure Environment**
   Create a `.env` file with your configuration:
   ```
   # Discord Bot Tokens
   DISCORD_BOT_TOKEN_PETER=your_peter_bot_token_here
   DISCORD_BOT_TOKEN_BRIAN=your_brian_bot_token_here
   DISCORD_BOT_TOKEN_STEWIE=your_stewie_bot_token_here

   # MongoDB Configuration
   MONGO_URI=mongodb://mongodb:27017/
   MONGO_DB_NAME=discord_bot_conversations
   MONGO_COLLECTION_NAME=conversations

   # Ollama Configuration
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```

3. **Build and Run Containers**
   ```bash
   # Build and start all services
   docker-compose up --build

   # Or run in detached mode
   docker-compose up -d
   ```

4. **Verify Setup**
   ```bash
   # Check running containers
   docker-compose ps

   # Check logs
   docker-compose logs -f
   ```

### Architecture Notes
- Ollama runs on the host machine to utilize GPU resources
- MongoDB runs in a container with persistent storage
- Bot services and orchestrator run in separate containers
- All services communicate over a dedicated Docker network
- Logs and Chroma DB are persisted through volume mounts

### Container Management
```bash
# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart peter

# View logs for a specific service
docker-compose logs -f orchestrator
```

### Troubleshooting
1. **Ollama Connection Issues**
   - Verify Ollama is running on the host: `curl http://localhost:11434/api/tags`
   - Check if the model is pulled: `ollama list`
   - Ensure host.docker.internal resolves correctly
   - For Linux hosts, add `--add-host=host.docker.internal:host-gateway` to your docker run command

2. **GPU Access**
   - Verify GPU is recognized by Ollama: `nvidia-smi`
   - Check Ollama logs for GPU initialization
   - Ensure CUDA drivers are installed
   - For Docker, ensure nvidia-container-toolkit is installed
   - Check GPU memory usage isn't maxed out

3. **MongoDB Connection Issues**
   - Verify MongoDB container is running: `docker ps | grep mongodb`
   - Check MongoDB logs: `docker-compose logs mongodb`
   - Ensure correct credentials in .env file
   - Check if MongoDB port is not conflicting with local installation

4. **Bot Communication Issues**
   - Verify all services are running: `docker-compose ps`
   - Check individual bot logs: `docker-compose logs <service_name>`
   - Ensure Discord bot tokens are valid
   - Check Discord bot permissions
   - Verify network connectivity between containers

5. **Performance Issues**
   - Monitor container resource usage: `docker stats`
   - Check host system resources
   - Verify GPU utilization if applicable
   - Consider adjusting container resource limits
   - Monitor MongoDB performance metrics

### Logs Location
- Container logs: `docker-compose logs`
- Application logs: `./logs/` directory
- Ollama logs: System-dependent location
  - Linux: `/var/log/ollama.log`
  - Windows: Event Viewer
  - macOS: Console.app

### Getting Help
- Open an issue on GitHub
- Check existing issues for similar problems
- Join our Discord community for support
- Review the documentation

## License

This project is licensed under the MIT License.

```text
MIT License

Copyright (c) 2024 DapeSec

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
``` 