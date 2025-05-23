import discord
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import threading
import requests
import traceback
import functools
import uuid # Import uuid for generating unique session IDs for human-initiated conversations
from datetime import datetime

# Load environment variables from a .env file
load_dotenv()

# --- Bot Configuration ---
API_TIMEOUT = 120  # Increased timeout for API calls to 120 seconds
MAX_RETRIES = 3    # Number of retries for failed API calls

# --- Discord Bot Configuration ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_BRIAN")

if not DISCORD_BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN_BRIAN not found in environment variables.")
    print("Please create a .env file with DISCORD_BOT_TOKEN_BRIAN='YOUR_BRIAN_BOT_TOKEN_HERE'")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True # Ensure guild intent is enabled for channel access
client = discord.Client(intents=intents)

# Global variables to store bot mention strings and their integer IDs
BRIAN_BOT_MENTION_STRING = ""
PETER_BOT_MENTION_STRING_GLOBAL = ""
STEWIE_BOT_MENTION_STRING_GLOBAL = ""

BRIAN_BOT_ID_INT = None
PETER_BOT_ID_INT = None
STEWIE_BOT_ID_INT = None

# --- Inter-Bot Communication Configuration (Orchestrator as central point) ---
BRIAN_BOT_PORT = 5002 # Brian's bot will listen on this port for orchestrator calls
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_API_URL") # URL for the orchestrator's main endpoint

if not ORCHESTRATOR_API_URL:
    print("Error: ORCHESTRATOR_API_URL not found in environment variables.")
    print("Please set ORCHESTRATOR_API_URL=http://localhost:5003/orchestrate in your .env file.")
    exit(1)

