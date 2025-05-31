import os
import asyncio
import requests
import traceback
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set, List
from flask import Flask, jsonify, request
from threading import Thread, Lock
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Load environment variables
load_dotenv()

# Configuration
BRIAN_DISCORD_PORT = int(os.getenv("BRIAN_DISCORD_PORT", "6012"))
DISCORD_BOT_TOKEN_BRIAN = os.getenv("DISCORD_BOT_TOKEN_BRIAN")
MESSAGE_ROUTER_URL = os.getenv("MESSAGE_ROUTER_URL", "http://message-router:6005")

# Flask app for health checks and API
app = Flask(__name__)

# Import centralized retry manager
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.retry_manager import retry_async, RetryConfig

# Import Redis for conversation history
import redis
import json

class BrianDiscordBot:
    """Brian Griffin Discord bot handler with spam protection."""
    
    def __init__(self):
        """Initialize the Brian Discord bot."""
        self.bot = None
        self.message_count = 0
        self.error_count = 0
        
        # Circuit breaker pattern for resilience
        self.consecutive_errors = 0
        self.last_error_time = None
        self.CIRCUIT_BREAKER_THRESHOLD = 5  # Errors before opening circuit
        self.CIRCUIT_BREAKER_TIMEOUT = 300  # 5 minutes timeout
        
        # Spam protection
        self.processed_messages: Set[str] = set()  # Message deduplication
        self.processing_lock = Lock()  # Prevent race conditions
        self.last_response_time: Dict[str, float] = {}  # Rate limiting per channel
        self.RATE_LIMIT_SECONDS = 2  # Minimum time between responses per channel
        self.MESSAGE_CACHE_SIZE = 1000  # Limit memory usage
        
        # Initialize KeyDB connection for conversation history
        self.redis_client = self._initialize_keydb()
        
        if not DISCORD_BOT_TOKEN_BRIAN:
            print("❌ Brian Discord: DISCORD_BOT_TOKEN_BRIAN not set!")
            return
            
        # Configure bot with intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(
            command_prefix='!brian ',
            intents=intents,
            description="Brian Griffin - Intellectual family dog"
        )
        
        self.setup_bot_events()
        
        # Start the Discord bot when the module is imported (for Gunicorn preload)
        self.start_discord_bot_background()
    
    def _get_message_hash(self, message) -> str:
        """Generate unique hash for message deduplication."""
        content = f"{message.id}:{message.channel.id}:{message.author.id}:{message.content}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_rate_limited(self, channel_id: str) -> bool:
        """Check if channel is rate limited."""
        now = time.time()
        last_time = self.last_response_time.get(channel_id, 0)
        return (now - last_time) < self.RATE_LIMIT_SECONDS
    
    def _update_rate_limit(self, channel_id: str):
        """Update rate limit timestamp for channel."""
        self.last_response_time[channel_id] = time.time()
    
    def _cleanup_old_messages(self):
        """Clean up old message hashes to prevent memory leaks."""
        if len(self.processed_messages) > self.MESSAGE_CACHE_SIZE:
            # Remove oldest 20% of messages
            to_remove = list(self.processed_messages)[:200]
            for msg_hash in to_remove:
                self.processed_messages.discard(msg_hash)

    def _record_error(self):
        """Record an error for circuit breaker pattern."""
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        self.error_count += 1
        
        if self.consecutive_errors >= self.CIRCUIT_BREAKER_THRESHOLD:
            print(f"🚨 Brian Discord: Circuit breaker OPEN - {self.consecutive_errors} consecutive errors")
            print(f"⏰ Brian Discord: Circuit will reset in {self.CIRCUIT_BREAKER_TIMEOUT} seconds")
        else:
            print(f"⚠️ Brian Discord: Error {self.consecutive_errors}/{self.CIRCUIT_BREAKER_THRESHOLD} until circuit breaker opens")

    def _is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is currently open."""
        if self.consecutive_errors < self.CIRCUIT_BREAKER_THRESHOLD:
            return False
        
        if self.last_error_time and (time.time() - self.last_error_time) > self.CIRCUIT_BREAKER_TIMEOUT:
            print("✅ Brian Discord: Circuit breaker CLOSED - timeout expired, resetting error count")
            self.consecutive_errors = 0
            return False
        
        return True
    
    def setup_bot_events(self):
        """Setup Discord bot event handlers."""
        
        @self.bot.event
        async def on_ready():
            print(f"🐕 Brian Discord Bot: Logged in as {self.bot.user}")
        
        @self.bot.event
        async def on_message(message):
            """Handle incoming Discord messages with spam protection."""
            # Ignore messages from bots
            if message.author.bot:
                return
            
            # Only respond to mentions or DMs
            if not (self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel)):
                return
            
            # Circuit breaker check
            if self._is_circuit_breaker_active():
                print(f"🚨 Brian Discord: Circuit breaker ACTIVE - ignoring message")
                return
            
            # Generate message hash for deduplication
            message_hash = self._get_message_hash(message)
            channel_id = str(message.channel.id)
            
            # Check for duplicate processing (CRITICAL SPAM PROTECTION)
            with self.processing_lock:
                if message_hash in self.processed_messages:
                    print(f"🚫 Brian Discord: Duplicate message detected, ignoring: {message_hash[:8]}")
                    return
                
                # Check rate limiting
                if self._is_rate_limited(channel_id):
                    print(f"⏱️ Brian Discord: Rate limited for channel {channel_id}")
                    return
                
                # Mark as processing
                self.processed_messages.add(message_hash)
                self._update_rate_limit(channel_id)
                self._cleanup_old_messages()
            
            try:
                self.message_count += 1
                print(f"🎯 Brian Discord: Processing message {message_hash[:8]} from {message.author}")
                
                # Clean the message content (remove mentions)
                content = message.content
                if self.bot.user.mentioned_in(message):
                    content = content.replace(f'<@{self.bot.user.id}>', '').strip()
                
                if not content:
                    print("⚠️ Brian Discord: Empty message content after cleaning")
                    return
                
                # Store user message in conversation history
                self._store_message_in_history(
                    channel_id=channel_id,
                    author=str(message.author),
                    content=content,
                    message_type="user"
                )
                
                # Get conversation history for context
                conversation_history = self._get_conversation_history(channel_id)
                
                # Create async function to handle the message
                async def generate_message():
                    # Send to message router
                    try:
                        response_data = await self.send_to_message_router(
                            input_text=content,
                            channel_id=channel_id,
                            user_id=str(message.author.id),
                            conversation_history=conversation_history
                        )
                        
                        if response_data and response_data.get('response'):
                            response_text = response_data['response']
                            
                            # Quality check before sending
                            quality_passed = await self.check_response_quality(response_text, content, channel_id)
                            
                            if quality_passed:
                                # Store Brian's response in conversation history
                                self._store_message_in_history(
                                    channel_id=channel_id,
                                    author="Brian Griffin",
                                    content=response_text,
                                    message_type="brian"
                                )
                                
                                # Send response to Discord
                                await message.channel.send(response_text)
                                print(f"✅ Brian Discord: Response sent to channel {channel_id}")
                                
                                # Reset error count on successful response
                                self.consecutive_errors = 0
                                
                                # Send organic notification for potential follow-up conversations
                                await self._notify_message_router_for_organic_analysis(
                                    response_sent=response_text,
                                    original_input=content,
                                    channel_id=channel_id,
                                    user_id=str(message.author.id),
                                    conversation_history=conversation_history
                                )
                                
                            else:
                                print(f"❌ Brian Discord: Response failed quality check for channel {channel_id}")
                                
                                # Generate fallback message
                                fallback_response = await self._generate_quality_fallback_message("quality_check_failed", content, channel_id)
                                if fallback_response:
                                    await message.channel.send(fallback_response)
                                    print(f"🔄 Brian Discord: Sent fallback response to channel {channel_id}")
                        else:
                            print(f"❌ Brian Discord: No response received from message router")
                            self._record_error()
                            
                    except Exception as e:
                        print(f"❌ Brian Discord: Error processing message: {e}")
                        print(f"📍 Brian Discord: Traceback: {traceback.format_exc()}")
                        self._record_error()
                
                # Execute async task
                await generate_message()
                
            except Exception as e:
                print(f"❌ Brian Discord: Unexpected error in message handler: {e}")
                print(f"📍 Brian Discord: Traceback: {traceback.format_exc()}")
                self._record_error()
                
                # Remove from processed messages if we failed to process
                self.processed_messages.discard(message_hash)

    async def check_response_quality(self, response: str, input_text: str, channel_id: str) -> bool:
        """Check response quality before sending to Discord."""
        try:
            quality_data = {
                "response": response,
                "original_input": input_text,
                "character": "brian",
                "conversation_context": {
                    "channel_id": channel_id,
                    "response_length": len(response),
                    "input_length": len(input_text)
                }
            }
            
            # Send to quality control service
            quality_response = requests.post(
                "http://quality-control:6003/validate-response",
                json=quality_data,
                timeout=10
            )
            
            if quality_response.status_code == 200:
                quality_result = quality_response.json()
                passed = quality_result.get('quality_passed', False)
                score = quality_result.get('quality_score', 0)
                
                print(f"🎯 Brian Discord: Quality check - Score: {score:.1f}, Passed: {passed}")
                return passed
            else:
                print(f"⚠️ Brian Discord: Quality service error: {quality_response.status_code}")
                return True  # Allow response if quality service is down
                
        except Exception as e:
            print(f"⚠️ Brian Discord: Quality check failed: {e}")
            return True  # Allow response if quality check fails

    async def _generate_quality_fallback_message(self, error_type: str, original_input: str, channel_id: str) -> Optional[str]:
        """Generate a fallback message when quality check fails."""
        try:
            fallback_data = {
                "character": "brian",
                "error_type": error_type,
                "original_input": original_input,
                "channel_id": channel_id
            }
            
            async def generate_fallback():
                try:
                    response = requests.post(
                        f"{MESSAGE_ROUTER_URL}/generate-fallback",
                        json=fallback_data,
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        return response.json().get('response')
                    else:
                        print(f"⚠️ Brian Discord: Fallback generation failed: {response.status_code}")
                        return "Well, this is embarrassing. Let me gather my thoughts and try again."
                        
                except Exception as e:
                    print(f"⚠️ Brian Discord: Fallback generation error: {e}")
                    return "Actually, let me reconsider that response. Give me a moment to think of something more... articulate."
            
            return await generate_fallback()
            
        except Exception as e:
            print(f"❌ Brian Discord: Failed to generate fallback: {e}")
            return "Hmm, let me approach this from a different intellectual angle."

    async def _notify_message_router_for_organic_analysis(self, response_sent: str, original_input: str, channel_id: str, user_id: str, conversation_history: list):
        """Notify message router about sent response for potential organic follow-ups."""
        try:
            notification_data = {
                "event_type": "direct_response_sent",
                "responding_character": "brian",
                "response_text": response_sent,
                "original_input": original_input,
                "channel_id": channel_id,
                "user_id": user_id,
                "conversation_history": conversation_history,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send asynchronously without blocking
            response = requests.post(
                f"{MESSAGE_ROUTER_URL}/organic-notification",
                json=notification_data,
                timeout=5  # Short timeout since this is fire-and-forget
            )
            
            if response.status_code == 200:
                print(f"✅ Brian Discord: Organic notification sent for channel {channel_id}")
            else:
                print(f"⚠️ Brian Discord: Organic notification failed: {response.status_code}")
                
        except requests.Timeout:
            print(f"⏱️ Brian Discord: Organic notification timeout for channel {channel_id}")
        except Exception as e:
            print(f"⚠️ Brian Discord: Organic notification error: {e}")

    @retry_async(RetryConfig(max_attempts=3, delay=1.0, backoff_multiplier=2.0))
    async def send_to_message_router(self, input_text: str, channel_id: str, user_id: str, conversation_history: list) -> Optional[Dict[str, Any]]:
        """Send message to message router with retry logic."""
        try:
            data = {
                "input_text": input_text,
                "character": "brian",
                "channel_id": channel_id,
                "user_id": user_id,
                "conversation_history": conversation_history,
                "source": "discord_brian"
            }
            
            print(f"📤 Brian Discord: Sending to message router - Channel: {channel_id}")
            
            response = requests.post(
                f"{MESSAGE_ROUTER_URL}/process-message",
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ Brian Discord: Received response from message router")
                return response_data
            else:
                print(f"❌ Brian Discord: Message router error: {response.status_code}")
                print(f"📄 Brian Discord: Response content: {response.text}")
                return None
                
        except requests.Timeout:
            print(f"⏱️ Brian Discord: Message router timeout")
            raise  # Let retry handle this
        except Exception as e:
            print(f"❌ Brian Discord: Error sending to message router: {e}")
            raise  # Let retry handle this

    def start_discord_bot_background(self):
        """Start Discord bot in background thread for Gunicorn compatibility."""
        def run_bot():
            try:
                print("🚀 Brian Discord: Starting bot in background...")
                asyncio.run(self.bot.start(DISCORD_BOT_TOKEN_BRIAN))
            except Exception as e:
                print(f"❌ Brian Discord: Failed to start bot: {e}")
                self.error_count += 1
        
        bot_thread = Thread(target=run_bot, daemon=True)
        bot_thread.start()
    
    def get_status(self) -> Dict[str, Any]:
        """Get bot status with thread-safe bot state checking."""
        # Check bot readiness dynamically rather than relying on is_running flag
        bot_ready = False
        bot_user_str = None
        
        if self.bot:
            try:
                # Check if bot is properly connected and has user info
                bot_ready = (
                    self.bot.user is not None and 
                    not self.bot.is_closed() and
                    self.bot.loop is not None and
                    not self.bot.loop.is_closed()
                )
                bot_user_str = str(self.bot.user) if self.bot.user else None
            except Exception as e:
                print(f"⚠️ Brian Discord: Error checking bot status: {e}")
                bot_ready = False
                bot_user_str = None
        
        return {
            "character": "Brian Griffin",
            "bot_ready": bot_ready,
            "bot_user": bot_user_str,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "circuit_breaker_active": self._is_circuit_breaker_active(),
            "token_configured": bool(DISCORD_BOT_TOKEN_BRIAN),
            "message_router_url": MESSAGE_ROUTER_URL,
            "timestamp": datetime.now().isoformat()
        }

    def _initialize_keydb(self):
        """Initialize KeyDB connection for conversation history"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://keydb:6379')
            if redis_url.startswith('redis://'):
                redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                host, port = redis_url.split(':')
                redis_client = redis.Redis(host=host, port=int(port), decode_responses=True)
            
            # Test connection
            redis_client.ping()
            print("✅ Brian Discord: Connected to KeyDB for conversation history")
            return redis_client
        except Exception as e:
            print(f"❌ Brian Discord: Failed to connect to KeyDB: {e}")
            return None
    
    def _store_message_in_history(self, channel_id: str, author: str, content: str, message_type: str = "user"):
        """Store message in conversation history."""
        if not self.redis_client:
            return
        
        try:
            # Create message record
            message_record = {
                "timestamp": datetime.now().isoformat(),
                "author": author,
                "content": content,
                "message_type": message_type,  # "user", "peter", "brian", "stewie"
                "channel_id": channel_id
            }
            
            # Store in ordered list for this channel
            history_key = f"conversation_history:{channel_id}"
            
            # Add message to the end of the list
            self.redis_client.lpush(history_key, json.dumps(message_record))
            
            # Keep only last 50 messages (trim list)
            self.redis_client.ltrim(history_key, 0, 49)
            
            # Set expiry for 24 hours
            self.redis_client.expire(history_key, 86400)
            
            print(f"💾 Brian Discord: Stored message in conversation history for channel {channel_id}")
            
        except Exception as e:
            print(f"⚠️ Brian Discord: Failed to store message in history: {e}")
    
    def _get_conversation_history(self, channel_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent conversation history for a channel."""
        if not self.redis_client:
            return []
        
        try:
            history_key = f"conversation_history:{channel_id}"
            
            # Get last 'limit' messages (they're stored in reverse order)
            raw_messages = self.redis_client.lrange(history_key, 0, limit - 1)
            
            # Parse and reverse to get chronological order
            messages = []
            for raw_msg in reversed(raw_messages):
                try:
                    message_data = json.loads(raw_msg)
                    
                    # Enhanced validation with specific error reporting
                    required_fields = ["message_type", "content", "timestamp"]
                    missing_fields = []
                    empty_fields = []
                    
                    for field in required_fields:
                        if field not in message_data:
                            missing_fields.append(field)
                        elif not message_data[field] or message_data[field] == "":
                            empty_fields.append(field)
                    
                    if missing_fields or empty_fields:
                        error_details = []
                        if missing_fields:
                            error_details.append(f"missing: {missing_fields}")
                        if empty_fields:
                            error_details.append(f"empty: {empty_fields}")
                        print(f"⚠️ Brian Discord: Skipping malformed message - {', '.join(error_details)}")
                        print(f"   Raw data: {message_data}")
                        continue
                    
                    # Convert to format expected by message router
                    formatted_message = {
                        "role": "assistant" if message_data["message_type"] in ["peter", "brian", "stewie"] else "user",
                        "content": message_data["content"],
                        "character": message_data["message_type"] if message_data["message_type"] in ["peter", "brian", "stewie"] else "user",
                        "timestamp": message_data["timestamp"]
                    }
                    messages.append(formatted_message)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"⚠️ Brian Discord: Skipping malformed message in history: {e}")
                    continue
            
            print(f"📚 Brian Discord: Retrieved {len(messages)} messages from conversation history for channel {channel_id}")
            return messages
            
        except Exception as e:
            print(f"⚠️ Brian Discord: Failed to retrieve conversation history: {e}")
            return []

# Global bot instance - starts automatically when imported
brian_bot = BrianDiscordBot()

# Flask endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        status = brian_bot.get_status()
        health_status = "healthy" if status["token_configured"] else "degraded"
        
        return jsonify({
            "status": health_status,
            "service": "Brian_Discord_Handler",
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
    """Get detailed bot status."""
    try:
        return jsonify(brian_bot.get_status()), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    """API endpoint to send messages (for testing)."""
    return jsonify({
        "message": "Brian Discord handler is running via Discord bot",
        "note": "Use Discord mentions or DMs to interact with Brian",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/organic-message', methods=['POST'])
def send_organic_message():
    """Receive and send organic follow-up messages from the message router."""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        message_text = data.get('message')
        channel_id = data.get('channel_id')
        is_organic = data.get('is_organic', True)  # Mark as organic by default
        
        if not message_text or not channel_id:
            return jsonify({
                "success": False, 
                "error": "Missing required fields: message, channel_id"
            }), 400
        
        print(f"🌱 Brian Discord: Received organic message for channel {channel_id} (organic: {is_organic})")
        
        # Store organic message in conversation history before sending
        brian_bot._store_message_in_history(
            channel_id=channel_id,
            author="Brian Griffin",
            content=message_text,
            message_type="brian"
        )
        
        # Send the message to Discord
        success = send_message_to_discord(message_text, channel_id)
        
        if success:
            print(f"✅ Brian Discord: Successfully sent organic message to channel {channel_id}")
            
            # Send organic notification to continue the conversation chain
            try:
                conversation_history = brian_bot._get_conversation_history(channel_id)
                
                notification_data = {
                    "event_type": "direct_response_sent",
                    "responding_character": "brian",
                    "response_text": message_text,
                    "original_input": message_text,  # For organic responses, use the response as context
                    "channel_id": channel_id,
                    "conversation_history": conversation_history,
                    "is_organic_chain": True  # Flag to indicate this is part of an organic chain
                }
                
                # Send notification to message router for continued organic analysis
                response = requests.post(
                    f"{MESSAGE_ROUTER_URL}/organic-notification",
                    json=notification_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    print(f"✅ Brian Discord: Organic chain notification sent to message router")
                else:
                    print(f"⚠️ Brian Discord: Organic chain notification failed: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️ Brian Discord: Failed to send organic chain notification: {e}")
            
            return jsonify({"success": True, "message": "Organic message sent successfully"})
        else:
            print(f"❌ Brian Discord: Failed to send organic message to channel {channel_id}")
            return jsonify({"success": False, "error": "Failed to send message to Discord"}), 500
        
    except Exception as e:
        print(f"❌ Brian Discord: Error in organic message endpoint: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def send_message_to_discord(message_text: str, channel_id: str) -> bool:
    """Send a message to Discord via the Brian bot."""
    try:
        if not brian_bot.bot or not brian_bot.bot.user or brian_bot.bot.is_closed():
            print(f"❌ Brian Discord: Bot not ready for message sending")
            return False
        
        # Create async function to send message
        async def send_message():
            try:
                channel = brian_bot.bot.get_channel(int(channel_id))
                if channel:
                    await channel.send(message_text)
                    print(f"✅ Brian Discord: Message sent to channel {channel_id}")
                    return True
                else:
                    print(f"❌ Brian Discord: Channel {channel_id} not found")
                    return False
            except Exception as e:
                print(f"❌ Brian Discord: Error sending message: {e}")
                return False
        
        # Get the bot's event loop and schedule the coroutine
        loop = brian_bot.bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(send_message(), loop)
            success = future.result(timeout=10)  # Wait up to 10 seconds
            return success
        else:
            print(f"❌ Brian Discord: Bot event loop not available")
            return False
            
    except Exception as e:
        print(f"❌ Brian Discord: Exception in send_message_to_discord: {e}")
        return False

# No Flask development server code needed - Gunicorn handles this
if __name__ == '__main__':
    print(f"🐕 Brian Discord Handler starting on port {BRIAN_DISCORD_PORT}...")
    print(f"🔗 Message Router URL: {MESSAGE_ROUTER_URL}")
    print(f"🔐 Token configured: {bool(DISCORD_BOT_TOKEN_BRIAN)}")
    print("⚠️  This should only run in development. Use Gunicorn for production.") 