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

# --- Brian Discord Handler Configuration ---
SERVICE_NAME = "BrianDiscordHandler"

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

BRIAN_DISCORD_PORT = int(os.getenv("BRIAN_DISCORD_PORT", 5012))
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_API_URL", "http://orchestrator:5003/orchestrate")

# --- Discord Bot Token ---
BRIAN_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_BRIAN")

if not BRIAN_BOT_TOKEN:
    print("ERROR: Missing Brian Discord bot token. Please check your environment variables.")
    exit(1)

# --- Discord Client ---
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

brian_client = discord.Client(intents=intents)

# Global variables to store bot mention strings and IDs
brian_mention = None
brian_id = None
brian_ready = False

# --- Flask App ---
app = Flask(__name__)

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and load balancers."""
    try:
        is_logged_in = brian_client.user is not None
        is_discord_ready = brian_client.is_ready()
        
        # Get state from cache if available
        cached_state = None
        cache_status = "not_available"
        if CACHE_AVAILABLE:
            try:
                cached_state = get_discord_state('brian')
                cache_status = "connected" if cached_state else "no_data"
            except Exception as e:
                cache_status = f"error: {str(e)}"
        
        # Consider ready if logged in or custom ready status or cached ready
        client_ready = is_logged_in or brian_ready
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
                "custom_ready": brian_ready,
                "status": "ready" if client_ready else "not_ready",
                "user_id": brian_client.user.id if brian_client.user else None,
                "username": brian_client.user.name if brian_client.user else None
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
    Send a message to Discord via Brian bot.
    
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
        is_logged_in = brian_client.user is not None
        if not (is_logged_in or brian_ready):
            return jsonify({
                "error": "Brian Discord client is not logged in or ready"
            }), 503

        # Schedule the message sending on the client's event loop
        loop = brian_client.loop
        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                _send_discord_message_async(brian_client, channel_id, message_content), 
                loop
            )
            future.result(timeout=30)  # 30 second timeout
            
            print(f"INFO: {SERVICE_NAME} - Brian sent message to channel {channel_id}")
            return jsonify({"status": "Message sent successfully"}), 200
        else:
            return jsonify({
                "error": "Event loop for Brian is not running"
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
    """Get information about Brian Discord bot."""
    try:
        if brian_client.is_ready() and brian_client.user:
            bot_info = {
                "id": brian_client.user.id,
                "username": brian_client.user.name,
                "mention": f"<@{brian_client.user.id}>",
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
    """Set up Discord event handlers for Brian client."""
    
    @brian_client.event
    async def on_ready():
        """Event fired when Brian Discord client is ready."""
        global brian_mention, brian_id, brian_ready
        user = brian_client.user
        brian_mention = f"<@{user.id}>"
        brian_id = user.id
        brian_ready = True
        
        # Cache state in KeyDB if available
        if CACHE_AVAILABLE:
            state_data = {
                'ready': True,
                'mention': brian_mention,
                'user_id': user.id,
                'username': user.name,
                'timestamp': datetime.now().isoformat(),
                'service_name': SERVICE_NAME
            }
            cache_discord_state('brian', state_data, ttl=3600)
            print(f"INFO: {SERVICE_NAME} - Brian Bot state cached in KeyDB")
        
        print(f"INFO: {SERVICE_NAME} - Brian Bot logged in as {user}")
        print(f"INFO: {SERVICE_NAME} - Brian mention: {brian_mention}")

    @brian_client.event
    async def on_message(message):
        """Event fired when Brian receives a Discord message."""
        await handle_discord_message(message)

async def handle_discord_message(message):
    """Handle Discord message received by Brian bot."""
    # Ignore messages from Brian bot itself
    if message.author.id == brian_id:
        return
    
    # Ignore messages from other bots (Peter and Stewie)
    if message.author.bot:
        return
    
    # Only process messages that are specifically for Brian
    user_message = message.content
    should_respond = False
    
    # Check for direct mentions of Brian
    if brian_mention in message.content:
        user_message = message.content.replace(brian_mention, '').strip()
        should_respond = True
    # Check for Brian-specific commands
    elif message.content.lower().startswith('!brian'):
        user_message = message.content[len('!brian'):].strip()
        should_respond = True
    # Check if message is a direct message to Brian
    elif isinstance(message.channel, discord.DMChannel):
        should_respond = True
    
    # If this message is not for Brian, ignore it
    if not should_respond:
        return
    
    if not user_message.strip():
        # Send a default response for empty mentions
        await message.channel.send("*sighs* Yes? What is it now?")
        return

    # Prepare message data for orchestrator
    message_data = {
        "user_query": user_message,
        "channel_id": message.channel.id,
        "initiator_bot_name": "Brian",
        "initiator_mention": brian_mention,
        "human_user_display_name": message.author.display_name,
        "is_new_conversation": False,
        "conversation_session_id": None,
        "original_message": message.content,
        "source": "brian_discord_handler"
    }

    # Forward to orchestrator in background thread
    threading.Thread(
        target=forward_to_orchestrator,
        args=(message_data,),
        daemon=True
    ).start()

# --- Discord Client Management ---
async def start_brian_discord_client():
    """Start Brian Discord client."""
    try:
        print(f"INFO: {SERVICE_NAME} - Starting Brian Discord client...")
        await brian_client.start(BRIAN_BOT_TOKEN)
    except Exception as e:
        print(f"ERROR: {SERVICE_NAME} - Error starting Brian Discord client: {e}")
        raise

def run_discord_client():
    """Run Brian Discord client in asyncio event loop."""
    try:
        print(f"INFO: {SERVICE_NAME} - Setting up Discord event handlers...")
        setup_discord_events()
        
        print(f"INFO: {SERVICE_NAME} - Starting Brian Discord client...")
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_brian_discord_client())
    except Exception as e:
        print(f"CRITICAL: {SERVICE_NAME} - Brian Discord client failed: {e}")
        print(traceback.format_exc())

def initialize_brian_discord_handler():
    """Initialize the Brian Discord Handler service - start Discord bot in background."""
    print(f"INFO: {SERVICE_NAME} - Initializing Brian Discord Handler Service...")
    
    # Start Discord client in a daemon thread (background)
    discord_thread = threading.Thread(target=run_discord_client, daemon=True)
    discord_thread.name = "BrianDiscordClientThread"
    discord_thread.start()
    print(f"INFO: {SERVICE_NAME} - Brian Discord client thread started")

# Initialize Brian Discord Handler when module is imported (for Gunicorn)
initialize_brian_discord_handler()

if __name__ == '__main__':
    print(f"INFO: {SERVICE_NAME} - Running in standalone mode...")
    
    # Initialize Brian Discord Handler
    initialize_brian_discord_handler()
    
    # Start Flask in the main thread
    print(f"INFO: {SERVICE_NAME} - Starting Flask app on port {BRIAN_DISCORD_PORT}...")
    app.run(
        host='0.0.0.0', 
        port=BRIAN_DISCORD_PORT, 
        debug=False, 
        use_reloader=False, 
        threaded=True
    ) 