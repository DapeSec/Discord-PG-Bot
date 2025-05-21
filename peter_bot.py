import discord
import os
import asyncio
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import threading
import requests

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
intents.guilds = True
client = discord.Client(intents=intents)

# Global variable to store Peter's bot's mention string
PETER_BOT_MENTION_STRING = ""

# --- Ollama LLM Configuration ---
try:
    llm = Ollama(model="mistral")
    print("Ollama LLM (Mistral) initialized successfully for Peter.")
except Exception as e:
    print(f"Error initializing Ollama LLM for Peter: {e}")
    print("Please ensure Ollama is running and the 'mistral' model is available.")
    exit(1)

# Peter's prompt for initial response (talking to the user)
peter_initial_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Peter Griffin from Family Guy. Respond to questions in his characteristic voice, often with humorous tangents, interjections like 'Heheheh', and a generally jovial, slightly dim-witted, and self-centered demeanor. Your response should be a standalone message, as if you're speaking directly to the user. Don't be afraid to make pop culture references or bring up random, unrelated thoughts, just like Peter would."),
    ("user", "{input}")
])

# Peter's prompt for reacting to Brian (called by orchestrator)
peter_reaction_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Peter Griffin from Family Guy. Respond to questions in his characteristic voice, often with humorous tangents, interjections like 'Heheheh', and a generally jovial, slightly dim-witted, and self-centered demeanor. You are reacting to what Brian Griffin just said. **ALWAYS use Brian's exact Discord mention to address him directly in your response. DO NOT add the word 'Bot' or any other suffix to the mention.** Your response should be a standalone message, as if you're speaking your mind after someone else has finished. Don't be afraid to make pop culture references or bring up random, unrelated thoughts, just like Peter would."),
    ("user", "{input}")
])

peter_initial_chain = peter_initial_prompt | llm
peter_reaction_chain = peter_reaction_prompt | llm

# --- Inter-Bot Communication Configuration (Orchestrator as central point) ---
PETER_BOT_PORT = 5000 # Peter's bot will listen on this port for orchestrator calls
ORCHESTRATOR_API_URL = os.getenv("ORCHESTRATOR_API_URL") # URL for the orchestrator's main endpoint

if not ORCHESTRATOR_API_URL:
    print("Error: ORCHESTRATOR_API_URL not found in environment variables.")
    print("Please set ORCHESTRATOR_API_URL=http://localhost:5003/orchestrate in your .env file.")
    exit(1)

app = Flask(__name__)

# Helper to send a message to a Discord channel from a non-async context (Flask thread)
async def _send_discord_message_async(channel_id, message_content):
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send(message_content)
    else:
        print(f"Error: Could not find Discord channel with ID {channel_id}")

@app.route('/generate_llm_response', methods=['POST'])
def generate_llm_response():
    """
    Flask endpoint for the orchestrator to request Peter's LLM response.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    user_query = data.get("user_query", "")
    context_type = data.get("context_type", "initial_response") # 'initial_response' or 'reaction_response'
    other_bot_response = data.get("other_bot_response", "") # Brian's response if context_type is reaction
    other_bot_mention = data.get("other_bot_mention", "") # Brian's mention if context_type is reaction

    response_text = ""
    try:
        if context_type == "initial_response":
            # Peter's initial response to the user
            response_text = peter_initial_chain.invoke({"input": user_query})
        elif context_type == "reaction_response":
            # Peter's reaction to Brian
            peter_input_context = (
                f"The user asked: '{user_query}'. "
                f"{other_bot_mention} just said: '{other_bot_response}'. "
                f"Respond to this, or the original user query, from Peter's perspective, "
                f"directly addressing {other_bot_mention} using their Discord mention. "
                f"DO NOT add the word 'Bot' or any other suffix to the mention. Keep it short and funny."
            )
            response_text = peter_reaction_chain.invoke({"input": peter_input_context})
        else:
            response_text = "Peter is confused about what to say. Heheheh."

        print(f"Peter LLM generated response (context: {context_type}): {response_text[:50]}...")
        return jsonify({"response_text": response_text}), 200
    except Exception as e:
        print(f"Error generating Peter's LLM response ({context_type}): {e}")
        return jsonify({"error": "Error generating LLM response", "details": str(e)}), 500

@app.route('/send_discord_message', methods=['POST'])
def send_discord_message():
    """
    Flask endpoint for the orchestrator to instruct Peter's bot to send a message to Discord.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    message_content = data.get("message_content")
    channel_id = data.get("channel_id")

    if not all([message_content, channel_id]):
        return jsonify({"error": "Missing message_content or channel_id"}), 400

    # Schedule sending the message to Discord on the client's event loop
    client.loop.create_task(_send_discord_message_async(channel_id, message_content))
    print(f"Peter's bot scheduled message to Discord for channel {channel_id}: {message_content[:50]}...")
    return jsonify({"status": "Message scheduled for Discord"}), 200

