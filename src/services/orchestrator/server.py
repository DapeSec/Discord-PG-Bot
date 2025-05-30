#!/usr/bin/env python3
"""
Organic Conversation Orchestrator Service

A dedicated microservice for managing organic conversations between Discord bots.
Monitors conversation flow, detects opportunities for natural interactions,
and triggers follow-up conversations between characters.
"""

import os
import time
import threading
import traceback
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import redis
import json
import requests
from typing import Dict, List, Any, Optional

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "6008"))
REDIS_URL = os.getenv("REDIS_URL", "redis://keydb:6379")
MESSAGE_ROUTER_URL = os.getenv("MESSAGE_ROUTER_URL", "http://message-router:6005")

# Service URLs for dynamic content generation
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:6001")
RAG_RETRIEVER_URL = os.getenv("RAG_RETRIEVER_URL", "http://rag-retriever:6007")

# Organic conversation configuration
MIN_TIME_BETWEEN_ORGANIC = int(os.getenv("MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS", "5"))  # minutes
CONVERSATION_SILENCE_THRESHOLD = int(os.getenv("CONVERSATION_SILENCE_THRESHOLD_MINUTES", "15"))  # minutes
ORGANIC_CONVERSATION_PROBABILITY = float(os.getenv("ORGANIC_CONVERSATION_PROBABILITY", "0.4"))

# Discord bot service URLs
DISCORD_BOT_SERVICES = {
    "peter": f"http://peter-discord:6011/organic-message",
    "brian": f"http://brian-discord:6012/organic-message", 
    "stewie": f"http://stewie-discord:6013/organic-message"
}

# Service name
SERVICE_NAME = "Organic Conversation Orchestrator"

