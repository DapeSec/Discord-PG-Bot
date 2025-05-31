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
STEWIE_DISCORD_PORT = int(os.getenv("STEWIE_DISCORD_PORT", "6013"))
DISCORD_BOT_TOKEN_STEWIE = os.getenv("DISCORD_BOT_TOKEN_STEWIE")
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

class StewieDiscordBot:
    """Stewie Griffin Discord bot handler with spam protection."""
    
    def __init__(self):
        """Initialize the Stewie Discord bot."""
        self.bot = None
        self.message_count = 0
        self.error_count = 0
        
        # Spam protection
        self.processed_messages: Set[str] = set()  # Message deduplication
        self.processing_lock = Lock()  # Prevent race conditions
        self.last_response_time: Dict[str, float] = {}  # Rate limiting per channel
        self.RATE_LIMIT_SECONDS = 2  # Minimum time between responses per channel
        self.MESSAGE_CACHE_SIZE = 1000  # Limit memory usage
        
        # Initialize KeyDB connection for conversation history
        self.redis_client = self._initialize_keydb()
        
        if not DISCORD_BOT_TOKEN_STEWIE:
            print("❌ Stewie Discord: DISCORD_BOT_TOKEN_STEWIE not set!")
            return
            
        # Configure bot with intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(
            command_prefix='!stewie ',
            intents=intents,
            description="Stewie Griffin - evil genius baby from Family Guy"
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
    
    def setup_bot_events(self):
        """Setup Discord bot event handlers."""
        
        @self.bot.event
        async def on_ready():
            print(f"👶 Stewie Discord Bot: Logged in as {self.bot.user}")
        
        @self.bot.event
        async def on_message(message):
            """Handle incoming Discord messages with spam protection."""
            # Ignore messages from bots
            if message.author.bot:
                return
            
            # Only respond to mentions or DMs
            if not (self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel)):
                return
            
            # Generate message hash for deduplication
            message_hash = self._get_message_hash(message)
            channel_id = str(message.channel.id)
            
            # Check for duplicate processing (CRITICAL SPAM PROTECTION)
            with self.processing_lock:
                if message_hash in self.processed_messages:
                    print(f"🚫 Stewie Discord: Duplicate message detected, ignoring: {message_hash[:8]}")
                    return
                
                # Check rate limiting
                if self._is_rate_limited(channel_id):
                    print(f"⏱️ Stewie Discord: Rate limited for channel {channel_id}")
                    return
                
                # Mark as processing
                self.processed_messages.add(message_hash)
                self._update_rate_limit(channel_id)
                self._cleanup_old_messages()
            
            try:
                self.message_count += 1
                print(f"🎯 Stewie Discord: Processing message {message_hash[:8]} from {message.author}")
                
                # Clean the message content (remove mentions)
                content = message.content
                if self.bot.user.mentioned_in(message):
                    content = content.replace(f'<@{self.bot.user.id}>', '').strip()
                
                # Store user message in conversation history
                self._store_message_in_history(
                    channel_id=channel_id,
                    author=str(message.author),
                    content=content,
                    message_type="user"
                )
                
                # Send typing indicator
                async with message.channel.typing():
                    # Get conversation history from KeyDB
                    conversation_history = self._get_conversation_history(channel_id, limit=15)
                    
                    # Define the message generation operation
                    async def generate_message():
                        # Send to message router
                        response = await self.send_to_message_router(
                            input_text=content,
                            channel_id=channel_id,
                            user_id=str(message.author.id),
                            conversation_history=conversation_history
                        )
                        
                        if not response or not response.get("success"):
                            error_msg = response.get("error", "Unknown error") if response else "No response"
                            raise Exception(f"Message router error: {error_msg}")
                        
                        return response["data"]["response"]
                    
                    # Use centralized retry for message generation (removed quality validation to fix asyncio errors)
                    stewie_response = await retry_async(
                        operation=generate_message,
                        service_name="Stewie Discord",
                        **RetryConfig.DISCORD_MESSAGE
                    )
                    
                    if stewie_response:
                        # Store Stewie's response in conversation history
                        self._store_message_in_history(
                            channel_id=channel_id,
                            author="Stewie Griffin",
                            content=stewie_response,
                            message_type="stewie"
                        )
                        
                        # Success - send message and notify for organic analysis
                        await message.channel.send(stewie_response)
                        print(f"✅ Stewie Discord: Successfully sent response")
                        
                        # OPTION 3: Notify message router for organic conversation analysis
                        await self._notify_message_router_for_organic_analysis(
                            stewie_response, content, channel_id, str(message.author.id), conversation_history
                        )
                    else:
                        # All retries failed - generate a quality-controlled fallback message
                        print(f"❌ Stewie Discord: All attempts failed, generating fallback")
                        fallback_message = await self._generate_quality_fallback_message("quality_failure", content, channel_id)
                        if fallback_message:
                            await message.channel.send(fallback_message)
                        else:
                            # Ultimate fallback if even error generation fails
                            await message.channel.send("*raises eyebrow skeptically*")
                        self.error_count += 1
            
            except Exception as e:
                self.error_count += 1
                print(f"❌ Stewie Discord: Exception handling message {message_hash[:8]}: {e}")
                print(traceback.format_exc())
                try:
                    fallback_message = await self._generate_quality_fallback_message("system_error", content, channel_id)
                    if fallback_message:
                        await message.channel.send(fallback_message)
                    else:
                        # Ultimate fallback if even error generation fails
                        await message.channel.send("*looks utterly bemused*")
                except:
                    print("❌ Stewie Discord: Failed to send error message")
            
            finally:
                # Ensure message is marked as processed even if there's an error
                with self.processing_lock:
                    self.processed_messages.add(message_hash)
    
    async def check_response_quality(self, response: str, input_text: str, channel_id: str) -> bool:
        """Check if the response meets quality standards."""
        try:
            # Make request to quality control service
            loop = asyncio.get_event_loop()
            quality_response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    "http://quality-control:6003/analyze",
                    json={
                        "response": response,
                        "character": "stewie",
                        "conversation_id": channel_id,
                        "context": input_text,
                        "last_speaker": "user"
                    },
                    timeout=10
                )
            )
            
            if quality_response.status_code == 200:
                quality_data = quality_response.json()
                quality_passed = quality_data.get("quality_check_passed", True)
                quality_score = quality_data.get("overall_score", 85)
                
                print(f"📊 Stewie Discord: Quality check - Score: {quality_score}, Passed: {quality_passed}")
                return quality_passed
            else:
                print(f"⚠️ Stewie Discord: Quality control service unavailable, allowing response")
                return True  # Default to allowing if service unavailable
                
        except Exception as e:
            print(f"⚠️ Stewie Discord: Quality check failed: {e}")
            return True  # Default to allowing if check fails
    
    async def _generate_quality_fallback_message(self, error_type: str, original_input: str, channel_id: str) -> Optional[str]:
        """Generate a quality-controlled fallback message for errors."""
        try:
            # Define error-specific prompts for Stewie
            error_prompts = {
                "quality_failure": "Respond as Stewie Griffin when you're intellectually frustrated by a difficult topic. Be brief, precociously intelligent Stewie, and show sophisticated annoyance.",
                "connection_error": "Respond as Stewie Griffin when some technology or system isn't working properly. Be brief, precociously intelligent Stewie, and show disdain for inferior technology.",
                "system_error": "Respond as Stewie Griffin when something unexpected and confusing happened. Be brief, precociously intelligent Stewie, and show intellectual bewilderment."
            }
            
            prompt = error_prompts.get(error_type, error_prompts["system_error"])
            
            # Define the fallback generation operation
            async def generate_fallback():
                fallback_response = await self.send_to_message_router(
                    input_text=f"[ERROR_FALLBACK_{error_type.upper()}] {original_input}",
                    channel_id=channel_id,
                    user_id="system_fallback",
                    conversation_history=[{
                        "role": "system", 
                        "content": prompt
                    }]
                )
                
                if not fallback_response or not fallback_response.get("success"):
                    raise Exception("Fallback generation failed")
                
                return fallback_response["data"]["response"]
            
            # Use centralized retry for fallback generation (no retries to prevent cascading)
            fallback_text = await retry_async(
                operation=generate_fallback,
                service_name="Stewie Discord",
                **RetryConfig.FALLBACK_GENERATION
            )
            
            if fallback_text:
                print(f"✅ Stewie Discord: Generated quality fallback message")
                return fallback_text
            else:
                print(f"❌ Stewie Discord: Fallback generation failed")
                return None
            
        except Exception as e:
            print(f"❌ Stewie Discord: Error in fallback generation: {e}")
            return None
    
    async def _notify_message_router_for_organic_analysis(self, response_sent: str, original_input: str, channel_id: str, user_id: str, conversation_history: list):
        """Notify message router that a direct response was sent, triggering organic conversation analysis."""
        try:
            # Create updated conversation history with the response we just sent
            updated_history = conversation_history + [{
                "role": "assistant",
                "content": response_sent,
                "character": "stewie",
                "timestamp": datetime.now().isoformat()
            }]
            
            # Send notification to message router for organic analysis
            notification_data = {
                "event_type": "direct_response_sent",
                "responding_character": "stewie",
                "response_text": response_sent,
                "original_input": original_input,
                "channel_id": channel_id,
                "user_id": user_id,
                "conversation_history": updated_history,
                "trigger_organic_analysis": True
            }
            
            # Make async request to message router
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{MESSAGE_ROUTER_URL}/organic-notification",
                    json=notification_data,
                    timeout=5  # Short timeout for async notification
                )
            )
            
            if response.status_code == 200:
                print(f"✅ Stewie Discord: Organic analysis notification sent to message router")
            else:
                print(f"⚠️ Stewie Discord: Organic notification failed: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Stewie Discord: Failed to send organic notification: {e}")
    
    async def send_to_message_router(self, input_text: str, channel_id: str, user_id: str, conversation_history: list) -> Optional[Dict[str, Any]]:
        """Send message to the message router service."""
        try:
            data = {
                "character_name": "Stewie",
                "input_text": input_text,
                "channel_id": channel_id,
                "user_id": user_id,
                "conversation_history": conversation_history
            }
            
            # Use asyncio to make non-blocking HTTP request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(f"{MESSAGE_ROUTER_URL}/orchestrate", json=data, timeout=30)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Stewie Discord: Message router returned {response.status_code}")
                # Try to parse JSON error response even for non-200 status codes
                try:
                    error_data = response.json()
                    return error_data  # Return the full error response including quality control info
                except:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            print("❌ Stewie Discord: Message router timeout")
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            print("❌ Stewie Discord: Cannot connect to message router")
            return {"success": False, "error": "Connection failed"}
        except Exception as e:
            print(f"❌ Stewie Discord: Exception sending to message router: {e}")
            return {"success": False, "error": str(e)}
    
    def start_discord_bot_background(self):
        """Start Discord bot in background thread."""
        if not self.bot or not DISCORD_BOT_TOKEN_STEWIE:
            return
        
        def run_bot():
            try:
                print("🚀 Stewie Discord: Starting bot in background...")
                asyncio.run(self.bot.start(DISCORD_BOT_TOKEN_STEWIE))
            except Exception as e:
                print(f"❌ Stewie Discord: Failed to start bot: {e}")
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
                print(f"⚠️ Stewie Discord: Error checking bot status: {e}")
                bot_ready = False
                bot_user_str = None
        
        return {
            "character": "Stewie Griffin",
            "bot_ready": bot_ready,
            "bot_user": bot_user_str,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "token_configured": bool(DISCORD_BOT_TOKEN_STEWIE),
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
            print("✅ Stewie Discord: Connected to KeyDB for conversation history")
            return redis_client
        except Exception as e:
            print(f"❌ Stewie Discord: Failed to connect to KeyDB: {e}")
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
            
            print(f"💾 Stewie Discord: Stored message in conversation history for channel {channel_id}")
            
        except Exception as e:
            print(f"⚠️ Stewie Discord: Failed to store message in history: {e}")
    
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
                        print(f"⚠️ Stewie Discord: Skipping malformed message - {', '.join(error_details)}")
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
                    print(f"⚠️ Stewie Discord: Skipping malformed message in history: {e}")
                    continue
            
            print(f"📚 Stewie Discord: Retrieved {len(messages)} messages from conversation history for channel {channel_id}")
            return messages
            
        except Exception as e:
            print(f"⚠️ Stewie Discord: Failed to retrieve conversation history: {e}")
            return []

# Global bot instance - starts automatically when imported
stewie_bot = StewieDiscordBot()

# Flask endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        status = stewie_bot.get_status()
        health_status = "healthy" if status["token_configured"] else "degraded"
        
        return jsonify({
            "status": health_status,
            "service": "Stewie_Discord_Handler",
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
        return jsonify(stewie_bot.get_status()), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    """API endpoint to send messages (for testing)."""
    return jsonify({
        "message": "Stewie Discord handler is running via Discord bot",
        "note": "Use Discord mentions or DMs to interact with Stewie",
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
        
        print(f"🌱 Stewie Discord: Received organic message for channel {channel_id} (organic: {is_organic})")
        
        # Store organic message in conversation history before sending
        stewie_bot._store_message_in_history(
            channel_id=channel_id,
            author="Stewie Griffin",
            content=message_text,
            message_type="stewie"
        )
        
        # Send the message to Discord
        success = send_message_to_discord(message_text, channel_id)
        
        if success:
            print(f"✅ Stewie Discord: Successfully sent organic message to channel {channel_id}")
            
            # Send organic notification to continue the conversation chain
            try:
                conversation_history = stewie_bot._get_conversation_history(channel_id)
                
                notification_data = {
                    "event_type": "direct_response_sent",
                    "responding_character": "stewie",
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
                    print(f"✅ Stewie Discord: Organic chain notification sent to message router")
                else:
                    print(f"⚠️ Stewie Discord: Organic chain notification failed: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️ Stewie Discord: Failed to send organic chain notification: {e}")
            
            return jsonify({"success": True, "message": "Organic message sent successfully"})
        else:
            print(f"❌ Stewie Discord: Failed to send organic message to channel {channel_id}")
            return jsonify({"success": False, "error": "Failed to send message to Discord"}), 500
        
    except Exception as e:
        print(f"❌ Stewie Discord: Error in organic message endpoint: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def send_message_to_discord(message_text: str, channel_id: str) -> bool:
    """Send a message to Discord via the Stewie bot."""
    try:
        if not stewie_bot.bot or not stewie_bot.bot.user or stewie_bot.bot.is_closed():
            print(f"❌ Stewie Discord: Bot not ready for message sending")
            return False
        
        # Create async function to send message
        async def send_message():
            try:
                channel = stewie_bot.bot.get_channel(int(channel_id))
                if channel:
                    await channel.send(message_text)
                    print(f"✅ Stewie Discord: Message sent to channel {channel_id}")
                    return True
                else:
                    print(f"❌ Stewie Discord: Channel {channel_id} not found")
                    return False
            except Exception as e:
                print(f"❌ Stewie Discord: Error sending message: {e}")
                return False
        
        # Get the bot's event loop and schedule the coroutine
        loop = stewie_bot.bot.loop
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(send_message(), loop)
            success = future.result(timeout=10)  # Wait up to 10 seconds
            return success
        else:
            print(f"❌ Stewie Discord: Bot event loop not available")
            return False
            
    except Exception as e:
        print(f"❌ Stewie Discord: Exception in send_message_to_discord: {e}")
        return False

# No Flask development server code needed - Gunicorn handles this
if __name__ == '__main__':
    print(f"👶 Stewie Discord Handler starting on port {STEWIE_DISCORD_PORT}...")
    print(f"🔗 Message Router URL: {MESSAGE_ROUTER_URL}")
    print(f"🔐 Token configured: {bool(DISCORD_BOT_TOKEN_STEWIE)}")
    print("⚠️  This should only run in development. Use Gunicorn for production.") 