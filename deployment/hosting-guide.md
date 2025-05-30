# Discord Bot Hosting Deployment Guide

## 🚀 Quick Deployment Options

### Option 1: Railway (Recommended for Free)

1. **Sign up** at [railway.app](https://railway.app)
2. **Connect GitHub** repository
3. **Deploy simplified version**:
   ```bash
   # Use simplified-docker-compose.yml
   railway login
   railway link
   railway up
   ```
4. **Set environment variables** in Railway dashboard
5. **Add custom domain** (optional)

### Option 2: DigitalOcean Droplet ($5/month)

1. **Create droplet** with Docker pre-installed
2. **SSH into server**:
   ```bash
   ssh root@your-server-ip
   ```
3. **Clone and deploy**:
   ```bash
   git clone your-repo
   cd discord-pg-bot
   cp .env.example .env
   # Edit .env with your tokens
   docker-compose -f deployment/simplified-docker-compose.yml up -d
   ```

### Option 3: Render

1. **Connect GitHub** at [render.com](https://render.com)
2. **Create Web Service** with Docker
3. **Set environment**:
   - Build Command: `docker build -f deployment/unified.dockerfile .`
   - Start Command: `docker run -p $PORT:8080 your-image`

## 🔧 Configuration Steps

### 1. Get Discord Bot Tokens
```bash
# Visit https://discord.com/developers/applications
# Create 3 applications (Peter, Brian, Stewie)
# Copy bot tokens to .env file
```

### 2. Setup External LLM (Recommended)
```bash
# Sign up for Groq: https://console.groq.com
# Get API key
# Add to environment: GROQ_API_KEY=your_key
```

### 3. Environment Variables
```bash
DISCORD_BOT_TOKEN_PETER=your_peter_token
DISCORD_BOT_TOKEN_BRIAN=your_brian_token
DISCORD_BOT_TOKEN_STEWIE=your_stewie_token
DEFAULT_DISCORD_CHANNEL_ID=your_channel_id
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key
```

## 💡 Cost Optimization Tips

1. **Use external LLM APIs** instead of local Ollama
2. **Combine microservices** into single container
3. **Use Redis instead of KeyDB** for caching
4. **Disable RAG features** for basic deployment
5. **Use smaller Docker images** (Alpine Linux)

## 🛠️ Monitoring & Maintenance

### Health Checks
```bash
# Check bot status
curl https://your-app.railway.app/health

# Check logs
railway logs
# or
docker logs discord-bot-unified
```

### Scaling Up
When ready to upgrade:
1. **Move to VPS** ($5-10/month)
2. **Enable all microservices**
3. **Add local LLM** for better privacy
4. **Setup monitoring** with Grafana 