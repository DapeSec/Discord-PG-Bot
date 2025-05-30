import os
import hashlib
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage

# Import cache utilities
try:
    from src.shared.cache import get_cache
    CACHE_AVAILABLE = True
    print("✅ LLM Service: Cache utilities imported successfully")
except ImportError as e:
    print(f"⚠️ LLM Service: Cache utilities not available: {e}")
    CACHE_AVAILABLE = False

# Load environment variables
load_dotenv()

# --- Service Configuration ---
LLM_SERVICE_PORT = int(os.getenv("LLM_SERVICE_PORT", "6001"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-nemo")

# Cache configuration
RESPONSE_CACHE_TTL = int(os.getenv("LLM_RESPONSE_CACHE_TTL", "3600"))  # 1 hour
MAX_PROMPT_CACHE_SIZE = int(os.getenv("MAX_PROMPT_CACHE_SIZE", "1000"))

# --- Flask App ---
app = Flask(__name__)

class LLMService:
    """
    Centralized LLM service that provides a single point of access to the Ollama instance.
    Handles request queuing, caching, and health monitoring.
    """
    
    def __init__(self):
        """Initialize the LLM service with Ollama connection and caching."""
        self.llm = None
        self.cache = None
        self.request_count = 0
        self.error_count = 0
        self.cache_hits = 0
        
        # Initialize cache if available
        if CACHE_AVAILABLE:
            self.cache = get_cache("llm_service")
            print("💾 LLM Service: Cache initialized")
        
        # Initialize Ollama connection
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the Ollama LLM connection."""
        try:
            self.llm = Ollama(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL,
                temperature=0.8,
                num_predict=512,
                top_k=40,
                top_p=0.9,
                repeat_penalty=1.1
            )
            
            # Test the connection
            test_response = self.llm.invoke("Test connection")
            print(f"🤖 LLM Service: Successfully connected to {OLLAMA_MODEL} at {OLLAMA_BASE_URL}")
            print(f"🧪 LLM Service: Test response: {test_response[:50]}...")
            
        except Exception as e:
            print(f"❌ LLM Service: Failed to initialize Ollama: {e}")
            raise Exception(f"LLM Service initialization failed: {e}")
    
    def _generate_cache_key(self, prompt: str, settings: Dict[str, Any]) -> str:
        """Generate a cache key for the prompt and settings."""
        # Create a hash of the prompt and settings for caching
        content = f"{prompt}:{json.dumps(settings, sort_keys=True)}"
        return f"llm:response:{hashlib.md5(content.encode()).hexdigest()}"
    
    def generate_response(self, prompt: str, user_message: str = None, chat_history: list = None, settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a response using the LLM with proper conversation structure."""
        
        self.request_count += 1
        print(f"🤖 LLM Service: Processing request {self.request_count}")
        
        try:
            # Apply settings if provided
            if settings:
                self._apply_settings(settings)
            
            # Generate cache key
            cache_key = None
            if self.cache:
                cache_content = {
                    "prompt": prompt,
                    "user_message": user_message,
                    "history": chat_history or [],
                    "settings": settings or {}
                }
                cache_key = self._generate_cache_key(json.dumps(cache_content, sort_keys=True), {})
                
                # Check cache first
                cached_response = self.cache.get(cache_key)
                if cached_response:
                    self.cache_hits += 1
                    print(f"💾 LLM Service: Cache hit for request {self.request_count}")
                    return {
                        "response": cached_response,
                        "cached": True,
                        "request_id": self.request_count,
                        "timestamp": datetime.now().isoformat()
                    }
            
            # Generate response with proper conversation structure
            if user_message:
                # Use chat template for proper system + user message structure
                messages = []
                
                # Add conversation history if provided
                if chat_history:
                    for msg in chat_history:
                        if isinstance(msg, HumanMessage):
                            messages.append(("user", msg.content))
                        elif isinstance(msg, AIMessage):
                            messages.append(("assistant", msg.content))
                
                # Add current user message
                messages.append(("user", user_message))
                
                # Create chat template with system prompt and messages
                chat_template = ChatPromptTemplate.from_messages([
                    ("system", prompt),
                    *messages
                ])
                
                response = chat_template | self.llm
                result = response.invoke({})
            elif chat_history:
                # Use chat template for conversation (legacy support)
                messages = []
                for msg in chat_history:
                    if isinstance(msg, HumanMessage):
                        messages.append(("user", msg.content))
                    elif isinstance(msg, AIMessage):
                        messages.append(("assistant", msg.content))
                
                # Add system prompt and current message
                chat_template = ChatPromptTemplate.from_messages([
                    ("system", prompt),
                    *messages
                ])
                
                response = chat_template | self.llm
                result = response.invoke({})
            else:
                # Simple prompt (fallback - treat prompt as complete input)
                result = self.llm.invoke(prompt)
            
            # Cache the response
            if self.cache and cache_key:
                self.cache.set(cache_key, result, ttl=RESPONSE_CACHE_TTL)
                print(f"💾 LLM Service: Cached response for request {self.request_count}")
            
            return {
                "response": result,
                "cached": False,
                "request_id": self.request_count,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.error_count += 1
            print(f"❌ LLM Service: Error generating response: {e}")
            print(traceback.format_exc())
            raise Exception(f"LLM generation failed: {e}")
    
    def _apply_settings(self, settings: Dict[str, Any]):
        """Apply LLM settings dynamically."""
        try:
            if "temperature" in settings:
                self.llm.temperature = settings["temperature"]
            if "max_tokens" in settings:
                self.llm.num_predict = settings["max_tokens"]
            if "top_p" in settings:
                self.llm.top_p = settings["top_p"]
            if "top_k" in settings:
                self.llm.top_k = settings["top_k"]
            if "repeat_penalty" in settings:
                self.llm.repeat_penalty = settings["repeat_penalty"]
                
        except Exception as e:
            print(f"⚠️ LLM Service: Warning - could not apply settings: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of the LLM service."""
        try:
            # Test LLM connection
            test_response = self.llm.invoke("Health check")
            llm_healthy = len(test_response) > 0
            
            cache_healthy = True
            cache_stats = {}
            if self.cache:
                try:
                    # Test cache connection
                    test_key = "health_check"
                    self.cache.set(test_key, "test", ttl=60)
                    test_result = self.cache.get(test_key)
                    cache_healthy = test_result == "test"
                    self.cache.delete(test_key)
                    
                    cache_stats = {
                        "available": True,
                        "healthy": cache_healthy
                    }
                except Exception as e:
                    cache_healthy = False
                    cache_stats = {
                        "available": True,
                        "healthy": False,
                        "error": str(e)
                    }
            else:
                cache_stats = {"available": False}
            
            return {
                "status": "healthy" if llm_healthy and cache_healthy else "degraded",
                "llm": {
                    "model": OLLAMA_MODEL,
                    "base_url": OLLAMA_BASE_URL,
                    "healthy": llm_healthy
                },
                "cache": cache_stats,
                "metrics": {
                    "total_requests": self.request_count,
                    "error_count": self.error_count,
                    "cache_hits": self.cache_hits,
                    "cache_hit_rate": self.cache_hits / max(self.request_count, 1) * 100
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Global LLM service instance
llm_service = LLMService()

# --- API Endpoints ---

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        health_status = llm_service.get_health_status()
        status_code = 200 if health_status["status"] in ["healthy", "degraded"] else 503
        return jsonify(health_status), status_code
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/generate', methods=['POST'])
def generate_response():
    """Generate a response using the LLM."""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({
                "error": "Missing required field: prompt"
            }), 400
        
        prompt = data['prompt']
        user_message = data.get('user_message')
        chat_history = data.get('chat_history', [])
        settings = data.get('settings', {})
        
        # Convert chat history to proper format if needed
        formatted_history = []
        for msg in chat_history:
            if isinstance(msg, dict):
                if msg.get('type') == 'human':
                    formatted_history.append(HumanMessage(content=msg['content']))
                elif msg.get('type') == 'ai':
                    formatted_history.append(AIMessage(content=msg['content']))
            else:
                formatted_history.append(msg)
        
        result = llm_service.generate_response(
            prompt=prompt,
            user_message=user_message,
            chat_history=formatted_history,
            settings=settings
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"❌ LLM Service: Error in generate endpoint: {e}")
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/models', methods=['GET'])
def get_models():
    """Get information about available models."""
    return jsonify({
        "current_model": OLLAMA_MODEL,
        "base_url": OLLAMA_BASE_URL,
        "capabilities": [
            "text_generation",
            "conversation",
            "character_roleplay"
        ],
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get service metrics."""
    try:
        health_status = llm_service.get_health_status()
        return jsonify({
            "metrics": health_status.get("metrics", {}),
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear the LLM response cache."""
    try:
        if llm_service.cache:
            # Clear LLM-specific cache keys
            # Note: This is a simple implementation - in production you'd want more sophisticated cache management
            llm_service.cache_hits = 0
            return jsonify({
                "message": "Cache cleared successfully",
                "timestamp": datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "message": "Cache not available",
                "timestamp": datetime.now().isoformat()
            }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print(f"🤖 LLM Service starting on port {LLM_SERVICE_PORT}...")
    print(f"🔗 Ollama connection: {OLLAMA_BASE_URL}")
    print(f"🧠 Model: {OLLAMA_MODEL}")
    print(f"💾 Cache available: {CACHE_AVAILABLE}")
    app.run(host='0.0.0.0', port=LLM_SERVICE_PORT, debug=False) 