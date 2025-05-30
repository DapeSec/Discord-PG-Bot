import os
import asyncio
import requests
import traceback
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set
from flask import Flask, jsonify, request
from threading import Thread, Lock
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Load environment variables
load_dotenv()

# Configuration
PETER_DISCORD_PORT = int(os.getenv("PETER_DISCORD_PORT", "6011"))
DISCORD_BOT_TOKEN_PETER = os.getenv("DISCORD_BOT_TOKEN_PETER")
MESSAGE_ROUTER_URL = os.getenv("MESSAGE_ROUTER_URL", "http://message-router:6005/orchestrate")

# Flask app for health checks and API
app = Flask(__name__)

# Import centralized retry manager
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from utils.retry_manager import retry_async, RetryConfig

class PeterDiscordBot:
    """Peter Griffin Discord bot handler with spam protection."""
    
    def __init__(self):
        """Initialize the Peter Discord bot."""
        self.bot = None
        self.message_count = 0
        self.error_count = 0
        
        # Spam protection
        self.processed_messages: Set[str] = set()  # Message deduplication
        self.processing_lock = Lock()  # Prevent race conditions
        self.last_response_time: Dict[str, float] = {}  # Rate limiting per channel
        self.RATE_LIMIT_SECONDS = 2  # Minimum time between responses per channel
        self.MESSAGE_CACHE_SIZE = 1000  # Limit memory usage
        
        if not DISCORD_BOT_TOKEN_PETER:
            print("❌ Peter Discord: DISCORD_BOT_TOKEN_PETER not set!")
            return
            
        # Configure bot with intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(
            command_prefix='!peter ',
            intents=intents,
            description="Peter Griffin - Family Guy patriarch"
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
            print(f"🍺 Peter Discord Bot: Logged in as {self.bot.user}")
        
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
                    print(f"🚫 Peter Discord: Duplicate message detected, ignoring: {message_hash[:8]}")
                    return
                
                # Check rate limiting
                if self._is_rate_limited(channel_id):
                    print(f"⏱️ Peter Discord: Rate limited for channel {channel_id}")
                    return
                
                # Mark as processing
                self.processed_messages.add(message_hash)
                self._update_rate_limit(channel_id)
                self._cleanup_old_messages()
            
            try:
                self.message_count += 1
                print(f"🎯 Peter Discord: Processing message {message_hash[:8]} from {message.author}")
                
                # Clean the message content (remove mentions)
                content = message.content
                if self.bot.user.mentioned_in(message):
                    content = content.replace(f'<@{self.bot.user.id}>', '').strip()
                
                # Send typing indicator
                async with message.channel.typing():
                    # Get conversation history (simplified for now)
                    conversation_history = []
                    
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
                    
                    # Define quality validation function
                    def validate_quality(peter_response):
                        return asyncio.run(self.check_response_quality(peter_response, content, channel_id))
                    
                    # Use centralized retry for message generation
                    peter_response = await retry_async(
                        operation=generate_message,
                        validation_func=lambda result: asyncio.run(self.check_response_quality(result, content, channel_id)) if result else False,
                        service_name="Peter Discord",
                        **RetryConfig.DISCORD_MESSAGE
                    )
                    
                    if peter_response:
                        # Success - send message and notify for organic analysis
                        await message.channel.send(peter_response)
                        print(f"✅ Peter Discord: Successfully sent response")
                        
                        # OPTION 3: Notify message router for organic conversation analysis
                        await self._notify_message_router_for_organic_analysis(
                            peter_response, content, channel_id, str(message.author.id), conversation_history
                        )
                    else:
                        # All retries failed - generate a quality-controlled fallback message
                        print(f"❌ Peter Discord: All attempts failed, generating fallback")
                        fallback_message = await self._generate_quality_fallback_message("quality_failure", content, channel_id)
                        if fallback_message:
                            await message.channel.send(fallback_message)
                        else:
                            # Ultimate fallback if even error generation fails
                            await message.channel.send("*scratches head in confusion*")
                        self.error_count += 1
            
            except Exception as e:
                self.error_count += 1
                print(f"❌ Peter Discord: Exception handling message {message_hash[:8]}: {e}")
                print(traceback.format_exc())
                try:
                    fallback_message = await self._generate_quality_fallback_message("system_error", content, channel_id)
                    if fallback_message:
                        await message.channel.send(fallback_message)
                    else:
                        # Ultimate fallback if even error generation fails
                        await message.channel.send("*tilts head in confusion*")
                except:
                    print("❌ Peter Discord: Failed to send error message")
            
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
                        "character": "peter",
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
                
                print(f"📊 Peter Discord: Quality check - Score: {quality_score}, Passed: {quality_passed}")
                return quality_passed
            else:
                print(f"⚠️ Peter Discord: Quality control service unavailable, allowing response")
                return True  # Default to allowing if service unavailable
                
        except Exception as e:
            print(f"⚠️ Peter Discord: Quality check failed: {e}")
            return True  # Default to allowing if check fails
    
    async def _generate_quality_fallback_message(self, error_type: str, original_input: str, channel_id: str) -> Optional[str]:
        """Generate a quality-controlled fallback message for errors."""
        try:
            # Define error-specific prompts for Peter
            error_prompts = {
                "quality_failure": "Respond as Peter Griffin when you're having trouble thinking of something good to say about this topic. Be brief, authentic Peter, and show mild confusion.",
                "connection_error": "Respond as Peter Griffin when something technical is broken or not working. Be brief, authentic Peter, and show frustration with technology.",
                "system_error": "Respond as Peter Griffin when something unexpected went wrong. Be brief, authentic Peter, and show confusion about what happened."
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
                validation_func=lambda result: asyncio.run(self.check_response_quality(result, original_input, channel_id)) if result else False,
                service_name="Peter Discord",
                **RetryConfig.FALLBACK_GENERATION
            )
            
            if fallback_text:
                print(f"✅ Peter Discord: Generated quality fallback message")
                return fallback_text
            else:
                print(f"❌ Peter Discord: Fallback generation failed")
                return None
            
        except Exception as e:
            print(f"❌ Peter Discord: Error in fallback generation: {e}")
            return None
    
    async def _notify_message_router_for_organic_analysis(self, response_sent: str, original_input: str, channel_id: str, user_id: str, conversation_history: list):
        """Notify message router that a direct response was sent, triggering organic conversation analysis."""
        try:
            # Create updated conversation history with the response we just sent
            updated_history = conversation_history + [{
                "role": "assistant",
                "content": response_sent,
                "character": "peter",
                "timestamp": datetime.now().isoformat()
            }]
            
            # Send notification to message router for organic analysis
            notification_data = {
                "event_type": "direct_response_sent",
                "responding_character": "peter",
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
                print(f"✅ Peter Discord: Organic analysis notification sent to message router")
            else:
                print(f"⚠️ Peter Discord: Organic notification failed: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Peter Discord: Failed to send organic notification: {e}")
    
    async def send_to_message_router(self, input_text: str, channel_id: str, user_id: str, conversation_history: list) -> Optional[Dict[str, Any]]:
        """Send message to the message router service."""
        try:
            data = {
                "character_name": "Peter",
                "input_text": input_text,
                "channel_id": channel_id,
                "user_id": user_id,
                "conversation_history": conversation_history
            }
            
            # Use asyncio to make non-blocking HTTP request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(MESSAGE_ROUTER_URL, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Peter Discord: Message router returned {response.status_code}")
                # Try to parse JSON error response even for non-200 status codes
                try:
                    error_data = response.json()
                    return error_data  # Return the full error response including quality control info
                except:
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            print("❌ Peter Discord: Message router timeout")
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            print("❌ Peter Discord: Cannot connect to message router")
            return {"success": False, "error": "Connection failed"}
        except Exception as e:
            print(f"❌ Peter Discord: Exception sending to message router: {e}")
            return {"success": False, "error": str(e)}
    
    def start_discord_bot_background(self):
        """Start Discord bot in background thread."""
        if not self.bot or not DISCORD_BOT_TOKEN_PETER:
            return
        
        def run_bot():
            try:
                print("🚀 Peter Discord: Starting bot in background...")
                asyncio.run(self.bot.start(DISCORD_BOT_TOKEN_PETER))
            except Exception as e:
                print(f"❌ Peter Discord: Failed to start bot: {e}")
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
                print(f"⚠️ Peter Discord: Error checking bot status: {e}")
                bot_ready = False
                bot_user_str = None
        
        return {
            "character": "Peter Griffin",
            "bot_ready": bot_ready,
            "bot_user": bot_user_str,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "token_configured": bool(DISCORD_BOT_TOKEN_PETER),
            "message_router_url": MESSAGE_ROUTER_URL,
            "timestamp": datetime.now().isoformat()
        }

# Global bot instance - starts automatically when imported
peter_bot = PeterDiscordBot()

# Flask endpoints
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        status = peter_bot.get_status()
        health_status = "healthy" if status["bot_ready"] and status["token_configured"] else "degraded"
        
        return jsonify({
            "status": health_status,
            "service": "Peter_Discord_Handler",
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
        return jsonify(peter_bot.get_status()), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    """API endpoint to send messages (for testing)."""
    return jsonify({
        "message": "Peter Discord handler is running via Discord bot",
        "note": "Use Discord mentions or DMs to interact with Peter",
        "timestamp": datetime.now().isoformat()
    }), 200

@app.route('/organic-message', methods=['POST'])
def send_organic_message():
    """Receive and send organic follow-up messages from the message router with quality control."""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        message_text = data.get('message')
        channel_id = data.get('channel_id')
        
        if not message_text or not channel_id:
            return jsonify({
                "success": False, 
                "error": "Missing required fields: message, channel_id"
            }), 400
        
        print(f"🌱 Peter Discord: Received organic message for channel {channel_id}")
        print(f"🌱 Peter Discord: Message: {message_text}")
        
        # CRITICAL: Run quality control on organic messages
        async def send_with_quality_control():
            """Send organic message with quality control validation."""
            try:
                # Check quality before sending
                quality_passed = await peter_bot.check_response_quality(
                    message_text, "", str(channel_id)
                )
                
                if not quality_passed:
                    print(f"❌ Peter Discord: Organic message FAILED quality control - rejecting")
                    return False
                
                # Quality passed - send to Discord
                channel = peter_bot.bot.get_channel(int(channel_id))
                if channel:
                    await channel.send(message_text)
                    print(f"✅ Peter Discord: Organic message sent to channel {channel_id} (passed quality control)")
                    return True
                else:
                    print(f"❌ Peter Discord: Channel {channel_id} not found")
                    return False
                    
            except Exception as e:
                print(f"❌ Peter Discord: Error sending organic message: {e}")
                return False
        
        # Send the message to Discord with quality control
        if peter_bot.bot and peter_bot.bot.user and not peter_bot.bot.is_closed():
            try:
                # Get the bot's event loop and schedule the coroutine
                loop = peter_bot.bot.loop
                if loop and not loop.is_closed():
                    future = asyncio.run_coroutine_threadsafe(send_with_quality_control(), loop)
                    success = future.result(timeout=10)  # Wait up to 10 seconds
                    
                    if success:
                        return jsonify({"success": True, "message": "Organic message sent (passed quality control)"}), 200
                    else:
                        return jsonify({"success": False, "error": "Message failed quality control or send failed"}), 400
                else:
                    return jsonify({"success": False, "error": "Bot event loop not available"}), 503
            except Exception as e:
                print(f"❌ Peter Discord: Error scheduling organic message: {e}")
                return jsonify({"success": False, "error": f"Failed to send: {str(e)}"}), 500
        else:
            return jsonify({"success": False, "error": "Bot not ready"}), 503
            
    except Exception as e:
        print(f"❌ Peter Discord: Exception in organic message handler: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# No Flask development server code needed - Gunicorn handles this
if __name__ == '__main__':
    print(f"🍺 Peter Discord Handler starting on port {PETER_DISCORD_PORT}...")
    print(f"🔗 Message Router URL: {MESSAGE_ROUTER_URL}")
    print(f"🔐 Token configured: {bool(DISCORD_BOT_TOKEN_PETER)}")
    print("⚠️  This should only run in development. Use Gunicorn for production.") 