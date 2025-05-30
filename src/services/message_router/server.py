import os
import requests
import traceback
import random
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import redis
import json
import logging
import hashlib

# Import cache utilities
try:
    from src.shared.cache import get_cache
    CACHE_AVAILABLE = True
    print("✅ Message Router: Cache utilities imported successfully")
except ImportError as e:
    print(f"⚠️ Message Router: Cache utilities not available: {e}")
    CACHE_AVAILABLE = False

# Import centralized retry manager
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.retry_manager import retry_sync, RetryConfig

# Load environment variables
load_dotenv()

# --- Service Configuration ---
MESSAGE_ROUTER_PORT = int(os.getenv("MESSAGE_ROUTER_PORT", "6005"))

# Service URLs
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:6001")
CHARACTER_CONFIG_URL = os.getenv("CHARACTER_CONFIG_API_URL", "http://character-config:6006")
CONVERSATION_COORDINATOR_URL = os.getenv("CONVERSATION_COORDINATOR_URL", "http://conversation-coordinator:6002")
QUALITY_CONTROL_URL = os.getenv("QUALITY_CONTROL_URL", "http://quality-control:6003")
FINE_TUNING_URL = os.getenv("FINE_TUNING_URL", "http://fine-tuning:6004")
RAG_RETRIEVER_URL = os.getenv("RAG_RETRIEVER_URL", "http://rag-retriever:6007")

# Discord bot service URLs
PETER_DISCORD_URL = os.getenv("PETER_DISCORD_URL", "http://peter-discord:6011")
BRIAN_DISCORD_URL = os.getenv("BRIAN_DISCORD_URL", "http://brian-discord:6012")
STEWIE_DISCORD_URL = os.getenv("STEWIE_DISCORD_URL", "http://stewie-discord:6013")

# Cache configuration
ROUTING_CACHE_TTL = int(os.getenv("ROUTING_CACHE_TTL", "300"))  # 5 minutes

