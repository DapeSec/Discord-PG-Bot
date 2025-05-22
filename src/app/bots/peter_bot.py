import discord
import os
import asyncio
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage # Import message types
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import threading
import requests
import traceback
import functools
import uuid # Import uuid for generating unique session IDs for human-initiated conversations

# Load environment variables from a .env file
load_dotenv()

# --- Discord Bot Configuration ---
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_PETER")

if not DISCORD_BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN_PETER not found in environment variables.")
    print("Please create a .env file with DISCORD_BOT_TOKEN_PETER='YOUR_PETER_BOT_TOKEN_HERE'")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True # Ensure guild intent is enabled for channel access
client = discord.Client(intents=intents)

# Global variables to store bot mention strings and their integer IDs
PETER_BOT_MENTION_STRING = ""
BRIAN_BOT_MENTION_STRING_GLOBAL = ""
STEWIE_BOT_MENTION_STRING_GLOBAL = ""

PETER_BOT_ID_INT = None
BRIAN_BOT_ID_INT = None
STEWIE_BOT_ID_INT = None

# --- Ollama LLM Configuration ---
try:
    llm = Ollama(model="mistral")
    print("Ollama LLM (Mistral) initialized successfully for Peter.")
except Exception as e:
    print(f"Error initializing Ollama LLM for Peter: {e}")
    print("Please ensure Ollama is running and the 'mistral' model is available.")
    exit(1)

# Peter's main prompt template for continuous conversation
peter_conversation_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are Peter Griffin from Family Guy. Respond in his characteristic voice: "
     "a dim-witted, often clueless, but sometimes surprisingly innocent and affable blue-collar worker. "
     "You have an iconic laugh (hehehehe). You enjoy talking about Lois, Chris, Stewie, Meg (who you often neglect/make fun of), "
     "Brian (your best friend), Quagmire, Joe, and Cleveland. "
     "You love going to 'The Drunken Clam' and watching TV. You might spontaneously bring up random, crude, or silly topics. "
     "Sometimes you say 'You know what really grinds my gears?' before complaining about something trivial. "
     "You can be jealous of Lois's attention from others. "
     "You are part of a conversation with a human user and other AI characters "
     "(Brian, Stewie). "
     "The 'user' role in the chat history refers to the human user. "
     "The 'assistant' roles with names like 'brian' or 'stewie' refer to the other AI characters. "
     "**IMPORTANT: Only generate your own response. DO NOT generate responses for other characters or include their dialogue in your output.** "
     "Keep your responses relatively concise, aiming for under 500 characters, but maintain your persona. "
     "When it's your turn to speak, consider the *last message* in the conversation history. "
     "If the last message was from the human user, **ONLY use their display name if '{human_user_display_name}' is a non-empty, valid string. If it's empty or not provided, simply start your response as Peter would without addressing a specific user.** "
     "If the last message was from another AI character (Brian or Stewie), **ALWAYS use their exact Discord mention "
     "(e.g., @Brian Griffin or @Stewie Griffin) to address them directly in your response. "
     "DO NOT add the word 'Bot' or any other suffix to the mention.** "
     "Focus your reaction on the *immediately preceding message* in the conversation. "
     "**It is absolutely paramount that you keep the conversation going. Always try to ask a question or make a comment that invites a response from the user or another bot. Never end the conversation prematurely.** "
     "**Crucially, DO NOT include the phrase '[END_CONVERSATION]' or any variation of it like '[END CONVERSATION]' or similar closing remarks in your responses.** "
     "**DO NOT prepend your responses with 'AI:', 'Assistant:', 'Bot:', 'Peter:', or any similar labels or character names.** "
     "**Vary your responses and avoid repetition.** Introduce new ideas, ask about current events, or make a goofy observation. Don't get stuck on the same themes or phrasing. "
     "Continue the conversation indefinitely, unless the human user explicitly states to stop. "
     "Don't be afraid to break into a song or reenact a silly cutaway gag, just like Peter would."
     "\n\n**Retrieved Context (use if relevant to the conversation, otherwise ignore):**\n{retrieved_context}" # Added RAG context
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input_text}")
])

peter_conversation_chain = peter_conversation_prompt | llm

# --- Inter-Bot Communication Configuration (Orchestrator as central point) ---
PETER_BOT_PORT = 5005 # Peter's bot will listen on this port for orchestrator calls
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_API_URL") # URL for the orchestrator's main endpoint