app = Flask(__name__)

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and load balancers."""
    try:
        # Check if Discord client is ready
        discord_status = "healthy" if client.is_ready() else "not_ready"
        
        overall_status = "healthy" if discord_status == "healthy" else "degraded"
        
        return jsonify({
            "status": overall_status,
            "bot_name": "Brian",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "discord": discord_status,
                "flask": "healthy"
            }
        }), 200 if overall_status == "healthy" else 503
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "reason": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

# Helper to send a message to a Discord channel from a non-async context (Flask thread)
async def _send_discord_message_async(channel_id, message_content):
    # Ensure channel_id is an integer for discord.py functions
    channel_id_int = int(channel_id)

    channel = client.get_channel(channel_id_int) # Try getting from cache first
    if channel is None:
        print(f"DEBUG: Channel {channel_id_int} not found in cache. Attempting to fetch from Discord API...")
        try:
            channel = await client.fetch_channel(channel_id_int) # Fetch from Discord API
        except discord.NotFound:
            print(f"ERROR: Channel {channel_id_int} not found or bot doesn't have access.")
            return
        except discord.Forbidden:
            print(f"ERROR: Bot doesn't have permission to access channel {channel_id_int}.")
            return
        except Exception as e:
            print(f"ERROR: Failed to fetch channel {channel_id_int}: {e}")
            return

    if channel:
        try:
            print(f"DEBUG: Sending message to channel {channel.name} ({channel_id_int}): {message_content[:50]}...")
            await channel.send(message_content)
            print(f"DEBUG: Message sent to channel {channel.name} ({channel_id_int})")
        except discord.Forbidden:
            print(f"ERROR: Bot doesn't have permission to send messages in channel {channel.name} ({channel_id_int}).")
        except Exception as e:
            print(f"ERROR: Failed to send message to channel {channel_id_int}: {e}")
    else:
        print(f"ERROR: Unable to get or fetch channel {channel_id_int}")

@app.route('/send_discord_message', methods=['POST'])
def send_discord_message():
    """
    Flask endpoint for the orchestrator to send messages to Discord via Brian's bot.
    This is required because the orchestrator cannot directly access Discord's API.
    """
    data = request.json
    if not data:
        print("ERROR: No JSON data received in /send_discord_message for Brian.")
        return jsonify({"error": "No JSON data received"}), 400

    message_content = data.get("message_content")
    channel_id = data.get("channel_id")

    if not all([message_content, channel_id]):
        print(f"ERROR: Missing message_content or channel_id in /send_discord_message. Received: {data}")
        return jsonify({"error": "Missing message_content or channel_id"}), 400

    print(f"DEBUG: Brian Bot - Sending message to Discord channel {channel_id}: '{message_content[:50]}...'")

    try:
        client.loop.create_task(_send_discord_message_async(channel_id, message_content))
        print(f"DEBUG: Brian's bot sent message to Discord channel {channel_id}.")
        return jsonify({"status": "Message sent to Discord channel"}), 200
    except Exception as e:
        print(f"ERROR: Error sending message to Discord for Brian: {e}")
        print(traceback.format_exc())
        return jsonify({"error": "Error sending message to Discord", "details": str(e)}), 500

@app.route('/initiate_conversation', methods=['POST'])
def initiate_conversation():
    """
    Flask endpoint for the orchestrator to instruct Brian's bot to initiate a conversation.
    This bot will then send the initial message to Discord.
    """
    data = request.json
    if not data:
        print("ERROR: No JSON data received in /initiate_conversation for Brian.")
        return jsonify({"error": "No JSON data received"}), 400

    conversation_starter_prompt = data.get("conversation_starter_prompt")
    channel_id = data.get("channel_id")
    is_new_conversation = data.get("is_new_conversation", False) # New: Get the flag
    conversation_session_id = data.get("conversation_session_id", None) # New: Get the session ID

    if not all([conversation_starter_prompt, channel_id]):
        print(f"ERROR: Missing conversation_starter_prompt or channel_id in /initiate_conversation. Received: {data}")
        return jsonify({"error": "Missing conversation_starter_prompt or channel_id"}), 500

    print(f"DEBUG: Brian Bot - Received initiation request for channel {channel_id} (Session: {conversation_session_id}) with prompt: '{conversation_starter_prompt[:50]}...'")

    # Brian's bot will send this message directly to Discord
    # The orchestrator already generated the prompt, so Brian just sends it.
    try:
        client.loop.create_task(_send_discord_message_async(channel_id, conversation_starter_prompt))
        print(f"DEBUG: Brian's bot scheduled initial conversation message to Discord for channel {channel_id} (Session: {conversation_session_id}).")

        # After sending the message, immediately inform the orchestrator to start the conversation loop
        orchestrator_payload = {
            "user_query": conversation_starter_prompt, # The starter acts as the initial "user query" from the bot
            "channel_id": channel_id,
            "initiator_bot_name": "Brian", # Brian is initiating this conversation
            "initiator_mention": BRIAN_BOT_MENTION_STRING,
            "human_user_display_name": None, # No human user initiated this specific turn, so pass None
            "is_new_conversation": is_new_conversation, # Pass the flag
            "conversation_session_id": conversation_session_id # Pass the session ID
        }
        # Call orchestrator in a non-blocking way
        threading.Thread(target=lambda: requests.post(ORCHESTRATOR_API_URL, json=orchestrator_payload, timeout=60)).start()
        print(f"DEBUG: Brian Bot - Informed orchestrator to start conversation loop for session {conversation_session_id}.")

        return jsonify({"status": "Initial conversation message scheduled and orchestrator informed"}), 200
    except Exception as e:
        print(f"ERROR: Error scheduling initial conversation message for Brian: {e}")
        print(traceback.format_exc())
        return jsonify({"error": "Error scheduling initial conversation message", "details": str(e)}), 500


def run_flask_app():
    """
    Function to run the Flask app in a separate thread.
    Includes a general exception handler for the Flask app itself.
    """
    print(f"DEBUG: Brian's Flask app starting on port {BRIAN_BOT_PORT}...")
    try:
        # Flask's app.run() is blocking, so it needs to be in its own thread.
        # use_reloader=False is important when running in a separate thread to prevent issues.
        app.run(host='0.0.0.0', port=BRIAN_BOT_PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"CRITICAL: Brian's Flask application failed to start or crashed unexpectedly: {e}")
        print(f"Please check if port {BRIAN_BOT_PORT} is already in use or if firewall/antivirus is blocking access.")
        print(traceback.format_exc()) # Log full traceback
        os._exit(1) # Force exit if Flask app thread crashes to avoid zombie process

# --- Discord Bot Events ---
@client.event
async def on_ready():
    """
    Event that fires when the bot successfully connects to Discord.
    """
    global BRIAN_BOT_MENTION_STRING
    global PETER_BOT_MENTION_STRING_GLOBAL
    global STEWIE_BOT_MENTION_STRING_GLOBAL
    global BRIAN_BOT_ID_INT
    global PETER_BOT_ID_INT
    global STEWIE_BOT_ID_INT

    BRIAN_BOT_MENTION_STRING = f"<@{client.user.id}>" # Store Brian's own mention string
    BRIAN_BOT_ID_INT = client.user.id # Store Brian's own integer ID

    # Load other bot mentions from environment variables
    PETER_BOT_MENTION_STRING_GLOBAL = os.getenv("PETER_BOT_MENTION_STRING")
    STEWIE_BOT_MENTION_STRING_GLOBAL = os.getenv("STEWIE_BOT_MENTION_STRING")

    # Convert global mention strings to integer IDs for comparison
    try:
        if PETER_BOT_MENTION_STRING_GLOBAL:
            PETER_BOT_ID_INT = int(PETER_BOT_MENTION_STRING_GLOBAL.replace('<@', '').replace('>', ''))
        else:
            print("WARNING: PETER_BOT_MENTION_STRING not found in .env. Peter's ID will be None.")
        if STEWIE_BOT_MENTION_STRING_GLOBAL:
            STEWIE_BOT_ID_INT = int(STEWIE_BOT_MENTION_STRING_GLOBAL.replace('<@', '').replace('>', ''))
        else:
            print("WARNING: STEWIE_BOT_MENTION_STRING not found in .env. Stewie's ID will be None.")
    except ValueError as e:
        print(f"ERROR: Failed to convert bot mention string to integer ID during on_ready: {e}. Check .env file format for bot mentions.")
        print(traceback.format_exc())


    # Basic validation and logging for global mention strings and IDs
    print(f"DEBUG: Brian's own mention string: {BRIAN_BOT_MENTION_STRING} (ID: {BRIAN_BOT_ID_INT})")
    print(f"DEBUG: Peter's global mention string: {PETER_BOT_MENTION_STRING_GLOBAL} (ID: {PETER_BOT_ID_INT})")
    print(f"DEBUG: Stewie's global mention string: {STEWIE_BOT_MENTION_STRING_GLOBAL} (ID: {STEWIE_BOT_ID_INT})")

    print(f'Brian Bot logged in as {client.user}')
    print('Brian Bot is ready!')
    # Start the Flask app in a new thread
    # Daemon=True means the thread will automatically exit when the main program exits
    threading.Thread(target=run_flask_app, daemon=True).start()
    print(f"DEBUG: Brian's internal API running on port {BRIAN_BOT_PORT}")

@client.event
async def on_message(message):
    """
    Event that fires when a message is sent in any channel the bot can see.
    This function now handles both direct queries and inter-bot mentions.
    """
    print(f"\nDEBUG: Brian Bot - Received message: '{message.content}' from {message.author} (ID: {message.author.id})")

    if message.author == client.user:
        print("DEBUG: Brian Bot - Ignoring message from self.")
        return # Ignore messages from self

    user_message_for_orchestrator = ""
    initiator_bot_name = ""
    initiator_mention = ""
    should_initiate_orchestration = False
    human_user_display_name = None # Initialize to None
    is_new_conversation = False # Default for human-initiated messages
    conversation_session_id = None # Default for human-initiated messages, orchestrator will assign/retrieve

    # Determine if the message author is one of the other registered bots
    is_author_another_bot = (message.author.id == PETER_BOT_ID_INT) or \
                            (message.author.id == STEWIE_BOT_ID_INT)
    print(f"DEBUG: Brian Bot - Is author another bot? {is_author_another_bot} (Author ID: {message.author.id})")
    print(f"DEBUG: Brian Bot - Peter ID: {PETER_BOT_ID_INT}, Stewie ID: {STEWIE_BOT_ID_INT}")


    # Check if this bot (Brian) is mentioned by another bot
    is_mentioned_by_another_bot = False
    if BRIAN_BOT_MENTION_STRING in message.content:
        if is_author_another_bot:
            is_mentioned_by_another_bot = True
            print(f"DEBUG: Brian Bot - Detected mention from another bot ({message.author.name}).")
        else:
            print("DEBUG: Brian Bot - Mention detected, but author is not a recognized bot (must be human).")

    # 1. Check if this message is a direct query to *this specific bot* (Brian) from a human or an explicit command.
    # This should take precedence for initial conversation start.
    if message.content.lower().startswith('!brian'):
        user_message_for_orchestrator = message.content[len('!brian'):].strip()
        should_initiate_orchestration = True
        initiator_bot_name = "Brian"
        initiator_mention = BRIAN_BOT_MENTION_STRING
        human_user_display_name = message.author.display_name # Capture human user's display name
        print("DEBUG: Brian Bot - Detected direct command '!brian'.")
    elif client.user.mentioned_in(message) and not is_author_another_bot: # Only if mentioned by a human
        # If Brian is mentioned, and it's NOT by another bot (meaning it's from a human)
        user_message_for_orchestrator = message.content.replace(BRIAN_BOT_MENTION_STRING, '').strip()
        should_initiate_orchestration = True
        initiator_bot_name = "Brian"
        initiator_mention = BRIAN_BOT_MENTION_STRING
        human_user_display_name = message.author.display_name # Capture human user's display name
        print("DEBUG: Brian Bot - Detected direct mention from human user.")

    # 2. Backup/Inter-bot conversation: If Brian is mentioned by another bot, he should join.
    # This is a backup if the direct query logic didn't trigger it, and ensures inter-bot turns.
    if not should_initiate_orchestration and is_mentioned_by_another_bot:
        should_initiate_orchestration = True
        # For inter-bot mentions, send the full message content as context
        user_message_for_orchestrator = message.content
        initiator_bot_name = "Brian"
        initiator_mention = BRIAN_BOT_MENTION_STRING
        # When another bot initiates, human_user_display_name remains None, which is fine for the LLM prompt
        print("DEBUG: Brian Bot - Initiating orchestration due to inter-bot mention.")


    if not should_initiate_orchestration:
        print("DEBUG: Brian Bot - Not the designated initiator for this message. Ignoring.")
        return # If this bot is not the designated initiator for this message, ignore.

    if not user_message_for_orchestrator:
        await message.channel.send("Yes? What profound thought do you wish to share with me?")
        print("DEBUG: Brian Bot - Empty user message after parsing. Sent fallback.")
        return

    print(f"DEBUG: Brian Bot - Initiating Orchestration for message from {message.author} (Type: {initiator_bot_name}): {user_message_for_orchestrator[:50]}... Sending to orchestrator...")

    async with message.channel.typing():
        try:
            payload = {
                "user_query": user_message_for_orchestrator,
                "channel_id": message.channel.id,
                "initiator_bot_name": initiator_bot_name,
                "initiator_mention": initiator_mention,
                "human_user_display_name": human_user_display_name,
                "is_new_conversation": is_new_conversation,
                "conversation_session_id": conversation_session_id
            }

            retry_count = 0
            while retry_count < MAX_RETRIES:
                try:
                    post_to_orchestrator = functools.partial(
                        requests.post,
                        ORCHESTRATOR_API_URL,
                        json=payload,
                        timeout=API_TIMEOUT
                    )
                    await client.loop.run_in_executor(None, post_to_orchestrator)
                    print("DEBUG: Message sent to orchestrator. Waiting for orchestrator to send Discord messages.")
                    break
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    retry_count += 1
                    if retry_count == MAX_RETRIES:
                        raise
                    print(f"Attempt {retry_count} failed, retrying in {2 ** retry_count} seconds...")
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff

        except requests.exceptions.Timeout:
            await message.channel.send("Brian tried to talk to the brain guy, but he's taking too long. Perhaps he's pondering the existential dread of being a sentient dog?")
            print(f"ERROR: ConnectionError: Timeout when sending to orchestrator. {traceback.format_exc()}")
        except requests.exceptions.ConnectionError:
            await message.channel.send("Brian tried to talk to the brain guy, but he's not picking up! Is he on a coffee break?")
            print(f"ERROR: ConnectionError: Orchestrator server might not be running or API URL is incorrect. {traceback.format_exc()}")
        except Exception as e:
            print(f"ERROR: Error sending message to orchestrator: {e}")
            print(traceback.format_exc())
            await message.channel.send("Brian's too busy contemplating the meaning of life to respond right now.")

# --- Main execution ---
if __name__ == '__main__':
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("ERROR: Invalid Discord bot token for Brian. Please check your DISCORD_BOT_TOKEN_BRIAN environment variable.")
    except Exception as e:
        print(f"CRITICAL: An unexpected error occurred while running Brian Bot's main Discord client: {e}")
        print(traceback.format_exc()) # Log full traceback

