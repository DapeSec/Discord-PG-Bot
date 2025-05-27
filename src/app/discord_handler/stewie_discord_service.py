import discord
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import threading
import requests
import traceback
from datetime import datetime

# Load environment variables
load_dotenv()

# --- Stewie Discord Handler Configuration ---
SERVICE_NAME = "StewieDiscordHandler"

# KeyDB Cache Integration
try:
    # Try multiple import paths for Docker compatibility
    try:
        from src.app.utils.cache import cache_discord_state, get_discord_state, get_cache
    except ImportError:
        # Fallback for Docker environment
        import sys
        import os
        sys.path.append('/app')
        from src.app.utils.cache import cache_discord_state, get_discord_state, get_cache
    
    CACHE_AVAILABLE = True
    print(f"✅ {SERVICE_NAME} - KeyDB cache utilities imported successfully")
except ImportError as e:
    print(f"⚠️ {SERVICE_NAME} - Cache utilities not available: {e}. Using in-memory state.")
    CACHE_AVAILABLE = False

STEWIE_DISCORD_PORT = int(os.getenv("STEWIE_DISCORD_PORT", 5013))
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_API_URL", "http://orchestrator:5003/orchestrate")

# --- Discord Bot Token ---
STEWIE_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_STEWIE")

if not STEWIE_BOT_TOKEN:
    print("ERROR: Missing Stewie Discord bot token. Please check your environment variables.")
    exit(1)

# --- Discord Client ---
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

stewie_client = discord.Client(intents=intents)

# Global variables to store bot mention strings and IDs
stewie_mention = None
stewie_id = None
stewie_ready = False

# --- Flask App ---
app = Flask(__name__)

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and load balancers."""
    try:
        is_logged_in = stewie_client.user is not None
        is_discord_ready = stewie_client.is_ready()
        
        # Get state from cache if available
        cached_state = None
        cache_status = "not_available"
        if CACHE_AVAILABLE:
            try:
                cached_state = get_discord_state('stewie')
                cache_status = "connected" if cached_state else "no_data"
            except Exception as e:
                cache_status = f"error: {str(e)}"
        
        # Consider ready if logged in or custom ready status or cached ready
        client_ready = is_logged_in or stewie_ready
        if cached_state:
            client_ready = client_ready or cached_state.get('ready', False)
        
        status = "healthy" if client_ready else "degraded"
        
        response_data = {
            "status": status,
            "service": SERVICE_NAME,
            "timestamp": datetime.now().isoformat(),
            "cache": {
                "status": cache_status,
                "available": CACHE_AVAILABLE
            },
            "discord_client": {
                "logged_in": is_logged_in,
                "discord_ready": is_discord_ready,
                "custom_ready": stewie_ready,
                "status": "ready" if client_ready else "not_ready",
                "user_id": stewie_client.user.id if stewie_client.user else None,
                "username": stewie_client.user.name if stewie_client.user else None
            }
        }
        
        # Include cached state if available
        if cached_state:
            response_data["cached_state"] = cached_state
        
        return jsonify(response_data), 200 if status == "healthy" else 503
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "reason": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

# --- Discord Message Sending Endpoint ---
@app.route('/send_message', methods=['POST'])
def send_message():
    """
    Send a message to Discord via Stewie bot.
    
    Expected JSON:
    {
        "channel_id": "discord_channel_id",
        "message_content": "message text"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        channel_id = data.get("channel_id")
        message_content = data.get("message_content")

        if not all([channel_id, message_content]):
            return jsonify({
                "error": "Missing required fields: channel_id, message_content"
            }), 400

        # Check if client is ready
        is_logged_in = stewie_client.user is not None
        if not (is_logged_in or stewie_ready):
            return jsonify({
                "error": "Stewie Discord client is not logged in or ready"
            }), 503

        # Schedule the message sending on the client's event loop
        loop = stewie_client.loop
        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                _send_discord_message_async(stewie_client, channel_id, message_content), 
                loop
            )
            future.result(timeout=30)  # 30 second timeout
            
            print(f"INFO: {SERVICE_NAME} - Stewie sent message to channel {channel_id}")
            return jsonify({"status": "Message sent successfully"}), 200
        else:
            return jsonify({
                "error": "Event loop for Stewie is not running"
            }), 503

    except Exception as e:
        print(f"ERROR: {SERVICE_NAME} - Error sending message: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": "Failed to send message",
            "details": str(e)
        }), 500

# --- Get Bot Information Endpoint ---
@app.route('/bot_info', methods=['GET'])
def get_bot_info():
    """Get information about Stewie Discord bot."""
    try:
        if stewie_client.is_ready() and stewie_client.user:
            bot_info = {
                "id": stewie_client.user.id,
                "username": stewie_client.user.name,
                "mention": f"<@{stewie_client.user.id}>",
                "ready": True
            }
        else:
            bot_info = {"ready": False}
        
        return jsonify(bot_info), 200
    except Exception as e:
        print(f"ERROR: {SERVICE_NAME} - Error getting bot info: {e}")
        return jsonify({"error": str(e)}), 500

# --- Helper Functions ---
async def _send_discord_message_async(client, channel_id, message_content):
    """Send a message to Discord asynchronously."""
    try:
        channel_id_int = int(channel_id)
        channel = client.get_channel(channel_id_int)
        
        if channel is None:
            # Try to fetch from Discord API
            channel = await client.fetch_channel(channel_id_int)
        
        if channel:
            await channel.send(message_content)
            print(f"SUCCESS: Message sent to channel {channel_id_int}")
        else:
            print(f"ERROR: Could not find channel {channel_id_int}")
            
    except Exception as e:
        print(f"ERROR: Failed to send message to channel {channel_id}: {e}")
        raise