# --- Flask App ---
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class MessageRouter:
    """
    Central message routing service that coordinates between all microservices.
    Handles request routing, service discovery, and response coordination.
    """
    
    def __init__(self):
        """Initialize the message router with service connections and caching."""
        self.cache = None
        self.redis_client = None
        self.request_count = 0
        self.successful_requests = 0
        self.error_count = 0
        
        # Concurrency limiting for organic retries
        self.active_retry_threads = 0
        self.max_concurrent_retries = 3  # Limit to 3 concurrent retry threads
        
        # Initialize cache if available
        if CACHE_AVAILABLE:
            self.cache = get_cache("message_router")
            print("💾 Message Router: Cache initialized")
        
        # Initialize KeyDB connection instead of MongoDB
        self.redis_client = self._initialize_keydb()
        
        # Service health status
        self.service_health = {}
    
    def _initialize_keydb(self):
        """Initialize KeyDB connection for conversation storage"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://keydb:6379')
            if redis_url.startswith('redis://'):
                redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                host, port = redis_url.split(':')
                redis_client = redis.Redis(host=host, port=int(port), decode_responses=True)
            
            # Test connection
            redis_client.ping()
            print("✅ Message Router: Connected to KeyDB")
            return redis_client
        except Exception as e:
            print(f"❌ Message Router: Failed to connect to KeyDB: {e}")
            return None
    
    def _make_service_request(self, service_url: str, endpoint: str, method: str = "GET", data: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """
        Make a request to a microservice with error handling.
        
        Args:
            service_url: Base URL of the service
            endpoint: API endpoint to call
            method: HTTP method (GET, POST, etc.)
            data: Request data for POST requests
            timeout: Request timeout in seconds
            
        Returns:
            Response data or error information
        """
        try:
            url = f"{service_url}{endpoint}"
            
            if method.upper() == "GET":
                response = requests.get(url, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": f"Service returned {response.status_code}",
                    "status_code": response.status_code,
                    "response": response.text
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Service timeout after {timeout}s",
                "status_code": 408
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Service unavailable",
                "status_code": 503
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": 500
            }
    
    def _send_organic_message_to_discord(self, character: str, message: str, channel_id: str) -> Dict[str, Any]:
        """Send an organic follow-up message to the Discord service for a character."""
        discord_services = {
            "peter": f"{PETER_DISCORD_URL}",
            "brian": f"{BRIAN_DISCORD_URL}",
            "stewie": f"{STEWIE_DISCORD_URL}"
        }
        
        character_lower = character.lower()
        if character_lower not in discord_services:
            return {
                "success": False,
                "error": f"Unknown character: {character}"
            }
        
        discord_url = discord_services[character_lower]
        
        # Define the Discord send operation
        def send_to_discord():
            return self._make_service_request(
                discord_url,
                "/organic-message",
                method="POST",
                data={
                    "message": message,
                    "channel_id": channel_id
                },
                timeout=10
            )
        
        # Use centralized retry with special handling for 503 errors
        def validate_response(response):
            if response and response.get("success"):
                return True
            # Allow retry only for 503 errors (service unavailable)
            if response and response.get("status_code") == 503:
                return False  # This will trigger a retry
            # For all other errors (including 400/quality control), don't retry
            return True  # Accept the failure without retry
        
        # Use centralized retry for Discord sending (limited retries)
        result = retry_sync(
            operation=send_to_discord,
            validation_func=validate_response,
            service_name="Message Router Discord",
            operation_name=f"send_organic_to_{character}",
            max_attempts=2,  # Limited retries
            base_delay=2.0   # 2 second delay for 503 retries
        )
        
        if result:
            return result
        else:
            return {
                "success": False,
                "error": f"Failed to send organic message to {character} after retries",
                "status_code": 503
            }
    
    def orchestrate_conversation(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrate a complete conversation flow through all microservices.
        
        Args:
            conversation_data: Input conversation data
            
        Returns:
            Final response or error information
        """
        self.request_count += 1
        
        try:
            # Extract key information
            character_name = conversation_data.get("character_name")
            input_text = conversation_data.get("input_text", "")
            conversation_history = conversation_data.get("conversation_history", [])
            channel_id = conversation_data.get("channel_id", "default")
            user_id = conversation_data.get("user_id", "anonymous")
            
            if not character_name:
                return {
                    "success": False,
                    "error": "Missing required field: character_name"
                }
            
            # Step 1: Use conversation coordinator to select responding character
            print(f"🎭 Message Router: Determining responding character")
            coordinator_response = self._make_service_request(
                CONVERSATION_COORDINATOR_URL,
                "/select-character",
                method="POST",
                data={
                    "message": input_text,
                    "conversation_id": channel_id,
                    "available_characters": [character_name],  # For single character bots
                    "force_character": character_name  # Force the specific character for individual bots
                }
            )
            
            if coordinator_response["success"]:
                selected_character = coordinator_response["data"]["selected_character"]
                selection_reasoning = coordinator_response["data"]["reasoning"]
                print(f"🎭 Message Router: Selected character {selected_character} - {selection_reasoning}")
            else:
                # Fallback to requested character if coordinator unavailable
                selected_character = character_name
                print(f"⚠️ Message Router: Coordinator unavailable, using fallback character {selected_character}")
            
            # Step 2: Get character configuration
            print(f"🔄 Message Router: Getting character config for {selected_character}")
            char_config_response = self._make_service_request(
                CHARACTER_CONFIG_URL, 
                f"/llm_prompt/{selected_character}"
            )
            
            if not char_config_response["success"]:
                return {
                    "success": False,
                    "error": f"Failed to get character config: {char_config_response['error']}"
                }
            
            character_config = char_config_response["data"]
            
            # Step 3: Get RAG context if needed
            rag_context = ""
            if input_text:
                print(f"🔍 Message Router: Retrieving RAG context")
                rag_response = self._make_service_request(
                    RAG_RETRIEVER_URL,
                    "/retrieve",
                    method="POST",
                    data={"query": input_text, "num_results": 3}
                )
                
                if rag_response["success"]:
                    rag_context = rag_response["data"].get("context", "")
            
            # Step 4: Get optimized prompt from fine-tuning service
            print(f"🔧 Message Router: Getting optimized prompt")
            fine_tuning_response = self._make_service_request(
                FINE_TUNING_URL,
                "/optimize-prompt",
                method="POST",
                data={
                    "character": selected_character,
                    "context": {
                        "topic": "general",  # Could be enhanced with topic detection
                        "conversation_context": {
                            "recent_topics": [],  # Could be populated from conversation history
                            "last_speaker": conversation_history[-1].get("character") if conversation_history else None
                        }
                    }
                }
            )
            
            # Use optimized prompt if available, otherwise fallback to character config
            if fine_tuning_response["success"] and "data" in fine_tuning_response:
                response_data = fine_tuning_response["data"]
                if "optimized_prompt" in response_data:
                    optimized_prompt = response_data["optimized_prompt"]
                    confidence = response_data.get("confidence", "N/A")
                    print(f"🔧 Message Router: Using optimized prompt (confidence: {confidence})")
                else:
                    optimized_prompt = character_config["llm_prompt"]
                    print(f"⚠️ Message Router: Fine-tuning response missing optimized_prompt, using base prompt")
            else:
                optimized_prompt = character_config["llm_prompt"]
                error_msg = fine_tuning_response.get("error", "Unknown error") if fine_tuning_response else "No response"
                print(f"⚠️ Message Router: Fine-tuning unavailable ({error_msg}), using base prompt")
            
            # Step 5: Generate response using LLM service
            print(f"🤖 Message Router: Generating response for {selected_character}")
            
            llm_response = self._make_service_request(
                LLM_SERVICE_URL,
                "/generate",
                method="POST",
                data={
                    "prompt": optimized_prompt,
                    "user_message": input_text,
                    "chat_history": conversation_history,
                    "settings": character_config.get("llm_settings", {})
                }
            )
            
            if not llm_response["success"]:
                return {
                    "success": False,
                    "error": f"LLM generation failed: {llm_response['error']}"
                }
            
            generated_response = llm_response["data"]["response"]
            
            # Step 6: Quality control analysis (for metrics only, not blocking)
            print(f"📊 Message Router: Analyzing response quality for metrics")
            
            # Determine last speaker from conversation history
            last_speaker = None
            if conversation_history:
                last_speaker = conversation_history[-1].get("character")
            
            quality_response = self._make_service_request(
                QUALITY_CONTROL_URL,
                "/analyze",
                method="POST",
                data={
                    "response": generated_response,
                    "character": selected_character,
                    "conversation_id": channel_id,  # Use channel_id as conversation_id
                    "context": input_text,
                    "last_speaker": last_speaker
                }
            )
            
            if quality_response["success"]:
                quality_data = quality_response["data"]
                quality_passed = quality_data.get("quality_check_passed", True)
                quality_score = quality_data.get("overall_score", 85)
                quality_metrics = quality_data.get("metrics", {})
                print(f"📊 Message Router: Quality analysis - Score: {quality_score}, Passed: {quality_passed}")
                
                # NOTE: We don't block on quality control here anymore
                # The Discord bots handle quality control and retries
                # We just collect metrics for learning
                
            else:
                # Fallback values if quality control unavailable
                quality_passed = True
                quality_score = 85
                quality_metrics = {}
                print(f"⚠️ Message Router: Quality control unavailable, using fallback values")
            
            # Step 7: Store conversation in KeyDB
            try:
                conversation_record = {
                    "timestamp": datetime.now().isoformat(),
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "character_name": selected_character,
                    "input_text": input_text,
                    "response_text": generated_response,
                    "conversation_history_length": len(conversation_history),
                    "rag_context_used": str(len(rag_context) > 0),  # Convert bool to string
                    "quality_score": quality_score,
                    "quality_passed": str(quality_passed),  # Convert bool to string
                    "quality_metrics": json.dumps(quality_metrics),
                    "prompt_optimized": str(fine_tuning_response["success"]),  # Convert bool to string
                    "request_id": self.request_count
                }
                
                # Store conversation record in KeyDB
                record_key = f"conversation:{channel_id}:{self.request_count}:{datetime.now().timestamp()}"
                self.redis_client.hset(record_key, mapping=conversation_record)
                
                # Set expiry (24 hours)
                self.redis_client.expire(record_key, 86400)
                
                print(f"💾 Message Router: Stored conversation record in KeyDB")
                
            except Exception as e:
                print(f"⚠️ Message Router: Failed to store conversation: {e}")
            
            # Step 8: Send to fine-tuning service for learning (async)
            print(f"📊 Message Router: Recording performance for learning")
            try:
                response_id = f"{channel_id}_{self.request_count}_{datetime.now().timestamp()}"
                performance_metrics = {
                    "quality_score": quality_score,
                    "authenticity_score": quality_metrics.get("authenticity_score", 8.0),
                    "engagement_score": quality_metrics.get("engagement_score", 7.0),
                    "response_time": 2.5  # Placeholder - could be actual measured time
                }
                
                self._make_service_request(
                    FINE_TUNING_URL,
                    "/record-performance",
                    method="POST",
                    data={
                        "response_id": response_id,
                        "character": selected_character,
                        "metrics": performance_metrics
                    },
                    timeout=5  # Short timeout for async operation
                )
            except Exception as e:
                print(f"⚠️ Message Router: Fine-tuning recording failed: {e}")
            
            # Step 9: Intelligent organic conversation analysis
            print(f"🧠 Message Router: Using LLM to analyze organic conversation opportunities")
            
            # Determine available characters for follow-up (exclude the one that just responded)
            all_characters = ["peter", "brian", "stewie"]
            available_for_followup = [char for char in all_characters if char != selected_character.lower()]
            
            organic_followup_triggered = False
            
            if available_for_followup:
                # Use intelligent LLM analysis instead of random chance
                organic_analysis_response = self._make_service_request(
                    CONVERSATION_COORDINATOR_URL,
                    "/analyze-organic-opportunity",
                    method="POST",
                    data={
                        "current_message": generated_response,
                        "current_character": selected_character.lower(),
                        "conversation_id": channel_id,
                        "available_characters": available_for_followup
                    }
                )
                
                if organic_analysis_response["success"]:
                    analysis = organic_analysis_response["data"]["analysis"]
                    should_respond = analysis.get("should_respond", False)
                    recommended_character = analysis.get("selected_character")
                    confidence = analysis.get("confidence", 0.0)
                    reasoning = analysis.get("reasoning", "No reason provided")
                    analysis_type = analysis.get("analysis_type", "unknown")
                    
                    print(f"🧠 Message Router: Organic analysis result:")
                    print(f"   Should respond: {should_respond}")
                    print(f"   Character: {recommended_character}")
                    print(f"   Confidence: {confidence:.2f}")
                    print(f"   Reasoning: {reasoning}")
                    print(f"   Analysis type: {analysis_type}")
                    
                    if should_respond and recommended_character and confidence > 0.3:
                        print(f"🌱 Message Router: LLM recommends {recommended_character} for organic follow-up (confidence: {confidence:.2f})")
                        organic_followup_triggered = True
                        
                        # Schedule the follow-up response (async way to trigger another bot)
                        try:
                            def trigger_followup_response():
                                # Check if we're already at max concurrent retries
                                if self.active_retry_threads >= self.max_concurrent_retries:
                                    print(f"⚠️ Message Router: Max concurrent retries ({self.max_concurrent_retries}) reached, skipping organic followup")
                                    return
                                
                                # Increment active retry counter
                                self.active_retry_threads += 1
                                
                                try:
                                    # Delay based on confidence (higher confidence = faster response)
                                    delay = max(2.0, 6.0 - (confidence * 4.0))
                                    time.sleep(random.uniform(delay, delay + 2))
                                    
                                    # Create follow-up conversation context
                                    followup_history = conversation_history + [{
                                        "role": "assistant",
                                        "content": generated_response,
                                        "character": selected_character,
                                        "timestamp": datetime.now().isoformat()
                                    }]
                                    
                                    # Define the organic follow-up generation operation
                                    def generate_organic_followup():
                                        # Generate follow-up using the selected character
                                        followup_data = {
                                            "input_text": f"[ORGANIC_FOLLOWUP] {generated_response}",
                                            "channel_id": channel_id,
                                            "user_id": "organic_system",
                                            "character_name": recommended_character,
                                            "conversation_history": followup_history
                                        }
                                        
                                        # Make call to generate follow-up
                                        followup_result = self.orchestrate_conversation(followup_data)
                                        if not followup_result["success"]:
                                            raise Exception(f"Follow-up generation failed: {followup_result.get('error')}")
                                        
                                        return followup_result["data"]["response"]
                                    
                                    # Define validation for organic messages
                                    def validate_organic_message(followup_response):
                                        if not followup_response:
                                            return False
                                        
                                        # Send to Discord bot service
                                        discord_result = self._send_organic_message_to_discord(
                                            recommended_character, 
                                            followup_response, 
                                            channel_id
                                        )
                                        
                                        # Only accept if Discord send was successful
                                        if discord_result["success"]:
                                            print(f"✅ Message Router: Organic follow-up sent to Discord by {recommended_character}")
                                            return True
                                        else:
                                            error_details = discord_result.get('error', 'Unknown error')
                                            status_code = discord_result.get('status_code')
                                            
                                            if status_code == 400:
                                                # Quality control failure - allow retry
                                                print(f"🔍 Message Router: Organic message failed quality control")
                                                print(f"   Error: {error_details}")
                                                return False  # Trigger retry
                                            else:
                                                # Other error (503, network, etc.) - don't retry from this level
                                                print(f"❌ Message Router: Non-retryable error sending organic follow-up: {error_details}")
                                                return True  # Accept failure without retry
                                    
                                    # Use centralized retry for organic follow-up (no retries to prevent explosion)
                                    success_response = retry_sync(
                                        operation=generate_organic_followup,
                                        validation_func=validate_organic_message,
                                        service_name="Message Router",
                                        **RetryConfig.ORGANIC_ANALYSIS
                                    )
                                    
                                    if success_response:
                                        print(f"✅ Message Router: Organic follow-up successfully sent by {recommended_character}")
                                    else:
                                        print(f"❌ Message Router: Organic follow-up attempt failed for {recommended_character}")
                                
                                finally:
                                    # Always decrement the active retry counter
                                    self.active_retry_threads -= 1
                            
                            # Start follow-up in background thread
                            followup_thread = threading.Thread(target=trigger_followup_response, daemon=True)
                            followup_thread.start()
                            print(f"🌱 Message Router: Scheduled intelligent organic follow-up by {recommended_character}")
                            
                        except Exception as e:
                            print(f"⚠️ Message Router: Failed to schedule follow-up: {e}")
                    else:
                        print(f"🧠 Message Router: LLM analysis determined no organic follow-up needed")
                        print(f"   Reason: {reasoning}")
                        
                else:
                    print(f"⚠️ Message Router: Organic analysis failed, falling back to no follow-up")
                    print(f"   Error: {organic_analysis_response.get('error')}")
            else:
                print(f"🌱 Message Router: No other characters available for follow-up")

            return {
                "success": True,
                "data": {
                    "response": generated_response,
                    "character": selected_character,
                    "quality_score": quality_score,
                    "rag_context_length": len(rag_context),
                    "conversation_id": channel_id,
                    "request_id": self.request_count,
                    "organic_followup_scheduled": organic_followup_triggered
                }
            }
            
        except Exception as e:
            self.error_count += 1
            print(f"❌ Message Router: Error in orchestration: {e}")
            print(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "request_id": self.request_count
            }
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all connected services."""
        # Core services
        services = {
            "llm_service": LLM_SERVICE_URL,
            "character_config": CHARACTER_CONFIG_URL,
            "rag_retriever": RAG_RETRIEVER_URL,
            "conversation_coordinator": CONVERSATION_COORDINATOR_URL,
            "quality_control": QUALITY_CONTROL_URL,
            "fine_tuning": FINE_TUNING_URL
        }
        
        health_status = {}
        overall_healthy = True
        
        for service_name, service_url in services.items():
            try:
                response = self._make_service_request(service_url, "/health", timeout=5)
                if response["success"]:
                    health_status[service_name] = {
                        "status": "healthy",
                        "response_time": "< 5s",
                        "last_check": datetime.now().isoformat()
                    }
                else:
                    health_status[service_name] = {
                        "status": "unhealthy",
                        "error": response["error"],
                        "last_check": datetime.now().isoformat()
                    }
                    overall_healthy = False
            except Exception as e:
                health_status[service_name] = {
                    "status": "unreachable",
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
                overall_healthy = False
        
        # Check KeyDB
        try:
            self.redis_client.ping()
            health_status["keydb"] = {
                "status": "healthy",
                "last_check": datetime.now().isoformat()
            }
        except Exception as e:
            health_status["keydb"] = {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }
            overall_healthy = False
        
        # Check cache
        if self.cache:
            try:
                test_key = "health_check"
                self.cache.set(test_key, "test", ttl=60)
                test_result = self.cache.get(test_key)
                cache_healthy = test_result == "test"
                self.cache.delete(test_key)
                
                health_status["cache"] = {
                    "status": "healthy" if cache_healthy else "unhealthy",
                    "last_check": datetime.now().isoformat()
                }
                if not cache_healthy:
                    overall_healthy = False
            except Exception as e:
                health_status["cache"] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.now().isoformat()
                }
                overall_healthy = False
        else:
            health_status["cache"] = {"status": "unavailable"}
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "services": health_status,
            "metrics": {
                "total_requests": self.request_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(self.request_count, 1) * 100
            },
            "timestamp": datetime.now().isoformat()
        }

# Global message router instance
message_router = MessageRouter()

# --- API Endpoints ---

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        health_status = message_router.get_service_health()
        status_code = 200 if health_status["status"] in ["healthy", "degraded"] else 503
        return jsonify(health_status), status_code
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/orchestrate', methods=['POST'])
def orchestrate_conversation():
    """Main orchestration endpoint for conversation handling."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        result = message_router.orchestrate_conversation(data)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"❌ Message Router: Error in orchestrate endpoint: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/services/health', methods=['GET'])