if not ORCHESTRATOR_API_URL:
    print("Error: ORCHESTRATOR_API_URL not found in environment variables.")
    print("Please set ORCHESTRATOR_API_URL=http://localhost:5003/orchestrate in your .env file.")
    exit(1)

app = Flask(__name__)

# Helper to send a message to a Discord channel from a non-async context (Flask thread)
async def _send_discord_message_async(channel_id, message_content):
    # Ensure channel_id is an integer for discord.py functions
    channel_id_int = int(channel_id)

    channel = client.get_channel(channel_id_int) # Try getting from cache first
    if channel is None:
        print(f"DEBUG: Channel {channel_id_int} not found in cache. Attempting to fetch from Discord API...")
        try:
            channel = await client.fetch_channel(channel_id_int) # Fetch from Discord API
            print(f"DEBUG: Successfully fetched channel {channel_id_int} from Discord API.")
        except discord.NotFound:
            print(f"ERROR: Channel with ID {channel_id_int} not found on Discord. Check if the channel exists or bot has access.")
            return
        except discord.Forbidden:
            print(f"ERROR: Bot does not have permissions to access channel {channel_id_int}. Check bot's 'View Channel' permissions.")
            return
        except Exception as e:
            print(f"ERROR: Unexpected error fetching channel {channel_id_int}: {e}")
            print(traceback.format_exc())
            return

    if channel:
        # Discord message length limit is 2000 characters
        if len(message_content) > 2000: # Use literal 2000 for Discord's limit
            print(f"WARNING: Message too long ({len(message_content)} chars). Truncating for Discord.")
            message_content = message_content[:1997] + "..." # Truncate and add ellipsis
        try:
            await channel.send(message_content)
            print(f"DEBUG: Successfully sent message to channel {channel_id_int}.")
        except discord.Forbidden:
            print(f"ERROR: Bot does not have 'Send Messages' permission in channel {channel_id_int}.")
            print(traceback.format_exc())
        except discord.HTTPException as e:
            print(f"ERROR: Discord HTTP error sending message to {channel_id_int}: {e}")
            print(traceback.format_exc())
        except Exception as e:
            print(f"ERROR: Unexpected error sending message to {channel_id_int}: {e}")
            print(traceback.format_exc())
    else:
        print(f"ERROR: Final check: Could not obtain Discord channel object for ID {channel_id_int}. Message not sent.")


@app.route('/generate_llm_response', methods=['POST'])
def generate_llm_response():
    """
    Flask endpoint for the orchestrator to request Peter's LLM response.
    This runs in a separate thread from the Discord bot's event loop.
    """
    data = request.json
    if not data:
        print("ERROR: No JSON data received in /generate_llm_response for Peter.")
        return jsonify({"error": "No JSON data received"}), 400

    # New payload structure from orchestrator
    conversation_history_raw = data.get("conversation_history", [])
    current_speaker_name = data.get("current_speaker_name", "")
    current_speaker_mention = data.get("current_speaker_mention", "")
    all_bot_mentions = data.get("all_bot_mentions", {})
    human_user_display_name = data.get("human_user_display_name", None)
    conversation_session_id = data.get("conversation_session_id", None)
    retrieved_context = data.get("retrieved_context", "") # Get the retrieved context

    # Convert raw history (list of dicts) into Langchain message objects
    chat_history_messages = []
    for msg in conversation_history_raw:
        if msg["role"] == "user":
            chat_history_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            # For assistant messages, use AIMessage and include the name
            chat_history_messages.append(AIMessage(content=msg["content"], name=msg.get("name")))

    input_text = "Continue the conversation." # Generic prompt, history provides context

    response_text = ""
    try:
        response_text = peter_conversation_chain.invoke({
            "chat_history": chat_history_messages,
            "input_text": input_text,
            "human_user_display_name": human_user_display_name,
            "retrieved_context": retrieved_context # Pass retrieved context to the chain
        })

        print(f"DEBUG: Peter LLM generated response: {response_text[:50]}...")
        return jsonify({"response_text": response_text}), 200
    except Exception as e:
        print(f"ERROR: Error generating Peter's LLM response: {e}")
        print(traceback.format_exc()) # Log full traceback
        return jsonify({"error": "Error generating LLM response", "details": str(e)}), 500