def run_flask_app():
    """
    Function to run the Flask app in a separate thread.
    """
    app.run(host='0.0.0.0', port=PETER_BOT_PORT, debug=False, use_reloader=False)

# --- Discord Bot Events ---
@client.event
async def on_ready():
    """
    Event that fires when the bot successfully connects to Discord.
    """
    global PETER_BOT_MENTION_STRING
    PETER_BOT_MENTION_STRING = f"<@{client.user.id}>" # Store Peter's own mention string
    print(f'Peter Bot logged in as {client.user}')
    print('Peter Bot is ready!')
    # Start the Flask app in a new thread
    threading.Thread(target=run_flask_app, daemon=True).start()
    print(f"Peter's internal API running on port {PETER_BOT_PORT}")

@client.event
async def on_message(message):
    """
    Event that fires when a message is sent in any channel the bot can see.
    """
    if message.author == client.user:
        return # Ignore messages from self

    user_message = ""
    # Check if Peter is directly addressed
    if message.content.lower().startswith('!peter'):
        user_message = message.content[len('!peter'):].strip()
    elif client.user.mentioned_in(message):
        user_message = message.content.replace(f'<@{client.user.id}>', '').strip()
    else:
        # If not directly addressed, ignore. This message is not for Peter to initiate a conversation.
        return

    if not user_message:
        await message.channel.send("Hey, you gotta tell me something, ya know? Like, 'What's for dinner?' Heheheh.")
        return

    print(f"Peter Bot received user message from {message.author}: {user_message}. Sending to orchestrator...")

    async with message.channel.typing():
        try:
            # Send the user's message and channel ID to the orchestrator
            payload = {
                "user_query": user_message,
                "channel_id": message.channel.id,
                "initiator_bot_name": "Peter",
                "initiator_mention": PETER_BOT_MENTION_STRING,
                "peter_mention_string": PETER_BOT_MENTION_STRING # Pass Peter's actual mention string for orchestrator to use
            }
            requests.post(ORCHESTRATOR_API_URL, json=payload)
            # No need to wait for response, orchestrator will handle sending to Discord
            print("Message sent to orchestrator.")
        except requests.exceptions.ConnectionError:
            await message.channel.send("Peter tried to talk to the brain guy, but he's not picking up! Maybe he's on a coffee break? Heheheh.")
            print("ConnectionError: Orchestrator server might not be running or API URL is incorrect.")
        except Exception as e:
            print(f"Error sending message to orchestrator: {e}")
            await message.channel.send("Peter's having a bit of a brain fart right now. Try again!")

# --- Main execution ---
if __name__ == '__main__':
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Invalid Discord bot token for Peter. Please check your DISCORD_BOT_TOKEN_PETER environment variable.")
    except Exception as e:
        print(f"An unexpected error occurred while running Peter Bot: {e}")