def get_services_health():
    """Get detailed health status of all services."""
    try:
        health_status = message_router.get_service_health()
        return jsonify(health_status), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get routing metrics."""
    try:
        return jsonify({
            "total_requests": message_router.request_count,
            "error_count": message_router.error_count,
            "error_rate": message_router.error_count / max(message_router.request_count, 1) * 100,
            "timestamp": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/organic-notification', methods=['POST'])
def handle_organic_notification():
    """Handle notifications from Discord bots about direct responses to trigger organic analysis."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        event_type = data.get("event_type")
        if event_type != "direct_response_sent":
            return jsonify({
                "success": False,
                "error": f"Unsupported event type: {event_type}"
            }), 400
        
        responding_character = data.get("responding_character")
        response_text = data.get("response_text")
        channel_id = data.get("channel_id")
        conversation_history = data.get("conversation_history", [])
        
        if not all([responding_character, response_text, channel_id]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: responding_character, response_text, channel_id"
            }), 400
        
        print(f"🔔 Message Router: Received organic notification from {responding_character} in channel {channel_id}")
        
        # Return success immediately and handle analysis in background
        return jsonify({
            "success": True,
            "message": "Organic analysis notification received"
        }), 200
            
    except Exception as e:
        print(f"❌ Message Router: Exception in organic notification handler: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    print(f"🔀 Message Router starting on port {MESSAGE_ROUTER_PORT}...")
    print(f"🔗 Connected services:")
    print(f"   - LLM Service: {LLM_SERVICE_URL}")
    print(f"   - Character Config: {CHARACTER_CONFIG_URL}")
    print(f"   - Conversation Coordinator: {CONVERSATION_COORDINATOR_URL}")
    print(f"   - Quality Control: {QUALITY_CONTROL_URL}")
    print(f"   - Fine-Tuning: {FINE_TUNING_URL}")
    print(f"   - RAG Retriever: {RAG_RETRIEVER_URL}")
    print(f"💾 Cache available: {CACHE_AVAILABLE}")
    app.run(host='0.0.0.0', port=MESSAGE_ROUTER_PORT, debug=False) 