class OrganicConversationOrchestrator:
    """Manages organic conversations between Discord bots."""
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.redis_client = None
        self.monitor_thread = None
        self.running = False
        self.conversation_count = 0
        self.organic_conversations_initiated = 0
        
        # Character personality traits for conversation selection
        self.character_traits = {
            "peter": {
                "initiation_probability": 0.5,
                "response_probability": 0.7,
                "topics": ["food", "tv", "work", "beer", "sports", "family"]
            },
            "brian": {
                "initiation_probability": 0.3,
                "response_probability": 0.6,
                "topics": ["politics", "literature", "philosophy", "culture", "writing"]
            },
            "stewie": {
                "initiation_probability": 0.4,
                "response_probability": 0.6, 
                "topics": ["science", "plans", "technology", "intelligence", "superiority"]
            }
        }
        
        # Initialize Redis connection
        self._initialize_redis()
        
        # Start monitoring thread
        self._start_monitor_thread()
    
    def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            print(f"{SERVICE_NAME} - Connected to Redis")
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: Could not connect to Redis: {e}")
            self.redis_client = None
    
    def _start_monitor_thread(self):
        """Start the conversation monitoring thread."""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_conversations, daemon=True)
        self.monitor_thread.start()
        print(f"{SERVICE_NAME} - Started conversation monitoring thread")
    
    def _monitor_conversations(self):
        """Monitor conversations and trigger organic responses."""
        print(f"{SERVICE_NAME} - Starting conversation monitoring...")
        
        while self.running:
            try:
                # Check for organic conversation opportunities
                if self._should_initiate_organic_conversation():
                    self._initiate_organic_conversation()
                
                # Sleep for a bit before checking again
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"{SERVICE_NAME} - Error in monitor thread: {e}")
                time.sleep(60)  # Continue monitoring even after errors
    
    def _should_initiate_organic_conversation(self) -> bool:
        """Determine if we should initiate an organic conversation."""
        if not self.redis_client:
            return False
        
        try:
            # Check time since last organic conversation
            last_organic_key = "orchestrator:last_organic_conversation"
            last_organic_time = self.redis_client.get(last_organic_key)
            
            if last_organic_time:
                last_time = datetime.fromisoformat(last_organic_time)
                time_since_last = datetime.now() - last_time
                
                if time_since_last.total_seconds() < (MIN_TIME_BETWEEN_ORGANIC * 60):
                    return False
            
            # Check for recent conversation activity
            activity_key = "orchestrator:recent_activity"
            recent_activity = self.redis_client.get(activity_key)
            
            if recent_activity:
                last_activity = datetime.fromisoformat(recent_activity)
                silence_time = datetime.now() - last_activity
                
                # If there's been silence for the threshold time, consider starting
                if silence_time.total_seconds() >= (CONVERSATION_SILENCE_THRESHOLD * 60):
                    # Random probability check
                    return random.random() < ORGANIC_CONVERSATION_PROBABILITY
            
            return False
            
        except Exception as e:
            print(f"{SERVICE_NAME} - Error checking conversation conditions: {e}")
            return False
    
    def _initiate_organic_conversation(self):
        """Initiate an organic conversation between bots."""
        try:
            print(f"{SERVICE_NAME} - Initiating organic conversation...")
            
            # Select a character to start the conversation
            initiator = self._select_conversation_initiator()
            if not initiator:
                print(f"{SERVICE_NAME} - No suitable conversation initiator found")
                return
            
            # Generate conversation starter
            conversation_starter = self._generate_conversation_starter(initiator)
            
            # Get a default channel (you might want to make this configurable)
            default_channel = os.getenv("DEFAULT_DISCORD_CHANNEL_ID")
            if not default_channel:
                print(f"{SERVICE_NAME} - No default Discord channel configured")
                return
            
            # Send the organic message
            success = self._send_organic_message(initiator, conversation_starter, default_channel)
            
            if success:
                self.organic_conversations_initiated += 1
                
                # Update last organic conversation time
                if self.redis_client:
                    self.redis_client.set(
                        "orchestrator:last_organic_conversation",
                        datetime.now().isoformat(),
                        ex=86400  # 24 hour expiry
                    )
                
                print(f"{SERVICE_NAME} - Successfully initiated organic conversation with {initiator}")
                
                # Schedule follow-up responses
                self._schedule_followup_responses(initiator, conversation_starter, default_channel)
            else:
                print(f"{SERVICE_NAME} - Failed to send organic message")
                
        except Exception as e:
            print(f"{SERVICE_NAME} - Error initiating organic conversation: {e}")
            print(traceback.format_exc())
    
    def _select_conversation_initiator(self) -> Optional[str]:
        """Select which character should initiate the conversation."""
        characters = list(self.character_traits.keys())
        
        # Weight selection by initiation probability
        weighted_characters = []
        for char in characters:
            prob = self.character_traits[char]["initiation_probability"]
            # Add character multiple times based on probability
            count = int(prob * 10)
            weighted_characters.extend([char] * count)
        
        if weighted_characters:
            return random.choice(weighted_characters)
        
        return random.choice(characters)  # Fallback
    
    def _generate_conversation_starter(self, character: str) -> str:
        """Generate a dynamic conversation starter using LLM and RAG services."""
        try:
            # Get character traits for context
            traits = self.character_traits.get(character, {})
            topics = traits.get("topics", [])
            
            # Try to get relevant context from RAG retriever
            rag_context = self._get_rag_context(character, topics)
            
            # Generate dynamic starter using LLM service
            dynamic_starter = self._generate_llm_starter(character, topics, rag_context)
            
            if dynamic_starter:
                print(f"{SERVICE_NAME} - Generated dynamic starter for {character}: {dynamic_starter[:50]}...")
                return dynamic_starter
            else:
                # Fallback to static starters if LLM generation fails
                print(f"{SERVICE_NAME} - LLM generation failed, using fallback starter for {character}")
                return self._get_fallback_starter(character)
                
        except Exception as e:
            print(f"{SERVICE_NAME} - Error generating conversation starter: {e}")
            return self._get_fallback_starter(character)
    
    def _get_rag_context(self, character: str, topics: List[str]) -> Optional[str]:
        """Get relevant context from RAG retriever for conversation starter."""
        try:
            # Create search queries based on character and topics
            search_queries = [
                f"{character} Griffin Family Guy",
                f"{character} {' '.join(topics[:2])}" if topics else f"{character} conversation"
            ]
            
            context_parts = []
            
            for query in search_queries:
                try:
                    response = requests.post(
                        f"{RAG_RETRIEVER_URL}/search",
                        json={
                            "query": query,
                            "top_k": 2,
                            "threshold": 0.3
                        },
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success") and data.get("results"):
                            for result in data["results"][:1]:  # Take top result
                                if result.get("content"):
                                    context_parts.append(result["content"][:200])  # Limit context length
                except requests.exceptions.RequestException:
                    continue  # Skip failed requests
            
            return " ".join(context_parts) if context_parts else None
            
        except Exception as e:
            print(f"{SERVICE_NAME} - Error getting RAG context: {e}")
            return None
    
    def _generate_llm_starter(self, character: str, topics: List[str], rag_context: Optional[str]) -> Optional[str]:
        """Generate conversation starter using LLM service."""
        try:
            # Build character-specific prompt
            character_prompts = {
                "peter": {
                    "personality": "Peter Griffin from Family Guy - loud, enthusiastic, often confused but well-meaning father who loves food, TV, and beer",
                    "style": "casual, energetic, often starts with 'Holy crap!' or 'Oh man!', references random experiences"
                },
                "brian": {
                    "personality": "Brian Griffin from Family Guy - intellectual, sophisticated talking dog who is cultured and philosophical",
                    "style": "articulate, thoughtful, often references literature or politics, slightly pretentious"
                },
                "stewie": {
                    "personality": "Stewie Griffin from Family Guy - evil genius baby with sophisticated vocabulary and condescending attitude",
                    "style": "condescending, verbose, sophisticated vocabulary, often dismissive of others' intelligence"
                }
            }
            
            char_info = character_prompts.get(character.lower(), character_prompts["peter"])
            topics_str = ", ".join(topics) if topics else "general conversation"
            
            # Build the prompt
            prompt = f"""You are {char_info['personality']}.

Your speaking style: {char_info['style']}

Your interests include: {topics_str}

"""
            
            if rag_context:
                prompt += f"Some relevant context/memories: {rag_context}\n\n"
            
            prompt += f"""Generate a natural conversation starter that {character} would say to initiate an organic conversation with other Family Guy characters. The starter should:

1. Be authentic to {character}'s personality and speaking style
2. Be engaging and likely to get responses from other characters
3. Be 1-2 sentences maximum
4. Feel natural and spontaneous (not forced)
5. NOT be a question (make it a statement or observation that others might respond to)

Just return the conversation starter, nothing else:"""

            # Call LLM service
            response = requests.post(
                f"{LLM_SERVICE_URL}/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": 100,
                    "temperature": 0.8,
                    "character_name": character
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("response"):
                    starter = data["response"].strip()
                    
                    # Clean up the response (remove quotes, extra formatting)
                    starter = starter.strip('"\'')
                    if starter.startswith(f"{character}:"):
                        starter = starter.replace(f"{character}:", "").strip()
                    
                    # Validate length (not too long)
                    if len(starter) <= 300 and len(starter) >= 10:
                        return starter
                    else:
                        print(f"{SERVICE_NAME} - Generated starter too long/short for {character}: {len(starter)} chars")
            else:
                print(f"{SERVICE_NAME} - LLM service returned {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"{SERVICE_NAME} - LLM service timeout")
        except requests.exceptions.ConnectionError:
            print(f"{SERVICE_NAME} - Cannot connect to LLM service")
        except Exception as e:
            print(f"{SERVICE_NAME} - Error calling LLM service: {e}")
        
        return None
    
    def _get_fallback_starter(self, character: str) -> str:
        """Get fallback static conversation starter if LLM generation fails."""
        fallback_starters = {
            "peter": [
                "Holy crap, you guys! You know what I just realized?",
                "Oh man, this reminds me of that time when...",
                "Hey, speaking of crazy stuff...",
                "You know what really grinds my gears?",
                "Oh! Oh! Guys, I got a great idea!"
            ],
            "brian": [
                "Well, that's an interesting perspective...",
                "You know, this actually reminds me of something Nietzsche once wrote...",
                "I've been thinking about this lately...",
                "From a philosophical standpoint...",
                "Actually, there's a fascinating parallel here..."
            ],
            "stewie": [
                "Good Lord, the intellectual deficiency in this conversation is staggering...",
                "Well, well, well... how delightfully pedestrian...",
                "Oh please, you're all missing the obvious point here...",
                "Fascinating... in the most banal way possible...",
                "Allow me to enlighten you simpletons..."
            ]
        }
        
        starters = fallback_starters.get(character, fallback_starters["peter"])
        return random.choice(starters)
    
    def _send_organic_message(self, character: str, message: str, channel_id: str) -> bool:
        """Send an organic message via the appropriate Discord bot."""
        try:
            discord_service_url = DISCORD_BOT_SERVICES.get(character)
            if not discord_service_url:
                print(f"{SERVICE_NAME} - No Discord service URL for character: {character}")
                return False
            
            data = {
                "message": message,
                "channel_id": channel_id
            }
            
            response = requests.post(discord_service_url, json=data, timeout=10)
            
            if response.status_code == 200:
                print(f"{SERVICE_NAME} - Sent organic message via {character}")
                return True
            else:
                print(f"{SERVICE_NAME} - Failed to send organic message: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"{SERVICE_NAME} - Error sending organic message: {e}")
            return False
    
    def _schedule_followup_responses(self, initiator: str, starter_message: str, channel_id: str):
        """Schedule follow-up responses from other characters."""
        other_characters = [char for char in self.character_traits.keys() if char != initiator]
        
        def trigger_followups():
            try:
                # Wait a bit for the initial message to be processed
                time.sleep(random.uniform(3, 8))
                
                for char in other_characters:
                    # Check if this character should respond
                    response_prob = self.character_traits[char]["response_probability"]
                    if random.random() < response_prob:
                        # Generate response through message router
                        self._generate_character_response(char, starter_message, channel_id)
                        
                        # Random delay between responses
                        time.sleep(random.uniform(2, 6))
                
            except Exception as e:
                print(f"{SERVICE_NAME} - Error in follow-up responses: {e}")
        
        # Start follow-up thread
        followup_thread = threading.Thread(target=trigger_followups, daemon=True)
        followup_thread.start()
    
    def _generate_character_response(self, character: str, context_message: str, channel_id: str):
        """Generate a response from a character to the organic conversation."""
        try:
            # Call message router to generate response
            data = {
                "character_name": character,
                "input_text": f"[ORGANIC_RESPONSE] {context_message}",
                "channel_id": channel_id,
                "user_id": "organic_system",
                "conversation_history": []
            }
            
            response = requests.post(f"{MESSAGE_ROUTER_URL}/orchestrate", json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    character_response = result["data"]["response"]
                    
                    # Send the response through Discord
                    self._send_organic_message(character, character_response, channel_id)
                    print(f"{SERVICE_NAME} - Generated organic response from {character}")
                else:
                    print(f"{SERVICE_NAME} - Message router failed for {character}: {result.get('error')}")
            else:
                print(f"{SERVICE_NAME} - Message router returned {response.status_code} for {character}")
                
        except Exception as e:
            print(f"{SERVICE_NAME} - Error generating character response: {e}")
    
    def record_conversation_activity(self, channel_id: str, character: str, message: str):
        """Record conversation activity for monitoring."""
        if self.redis_client:
            try:
                # Update recent activity timestamp
                self.redis_client.set(
                    "orchestrator:recent_activity",
                    datetime.now().isoformat(),
                    ex=3600  # 1 hour expiry
                )
                
                # Store conversation record
                activity_record = {
                    "timestamp": datetime.now().isoformat(),
                    "channel_id": channel_id,
                    "character": character,
                    "message_length": len(message),
                    "is_organic": "organic" in message.lower()
                }
                
                activity_key = f"orchestrator:activity:{channel_id}:{datetime.now().timestamp()}"
                self.redis_client.hset(activity_key, mapping=activity_record)
                self.redis_client.expire(activity_key, 86400)  # 24 hours
                
                self.conversation_count += 1
                
            except Exception as e:
                print(f"{SERVICE_NAME} - Error recording activity: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "service": SERVICE_NAME,
            "running": self.running,
            "monitor_thread_alive": self.monitor_thread.is_alive() if self.monitor_thread else False,
            "redis_connected": bool(self.redis_client),
            "conversation_count": self.conversation_count,
            "organic_conversations_initiated": self.organic_conversations_initiated,
            "configuration": {
                "min_time_between_organic_minutes": MIN_TIME_BETWEEN_ORGANIC,
                "silence_threshold_minutes": CONVERSATION_SILENCE_THRESHOLD,
                "organic_probability": ORGANIC_CONVERSATION_PROBABILITY
            },
            "timestamp": datetime.now().isoformat()
        }

# Global orchestrator instance
orchestrator = OrganicConversationOrchestrator()

# --- API Endpoints ---

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        status = orchestrator.get_status()
        health_status = "healthy" if status["running"] and status["redis_connected"] else "degraded"
        
        return jsonify({
            "status": health_status,
            **status
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/status', methods=['GET'])
def get_status():
    """Get detailed orchestrator status."""
    try:
        return jsonify(orchestrator.get_status()), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/record-activity', methods=['POST'])
def record_activity():
    """Record conversation activity."""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        channel_id = data.get('channel_id')
        character = data.get('character')
        message = data.get('message', '')
        
        if not channel_id or not character:
            return jsonify({
                "success": False,
                "error": "Missing required fields: channel_id, character"
            }), 400
        
        orchestrator.record_conversation_activity(channel_id, character, message)
        
        return jsonify({
            "success": True,
            "message": "Activity recorded"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/trigger-organic', methods=['POST'])
def trigger_organic_conversation():
    """Manually trigger an organic conversation."""
    try:
        # Force trigger an organic conversation
        orchestrator._initiate_organic_conversation()
        
        return jsonify({
            "success": True,
            "message": "Organic conversation triggered"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/test-starter', methods=['POST'])
def test_conversation_starter():
    """Test conversation starter generation for a specific character."""
    try:
        data = request.json or {}
        character = data.get('character', 'peter').lower()
        
        if character not in orchestrator.character_traits:
            return jsonify({
                "success": False,
                "error": f"Unknown character: {character}. Available: {list(orchestrator.character_traits.keys())}"
            }), 400
        
        # Generate a test conversation starter
        starter = orchestrator._generate_conversation_starter(character)
        
        return jsonify({
            "success": True,
            "character": character,
            "conversation_starter": starter,
            "generation_method": "dynamic_llm" if "Holy crap" not in starter and "Well, that's" not in starter and "Good Lord" not in starter else "fallback_static"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print(f"🌱 {SERVICE_NAME} starting on port {ORCHESTRATOR_PORT}...")
    print(f"🔗 Message Router URL: {MESSAGE_ROUTER_URL}")
    print(f"⚙️ Configuration:")
    print(f"   - Min time between organic: {MIN_TIME_BETWEEN_ORGANIC} minutes")
    print(f"   - Silence threshold: {CONVERSATION_SILENCE_THRESHOLD} minutes") 
    print(f"   - Organic probability: {ORGANIC_CONVERSATION_PROBABILITY}")
    app.run(host='0.0.0.0', port=ORCHESTRATOR_PORT, debug=False) 