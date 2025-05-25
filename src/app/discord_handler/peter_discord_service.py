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

# --- Peter Discord Handler Configuration ---
SERVICE_NAME = "PeterDiscordHandler"
PETER_DISCORD_PORT = int(os.getenv("PETER_DISCORD_PORT", 5011))
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_API_URL", "http://orchestrator:5003/orchestrate")

# --- Discord Bot Token ---
PETER_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_PETER")

if not PETER_BOT_TOKEN:
    print("ERROR: Missing Peter Discord bot token. Please check your environment variables.")
    exit(1)

# --- Discord Client ---
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

peter_client = discord.Client(intents=intents)

# Global variables to store bot mention strings and IDs
peter_mention = None
peter_id = None
peter_ready = False

# --- Flask App ---
app = Flask(__name__)

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and load balancers."""
    try:
        is_logged_in = peter_client.user is not None
        is_discord_ready = peter_client.is_ready()
        
        # Consider ready if logged in or custom ready status
        client_ready = is_logged_in or peter_ready
        
        status = "healthy" if client_ready else "degraded"
        
        return jsonify({
            "status": status,
            "service": SERVICE_NAME,
            "timestamp": datetime.now().isoformat(),
            "discord_client": {
                "logged_in": is_logged_in,
                "discord_ready": is_discord_ready,
                "custom_ready": peter_ready,
                "status": "ready" if client_ready else "not_ready",
                "user_id": peter_client.user.id if peter_client.user else None,
                "username": peter_client.user.name if peter_client.user else None
            }
        }), 200 if status == "healthy" else 503
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
    Send a message to Discord via Peter bot.
    
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
        is_logged_in = peter_client.user is not None
        if not (is_logged_in or peter_ready):
            return jsonify({
                "error": "Peter Discord client is not logged in or ready"
            }), 503

        # Schedule the message sending on the client's event loop
        loop = peter_client.loop
        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                _send_discord_message_async(peter_client, channel_id, message_content), 
                loop
            )
            future.result(timeout=30)  # 30 second timeout
            
            print(f"INFO: {SERVICE_NAME} - Peter sent message to channel {channel_id}")
            return jsonify({"status": "Message sent successfully"}), 200
        else:
            return jsonify({
                "error": "Event loop for Peter is not running"
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
    """Get information about Peter Discord bot."""
    try:
        if peter_client.is_ready() and peter_client.user:
            bot_info = {
                "id": peter_client.user.id,
                "username": peter_client.user.name,
                "mention": f"<@{peter_client.user.id}>",
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
    """Set up Discord event handlers for Peter client."""
    
    @peter_client.event
    async def on_ready():
        """Event fired when Peter Discord client is ready."""
        global peter_mention, peter_id, peter_ready
        user = peter_client.user
        peter_mention = f"<@{user.id}>"
        peter_id = user.id
        peter_ready = True
        
        print(f"INFO: {SERVICE_NAME} - Peter Bot logged in as {user}")
        print(f"INFO: {SERVICE_NAME} - Peter mention: {peter_mention}")

    @peter_client.event
    async def on_message(message):
        """Event fired when Peter receives a Discord message."""
        await handle_discord_message(message)

async def handle_discord_message(message):
    """Handle Discord message received by Peter bot."""
    # Ignore messages from Peter bot itself
    if message.author.id == peter_id:
        return
    
    # Ignore messages from other bots (Brian and Stewie)
    if message.author.bot:
        return
    
    # Only process messages that are specifically for Peter
    user_message = message.content
    should_respond = False
    
    # Check for direct mentions of Peter
    if peter_mention in message.content:
        user_message = message.content.replace(peter_mention, '').strip()
        should_respond = True
    # Check for Peter-specific commands
    elif message.content.lower().startswith('!peter'):
        user_message = message.content[len('!peter'):].strip()
        should_respond = True
    # Check if message is a direct message to Peter
    elif isinstance(message.channel, discord.DMChannel):
        should_respond = True
    
    # If this message is not for Peter, ignore it
    if not should_respond:
        return
    
    if not user_message.strip():
        # Send a default response for empty mentions
        await message.channel.send("Hehehe! Yeah? What can I do for you?")
        return

    # Prepare message data for orchestrator
    message_data = {
        "user_query": user_message,
        "channel_id": message.channel.id,
        "initiator_bot_name": "Peter",
        "initiator_mention": peter_mention,
        "human_user_display_name": message.author.display_name,
        "is_new_conversation": False,
        "conversation_session_id": None,
        "original_message": message.content,
        "source": "peter_discord_handler"
    }

    # Forward to orchestrator in background thread
    threading.Thread(
        target=forward_to_orchestrator,
        args=(message_data,),
        daemon=True
    ).start()

# --- Discord Client Management ---
async def start_peter_discord_client():
    """Start Peter Discord client."""
    try:
        print(f"INFO: {SERVICE_NAME} - Starting Peter Discord client...")
        await peter_client.start(PETER_BOT_TOKEN)
    except Exception as e:
        print(f"ERROR: {SERVICE_NAME} - Error starting Peter Discord client: {e}")
        raise

def run_discord_client():
    """Run Peter Discord client in asyncio event loop."""
    try:
        print(f"INFO: {SERVICE_NAME} - Setting up Discord event handlers...")
        setup_discord_events()
        
        print(f"INFO: {SERVICE_NAME} - Starting Peter Discord client...")
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_peter_discord_client())
    except Exception as e:
        print(f"CRITICAL: {SERVICE_NAME} - Peter Discord client failed: {e}")
        print(traceback.format_exc())

def initialize_peter_discord_handler():
    """Initialize the Peter Discord Handler service - start Discord bot in background."""
    print(f"INFO: {SERVICE_NAME} - Initializing Peter Discord Handler Service...")
    
    # Start Discord client in a daemon thread (background)
    discord_thread = threading.Thread(target=run_discord_client, daemon=True)
    discord_thread.name = "PeterDiscordClientThread"
    discord_thread.start()
    print(f"INFO: {SERVICE_NAME} - Peter Discord client thread started")

# Initialize Peter Discord Handler when module is imported (for Gunicorn)
initialize_peter_discord_handler()

if __name__ == '__main__':
    print(f"INFO: {SERVICE_NAME} - Running in standalone mode...")
    
    # Initialize Peter Discord Handler
    initialize_peter_discord_handler()
    
    # Start Flask in the main thread
    print(f"INFO: {SERVICE_NAME} - Starting Flask app on port {PETER_DISCORD_PORT}...")
    app.run(
        host='0.0.0.0', 
        port=PETER_DISCORD_PORT, 
        debug=False, 
        use_reloader=False, 
        threaded=True
    ) 