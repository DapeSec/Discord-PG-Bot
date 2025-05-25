# Setting Up Mistral Nemo for Discord Family Guy Bot

This guide helps you set up **Mistral Nemo** (optimized for RTX 4070 Super) for the Discord Family Guy bot system.

## 🎯 **Model Overview**

**Mistral Nemo** is perfect for your RTX 4070 Super because:
- **Model Size**: 12B parameters - optimal for 16GB VRAM
- **Chat Optimized**: Specifically trained for conversational AI
- **Fast Inference**: Excellent performance on consumer GPUs
- **Quality**: High-quality responses with good character consistency

## 🚀 **Quick Setup**

### 1. Install Ollama
```powershell
# Download from: https://ollama.com/
# Or if already installed:
ollama --version
```

### 2. Download Mistral Nemo
```powershell
ollama pull mistral-nemo
```

### 3. Test the Model
```powershell
ollama run mistral-nemo "You are Peter Griffin. Say hello!"
```

### 4. Start Ollama Service
```powershell
# Option A: Command line (blocking)
ollama serve

# Option B: Background service
Start-Process -NoNewWindow ollama serve
```

## ⚙️ **Configuration**

### Environment Variables
Create a `.env` file in your project root:
```env
# Mistral Nemo Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-nemo

# Or for local testing (outside Docker):
# OLLAMA_BASE_URL=http://localhost:11434
```

### Character-Specific Settings
The bot is pre-configured with optimal settings for each character:

**Peter Griffin:**
- Temperature: 0.9 (high creativity for unpredictable responses)
- Max tokens: 500 (shorter, Peter-like responses)

**Brian Griffin:**
- Temperature: 0.8 (controlled creativity for intellectual responses)
- Max tokens: 1800 (longer, verbose responses)

**Stewie Griffin:**
- Temperature: 0.9 (high creativity for evil schemes)
- Max tokens: 1800 (elaborate evil monologues)

## 🎯 Overview

The system now runs entirely on your local Mistral 4070 model via Ollama, providing:
- **Complete privacy** - no data leaves your system
- **Zero API costs** - no external API charges
- **Full control** - customize model behavior as needed
- **Offline operation** - works without internet (after initial setup)

## 📋 Prerequisites

- **Windows 10/11** (for your setup)
- **8GB+ RAM** (4GB for Mistral model + 4GB for services)
- **20GB+ free disk space** (for model and Docker images)
- **Docker Desktop** for Windows
- **Optional: NVIDIA GPU** with 8GB+ VRAM for faster inference

## 🔧 Step 1: Install Ollama

### Download and Install
1. **Download Ollama for Windows:**
   ```
   https://ollama.ai/download/windows
   ```

2. **Run the installer** and follow the setup wizard

3. **Verify installation:**
   ```powershell
   ollama --version
   ```

### Start Ollama Service
```powershell
# Start Ollama in the background
ollama serve
```

**Note:** Keep this terminal open or run Ollama as a Windows service.

## 🤖 Step 2: Download Mistral Nemo

### Pull the Model
```powershell
# Download Mistral Nemo (this may take 10-20 minutes)
ollama pull mistral-nemo
```

### Verify Model Installation
```powershell
# List available models
ollama list

# Test the model
ollama run mistral-nemo "Hello! Please introduce yourself as Peter Griffin."
```

**Expected output:** Peter Griffin-style response

## 🐳 Step 3: Configure Environment

### Update .env File
Create or update your `.env` file:

```env
# Discord Bot Tokens (Required)
DISCORD_BOT_TOKEN_PETER=your_peter_bot_token_here
DISCORD_BOT_TOKEN_BRIAN=your_brian_bot_token_here
DISCORD_BOT_TOKEN_STEWIE=your_stewie_bot_token_here

# Local Mistral Configuration (NO API KEYS NEEDED!)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-nemo

# Service Ports (defaults are fine)
DISCORD_HANDLER_PORT=5001
ORCHESTRATOR_PORT=5003
PETER_BOT_PORT=5005
BRIAN_BOT_PORT=5006
STEWIE_BOT_PORT=5007

# Database Configuration
MONGO_URI=mongodb://admin:adminpassword@mongodb:27017/?authSource=admin
MONGO_DB_NAME=discord_bot_conversations
```

**Important:** No `OPENAI_API_KEY` needed anymore!

## 🚀 Step 4: Start the System

### Test Mistral Setup First
```powershell
# Run the test script to verify everything is working
python scripts/test_mistral_setup.py
```

### Start Docker Services
```powershell
# Start all services
docker-compose -f docker/docker-compose.yml up -d

# Check service status
docker-compose -f docker/docker-compose.yml ps
```

### Verify Health
```powershell
# Check orchestrator (should show local_mistral)
curl http://localhost:5003/health

# Check character info (should show Mistral model)
curl http://localhost:5003/character_info
```

## 🧪 Step 5: Test Character Responses

