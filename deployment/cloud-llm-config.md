# Cloud LLM Configuration for Free Hosting

## Recommended Free/Low-Cost LLM APIs

### 1. **Groq (Best Performance)** 
- **Free tier**: 14,400 requests/day
- **Models**: Llama 3.1, Mixtral
- **Speed**: Very fast inference
- **Setup**: `GROQ_API_KEY=your_key`

### 2. **OpenRouter**
- **Free tier**: $1 free credits
- **Models**: Multiple open-source options
- **Cost**: $0.0001-0.001 per 1K tokens
- **Setup**: `OPENROUTER_API_KEY=your_key`

### 3. **Hugging Face Inference**
- **Free tier**: Rate-limited but free
- **Models**: Open-source models
- **Cost**: Free for basic usage
- **Setup**: `HF_API_KEY=your_key`

## Environment Variables

```bash
# Replace Ollama with cloud LLM
LLM_PROVIDER=groq  # or 'openrouter', 'huggingface'
GROQ_API_KEY=your_groq_api_key
OPENROUTER_API_KEY=your_openrouter_key
HF_API_KEY=your_huggingface_key

# Model configuration
LLM_MODEL=llama-3.1-8b-instant  # for Groq
# LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free  # for OpenRouter
```

## Benefits
- **Reduced RAM usage**: No local LLM inference
- **Better performance**: Professional inference servers
- **Cost-effective**: Free tiers available
- **Easier deployment**: No GPU requirements 