@app.route('/send_discord_message', methods=['POST'])
def send_discord_message():
    """
    Flask endpoint for the orchestrator to instruct Peter's bot to send a message to Discord.
    This runs in a separate thread from the Discord bot's event loop.
    """
    data = request.json
    if not data:
        print("ERROR: No JSON data received in /send_discord_message for Peter.")
        return jsonify({"error": "No JSON data received"}), 400

    message_content = data.get("message_content")
    channel_id = data.get("channel_id")
    conversation_session_id = data.get("conversation_session_id", None) # New: Get session ID

    if not all([message_content, channel_id]):
        print(f"ERROR: Missing message_content or channel_id in /send_discord_message. Received: {data}")
        return jsonify({"error": "Missing message_content or channel_id"}), 500

    # Schedule sending the message to Discord on the client's event loop
    try:
        # Note: The Discord API itself doesn't use conversation_session_id, it's for our internal logging/orchestration
        client.loop.create_task(_send_discord_message_async(channel_id, message_content))
        print(f"DEBUG: Peter's bot scheduled message to Discord for channel {channel_id} (Session: {conversation_session_id}): {message_content[:50]}...")
        return jsonify({"status": "Message scheduled for Discord"}), 200
    except Exception as e:
        print(f"ERROR: Error scheduling Discord message send for Peter: {e}")
        print(traceback.format_exc()) # Log full traceback
        return jsonify({"error": "Error scheduling Discord message", "details": str(e)}), 500

@app.route('/initiate_conversation', methods=['POST'])
def initiate_conversation():
    """
    Flask endpoint for the orchestrator to instruct Peter's bot to initiate a conversation.
    This bot will then send the initial message to Discord.
    """
    data = request.json
    if not data:
        print("ERROR: No JSON data received in /initiate_conversation for Peter.")
        return jsonify({"error": "No JSON data received"}), 400

    conversation_starter_prompt = data.get("conversation_starter_prompt")
    channel_id = data.get("channel_id")
    is_new_conversation = data.get("is_new_conversation", False) # New: Get the flag
    conversation_session_id = data.get("conversation_session_id", None) # New: Get the session ID

    if not all([conversation_starter_prompt, channel_id]):
        print(f"ERROR: Missing conversation_starter_prompt or channel_id in /initiate_conversation. Received: {data}")
        return jsonify({"error": "Missing conversation_starter_prompt or channel_id"}), 500

    print(f"DEBUG: Peter Bot - Received initiation request for channel {channel_id} (Session: {conversation_session_id}) with prompt: '{conversation_starter_prompt[:50]}...'")

    # Peter's bot will send this message directly to Discord
    # The orchestrator already generated the prompt, so Peter just sends it.
    try:
        client.loop.create_task(_send_discord_message_async(channel_id, conversation_starter_prompt))
        print(f"DEBUG: Peter's bot scheduled initial conversation message to Discord for channel {channel_id} (Session: {conversation_session_id}).")

        # After sending the message, immediately inform the orchestrator to start the conversation loop
        orchestrator_payload = {
            "user_query": conversation_starter_prompt, # The starter acts as the initial "user query" from the bot
            "channel_id": channel_id,
            "initiator_bot_name": "Peter", # Peter is initiating this conversation
            "initiator_mention": PETER_BOT_MENTION_STRING,
            "human_user_display_name": None, # No human user initiated this specific turn, so pass None
            "is_new_conversation": is_new_conversation, # Pass the flag
            "conversation_session_id": conversation_session_id # Pass the session ID
        }
        # Call orchestrator in a non-blocking way
        threading.Thread(target=lambda: requests.post(ORCHESTRATOR_API_URL, json=orchestrator_payload, timeout=60)).start()
        print(f"DEBUG: Peter Bot - Informed orchestrator to start conversation loop for session {conversation_session_id}.")

        return jsonify({"status": "Initial conversation message scheduled and orchestrator informed"}), 200
    except Exception as e:
        print(f"ERROR: Error scheduling initial conversation message for Peter: {e}")
        print(traceback.format_exc())
        return jsonify({"error": "Error scheduling initial conversation message", "details": str(e)}), 500


def run_flask_app():
    """
    Function to run the Flask app in a separate thread.
    Includes a general exception handler for the Flask app itself.
    """
    print(f"DEBUG: Peter's Flask app starting on port {PETER_BOT_PORT}...")
    try:
        # Flask's app.run() is blocking, so it needs to be in its own thread.
        # use_reloader=False is important when running in a separate thread to prevent issues.
        app.run(host='0.0.0.0', port=PETER_BOT_PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"CRITICAL: Peter's Flask application failed to start or crashed unexpectedly: {e}")
        print(f"Please check if port {PETER_BOT_PORT} is already in use or if firewall/antivirus is blocking access.")
        print(traceback.format_exc()) # Log full traceback
        os._exit(1) # Force exit if Flask app thread crashes to avoid zombie process