def forward_to_orchestrator(message_data):
    """Forward Discord message to orchestrator in a separate thread."""
    try:
        response = requests.post(
            ORCHESTRATOR_API_URL,
            json=message_data,
            timeout=300  # Increased timeout for optimized orchestrator
        )
        response.raise_for_status()
        print(f"INFO: {SERVICE_NAME} - Forwarded message to orchestrator")
    except Exception as e:
        print(f"ERROR: {SERVICE_NAME} - Failed to forward to orchestrator: {e}")

# --- Discord Event Handlers ---
def setup_discord_events():
    """Set up Discord event handlers for Stewie client."""
    
    @stewie_client.event
    async def on_ready():
        """Event fired when Stewie Discord client is ready."""
        global stewie_mention, stewie_id, stewie_ready
        user = stewie_client.user
        stewie_mention = f"<@{user.id}>"
        stewie_id = user.id
        stewie_ready = True
        
        # Cache state in KeyDB if available
        if CACHE_AVAILABLE:
            state_data = {
                'ready': True,
                'mention': stewie_mention,
                'user_id': user.id,
                'username': user.name,
                'timestamp': datetime.now().isoformat(),
                'service_name': SERVICE_NAME
            }
            cache_discord_state('stewie', state_data, ttl=3600)
            print(f"INFO: {SERVICE_NAME} - Stewie Bot state cached in KeyDB")
        
        print(f"INFO: {SERVICE_NAME} - Stewie Bot logged in as {user}")
        print(f"INFO: {SERVICE_NAME} - Stewie mention: {stewie_mention}")

    @stewie_client.event
    async def on_message(message):
        """Event fired when Stewie receives a Discord message."""
        await handle_discord_message(message)

async def handle_discord_message(message):
    """Handle Discord message received by Stewie bot."""
    # Ignore messages from Stewie bot itself
    if message.author.id == stewie_id:
        return
    
    # Ignore messages from other bots (Peter and Brian)
    if message.author.bot:
        return
    
    # Only process messages that are specifically for Stewie
    user_message = message.content
    should_respond = False
    
    # Check for direct mentions of Stewie
    if stewie_mention in message.content:
        user_message = message.content.replace(stewie_mention, '').strip()
        should_respond = True
    # Check for Stewie-specific commands
    elif message.content.lower().startswith('!stewie'):
        user_message = message.content[len('!stewie'):].strip()
        should_respond = True
    # Check if message is a direct message to Stewie
    elif isinstance(message.channel, discord.DMChannel):
        should_respond = True
    
    # If this message is not for Stewie, ignore it
    if not should_respond:
        return
    
    if not user_message.strip():
        # Send a default response for empty mentions
        await message.channel.send("What is it, you insufferable fool?")
        return

    # Prepare message data for orchestrator
    message_data = {
        "user_query": user_message,
        "channel_id": message.channel.id,
        "initiator_bot_name": "Stewie",
        "initiator_mention": stewie_mention,
        "human_user_display_name": message.author.display_name,
        "is_new_conversation": False,
        "conversation_session_id": None,
        "original_message": message.content,
        "source": "stewie_discord_handler"
    }

    # Forward to orchestrator in background thread
    threading.Thread(
        target=forward_to_orchestrator,
        args=(message_data,),
        daemon=True
    ).start()

# --- Discord Client Management ---
async def start_stewie_discord_client():
    """Start Stewie Discord client."""
    try:
        print(f"INFO: {SERVICE_NAME} - Starting Stewie Discord client...")
        await stewie_client.start(STEWIE_BOT_TOKEN)
    except Exception as e:
        print(f"ERROR: {SERVICE_NAME} - Error starting Stewie Discord client: {e}")
        raise

def run_discord_client():
    """Run Stewie Discord client in asyncio event loop."""
    try:
        print(f"INFO: {SERVICE_NAME} - Setting up Discord event handlers...")
        setup_discord_events()
        
        print(f"INFO: {SERVICE_NAME} - Starting Stewie Discord client...")
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_stewie_discord_client())
    except Exception as e:
        print(f"CRITICAL: {SERVICE_NAME} - Stewie Discord client failed: {e}")
        print(traceback.format_exc())

def initialize_stewie_discord_handler():
    """Initialize the Stewie Discord Handler service - start Discord bot in background."""
    print(f"INFO: {SERVICE_NAME} - Initializing Stewie Discord Handler Service...")
    
    # Start Discord client in a daemon thread (background)
    discord_thread = threading.Thread(target=run_discord_client, daemon=True)
    discord_thread.name = "StewieDiscordClientThread"
    discord_thread.start()
    print(f"INFO: {SERVICE_NAME} - Stewie Discord client thread started")

# Initialize Stewie Discord Handler when module is imported (for Gunicorn)
initialize_stewie_discord_handler()

if __name__ == '__main__':
    print(f"INFO: {SERVICE_NAME} - Running in standalone mode...")
    
    # Initialize Stewie Discord Handler
    initialize_stewie_discord_handler()
    
    # Start Flask in the main thread
    print(f"INFO: {SERVICE_NAME} - Starting Flask app on port {STEWIE_DISCORD_PORT}...")
    app.run(
        host='0.0.0.0', 
        port=STEWIE_DISCORD_PORT, 
        debug=False, 
        use_reloader=False, 
        threaded=True
    ) 