### Test via Orchestrator API
```powershell
# Test Peter Griffin response
curl -X POST http://localhost:5003/orchestrate -H "Content-Type: application/json" -d '{
  "user_query": "Hello Peter! Tell me about yourself.",
  "channel_id": "test_channel",
  "initiator_bot_name": "Peter",
  "human_user_display_name": "TestUser"
}'
```

### Expected Response Format
```json
{
  "status": "success",
  "character_name": "Peter",
  "response_sent": true,
  "llm_type": "local_mistral",
  "model": "mistral-nemo"
}
```

## 🎭 Character Optimization

### Mistral-Specific Prompts
The characters have been optimized for Mistral Nemo:

- **Peter Griffin:** High creativity (temp 0.9) for unpredictable responses
- **Brian Griffin:** Controlled creativity (temp 0.8) for intellectual responses  
- **Stewie Griffin:** High creativity (temp 0.9) for dramatic evil schemes

### Customizing Characters
Edit `src/app/orchestrator/server_v2.py` to adjust:

```python
CHARACTER_SETTINGS = {
    "Peter": {
        "max_tokens": 500,        # Response length
        "temperature": 0.9,       # Creativity level
        "presence_penalty": 0.3,  # Avoid repetition
        "frequency_penalty": 0.3  # Vary word usage
    }
}
```

## 🔧 Performance Optimization

### GPU Acceleration (Recommended)
If you have an NVIDIA GPU:

```powershell
# Check GPU availability
nvidia-smi

# Ollama will automatically use GPU if available
# Monitor GPU usage during conversations
```

### CPU-Only Optimization
For CPU-only setups:

```powershell
# Set environment variable for CPU optimization
set OLLAMA_NUM_PARALLEL=2
set OLLAMA_FLASH_ATTENTION=0
```

### Memory Management
Monitor system resources:

```powershell
# Check memory usage
Get-Process -Name "ollama"
docker stats

# If memory is low, consider using smaller model
ollama pull mistral:7b
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Ollama Not Accessible
```powershell
# Check if Ollama is running
Get-Process -Name "ollama"

# Restart Ollama
taskkill /F /IM ollama.exe
ollama serve
```

#### 2. Model Not Found
```powershell
# Re-download the model
ollama pull mistral-nemo

# Check available models
ollama list
```

#### 3. Slow Response Times
```powershell
# Check system resources
Get-Counter "\Processor(_Total)\% Processor Time"
Get-Counter "\Memory\Available MBytes"

# Consider smaller model if needed
ollama pull mistral:7b
# Update OLLAMA_MODEL=mistral:7b in .env
```

#### 4. Docker Connection Issues
```powershell
# Check Docker is running
docker version

# Verify network connectivity
docker run --rm alpine ping host.docker.internal
```

#### 5. Character Responses Not Character-Specific
- Check the character prompts in `server_v2.py`
- Increase temperature for more creative responses
- Ensure conversation history is being passed correctly

### Performance Monitoring

#### Monitor Ollama Performance
```powershell
# View Ollama logs
ollama logs

# Check model usage
ollama ps
```

#### Monitor Docker Services
```powershell
# View service logs
docker-compose -f docker/docker-compose.yml logs -f orchestrator

# Check resource usage
docker stats
```

## 🔄 Switching Models

### Use Different Mistral Versions
```powershell
# Download other Mistral variants
ollama pull mistral:7b      # Smaller, faster
ollama pull mistral:latest  # Latest version

# Update environment
# Change OLLAMA_MODEL=mistral:7b in .env
# Restart services
```

### Model Comparison
| Model | Size | Speed | Quality | Memory |
|-------|------|-------|---------|---------|
| mistral:7b | 4GB | Fast | Good | 6GB RAM |
| mistral-nemo | 12GB | Medium | Excellent | 16GB RAM |
| mistral:latest | Varies | Varies | Latest | Varies |

## 📊 Monitoring & Metrics

### Built-in Metrics
```powershell
# Get performance metrics
curl http://localhost:5003/metrics
```

### Custom Monitoring
Monitor these metrics for optimal performance:
- Response time per character
- Memory usage
- GPU utilization (if available)
- Token generation speed

## 🎉 Success Indicators

Your local Mistral setup is working correctly when:

1. ✅ Ollama responds to health checks
2. ✅ Mistral Nemo model is available
3. ✅ Test script passes all tests
4. ✅ Character responses are in-character
5. ✅ Docker services are healthy
6. ✅ No external API calls are made

## 📞 Support

If you encounter issues:

1. **Run the test script:** `python scripts/test_mistral_setup.py`
2. **Check logs:** `docker-compose logs orchestrator`
3. **Verify Ollama:** `ollama list` and `ollama ps`
4. **Monitor resources:** Task Manager or `docker stats`

---

**Congratulations!** You now have a completely local, private, and cost-free Discord bot system powered by Mistral Nemo! 🎊 