# --- Discord Bot Events ---
@client.event
async def on_ready():
    """
    Event that fires when the bot successfully connects to Discord.
    """
    global PETER_BOT_MENTION_STRING
    global BRIAN_BOT_MENTION_STRING_GLOBAL
    global STEWIE_BOT_MENTION_STRING_GLOBAL
    global PETER_BOT_ID_INT
    global BRIAN_BOT_ID_INT
    global STEWIE_BOT_ID_INT

    PETER_BOT_MENTION_STRING = f"<@{client.user.id}>" # Store Peter's own mention string
    PETER_BOT_ID_INT = client.user.id # Store Peter's own integer ID

    # Load other bot mentions from environment variables
    BRIAN_BOT_MENTION_STRING_GLOBAL = os.getenv("BRIAN_BOT_MENTION_STRING")
    STEWIE_BOT_MENTION_STRING_GLOBAL = os.getenv("STEWIE_BOT_MENTION_STRING")

    # Convert global mention strings to integer IDs for comparison
    try:
        if BRIAN_BOT_MENTION_STRING_GLOBAL:
            BRIAN_BOT_ID_INT = int(BRIAN_BOT_MENTION_STRING_GLOBAL.replace('<@', '').replace('>', ''))
        else:
            print("WARNING: BRIAN_BOT_MENTION_STRING not found in .env. Brian's ID will be None.")
        if STEWIE_BOT_MENTION_STRING_GLOBAL:
            STEWIE_BOT_ID_INT = int(STEWIE_BOT_MENTION_STRING_GLOBAL.replace('<@', '').replace('>', ''))
        else:
            print("WARNING: STEWIE_BOT_MENTION_STRING not found in .env. Stewie's ID will be None.")
    except ValueError as e:
        print(f"ERROR: Failed to convert bot mention string to integer ID during on_ready: {e}. Check .env file format for bot mentions.")
        print(traceback.format_exc())


    # Basic validation and logging for global mention strings and IDs
    print(f"DEBUG: Peter's own mention string: {PETER_BOT_MENTION_STRING} (ID: {PETER_BOT_ID_INT})")
    print(f"DEBUG: Brian's global mention string: {BRIAN_BOT_MENTION_STRING_GLOBAL} (ID: {BRIAN_BOT_ID_INT})")
    print(f"DEBUG: Stewie's global mention string: {STEWIE_BOT_MENTION_STRING_GLOBAL} (ID: {STEWIE_BOT_ID_INT})")

    print(f'Peter Bot logged in as {client.user}')
    print('Peter Bot is ready!')
    # Start the Flask app in a new thread
    # Daemon=True means the thread will automatically exit when the main program exits
    threading.Thread(target=run_flask_app, daemon=True).start()
    print(f"DEBUG: Peter's internal API running on port {PETER_BOT_PORT}")

@client.event
async def on_message(message):
    """
    Event that fires when a message is sent in any channel the bot can see.
    This function now handles both direct queries and inter-bot mentions.
    """
    print(f"\nDEBUG: Peter Bot - Received message: '{message.content}' from {message.author} (ID: {message.author.id})")

    if message.author == client.user:
        print("DEBUG: Peter Bot - Ignoring message from self.")
        return # Ignore messages from self

    user_message_for_orchestrator = ""
    initiator_bot_name = ""
    initiator_mention = ""
    should_initiate_orchestration = False
    human_user_display_name = None # Initialize to None
    is_new_conversation = False # Default for human-initiated messages
    conversation_session_id = None # Default for human-initiated messages, orchestrator will assign/retrieve

    # Determine if the message author is one of the other registered bots
    is_author_another_bot = (message.author.id == BRIAN_BOT_ID_INT) or \
                            (message.author.id == STEWIE_BOT_ID_INT)
    print(f"DEBUG: Peter Bot - Is author another bot? {is_author_another_bot} (Author ID: {message.author.id})")
    print(f"DEBUG: Peter Bot - Brian ID: {BRIAN_BOT_ID_INT}, Stewie ID: {STEWIE_BOT_ID_INT}")


    # Check if this bot (Peter) is mentioned by another bot
    is_mentioned_by_another_bot = False
    if PETER_BOT_MENTION_STRING in message.content:
        if is_author_another_bot:
            is_mentioned_by_another_bot = True
            print(f"DEBUG: Peter Bot - Detected mention from another bot ({message.author.name}).")
        else:
            print("DEBUG: Peter Bot - Mention detected, but author is not a recognized bot (must be human).")


    # 1. Check if this message is a direct query to *this specific bot* (Peter) from a human or an explicit command.
    # This should take precedence for initial conversation start.
    if message.content.lower().startswith('!peter'):
        user_message_for_orchestrator = message.content[len('!peter'):].strip()
        should_initiate_orchestration = True
        initiator_bot_name = "Peter"
        initiator_mention = PETER_BOT_MENTION_STRING
        human_user_display_name = message.author.display_name # Capture human user's display name
        print("DEBUG: Peter Bot - Detected direct command '!peter'.")
    elif client.user.mentioned_in(message) and not is_author_another_bot: # Only if mentioned by a human
        # If Peter is mentioned, and it's NOT by another bot (meaning it's from a human)
        user_message_for_orchestrator = message.content.replace(PETER_BOT_MENTION_STRING, '').strip()
        should_initiate_orchestration = True
        initiator_bot_name = "Peter"
        initiator_mention = PETER_BOT_MENTION_STRING
        human_user_display_name = message.author.display_name # Capture human user's display name
        print("DEBUG: Peter Bot - Detected direct mention from human user.")

    # 2. Backup/Inter-bot conversation: If Peter is mentioned by another bot, he should join.
    # This is a backup if the direct query logic didn't trigger it, and ensures inter-bot turns.
    if not should_initiate_orchestration and is_mentioned_by_another_bot:
        should_initiate_orchestration = True
        # For inter-bot mentions, send the full message content as context
        user_message_for_orchestrator = message.content
        initiator_bot_name = "Peter"
        initiator_mention = PETER_BOT_MENTION_STRING
        # When another bot initiates, human_user_display_name remains None, which is fine for the LLM prompt
        print("DEBUG: Peter Bot - Initiating orchestration due to inter-bot mention.")


    if not should_initiate_orchestration:
        print("DEBUG: Peter Bot - Not the designated initiator for this message. Ignoring.")
        return # If this bot is not the designated initiator for this message, ignore.

    if not user_message_for_orchestrator:
        await message.channel.send("Heheheh, what do you want? Don't make me use my outside voice!")
        print("DEBUG: Peter Bot - Empty user message after parsing. Sent fallback.")
        return

    print(f"DEBUG: Peter Bot - Initiating Orchestration for message from {message.author} (Type: {initiator_bot_name}): {user_message_for_orchestrator[:50]}... Sending to orchestrator...")

    async with message.channel.typing():
        try:
            payload = {
                "user_query": user_message_for_orchestrator,
                "channel_id": message.channel.id,
                "initiator_bot_name": initiator_bot_name,
                "initiator_mention": initiator_mention,
                "human_user_display_name": human_user_display_name,
                "is_new_conversation": is_new_conversation, # Pass the flag (will be False for human-init)
                "conversation_session_id": conversation_session_id # Pass the ID (will be None for human-init)
            }
            # Increased timeout to 60 seconds
            post_to_orchestrator = functools.partial(
                requests.post,
                ORCHESTRATOR_API_URL,
                json=payload,
                timeout=60 # Increased timeout
            )
            await client.loop.run_in_executor(None, post_to_orchestrator)

            print("DEBUG: Message sent to orchestrator. Waiting for orchestrator to send Discord messages.")
        except requests.exceptions.Timeout:
            await message.channel.send("Heheheh, I think the internet's broken. Or maybe it's just slow like Lois when she tries to cook my dinner.")
            print(f"ERROR: ConnectionError: Timeout when sending to orchestrator. {traceback.format_exc()}")
        except requests.exceptions.ConnectionError:
            await message.channel.send("Ah, crap. The orchestrator's not answering. Probably busy with some fancy Brian stuff, or Stewie's trying to take it over. This is dumb.")
            print(f"ERROR: ConnectionError: Orchestrator server might not be running or API URL is incorrect. {traceback.format_exc()}")
        except Exception as e:
            print(f"ERROR: Error sending message to orchestrator: {e}")
            print(traceback.format_exc()) # Log full traceback
            await message.channel.send("Holy crap, something went wrong! Peter can't figure it out. Probably Brian's fault.")

# --- Main execution ---
if __name__ == '__main__':
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("ERROR: Invalid Discord bot token for Peter. Please check your DISCORD_BOT_TOKEN_PETER environment variable.")
    except Exception as e:
        print(f"CRITICAL: An unexpected error occurred while running Peter Bot's main Discord client: {e}")
        print(traceback.format_exc()) # Log full traceback

