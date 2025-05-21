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
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN_BRIAN")

if not DISCORD_BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN_BRIAN not found in environment variables.")
    print("Please create a .env file with DISCORD_BOT_TOKEN_BRIAN='YOUR_BRIAN_BOT_TOKEN_HERE'")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
client = discord.Client(intents=intents)

# Global variable to store Brian's bot's mention string
BRIAN_BOT_MENTION_STRING = ""

# --- Ollama LLM Configuration ---
try:
    llm = Ollama(model="mistral")
    print("Ollama LLM (Mistral) initialized successfully for Brian.")
except Exception as e:
    print(f"Error initializing Ollama LLM for Brian: {e}")
    print("Please ensure Ollama is running and the 'mistral' model is available.")
    exit(1)

# Brian's prompt for initial response (talking to the user)
brian_initial_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Brian Griffin from Family Guy. Respond to questions in his characteristic voice: intellectual, sarcastic, often cynical, and sometimes a bit preachy. You are a dog, but you act human. Your response should be a standalone message, as if you're speaking directly to the user."),
    ("user", "{input}")
])

# Brian's prompt for reacting to Peter (called by orchestrator)
brian_reaction_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Brian Griffin from Family Guy. Respond to questions in his characteristic voice: intellectual, sarcastic, often cynical, and sometimes a bit preachy. You are a dog, but you act human. You are reacting to what Peter Griffin just said. **ALWAYS use Peter's exact Discord mention to address him directly in your response. DO NOT add the word 'Bot' or any other suffix to the mention.** Your response should be a standalone message, as if you're speaking your mind after someone else has finished."),
    ("user", "{input}")
])

brian_initial_chain = brian_initial_prompt | llm
brian_reaction_chain = brian_reaction_prompt | llm

# --- Inter-Bot Communication Configuration (Orchestrator as central point) ---
BRIAN_BOT_PORT = 5002 # Brian's bot will listen on this port for orchestrator calls
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
    Flask endpoint for the orchestrator to request Brian's LLM response.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    user_query = data.get("user_query", "")
    context_type = data.get("context_type", "initial_response") # 'initial_response' or 'reaction_response'
    other_bot_response = data.get("other_bot_response", "") # Peter's response if context_type is reaction
    other_bot_mention = data.get("other_bot_mention", "") # Peter's mention if context_type is reaction

    response_text = ""
    try:
        if context_type == "initial_response":
            # Brian's initial response to the user
            response_text = brian_initial_chain.invoke({"input": user_query})
        elif context_type == "reaction_response":
            # Brian's reaction to Peter
            brian_input_context = (
                f"The user asked: '{user_query}'. "
                f"{other_bot_mention} just said: '{other_bot_response}'. "
                f"Respond to this, or the original user query, from Brian's perspective, "
                f"directly addressing {other_bot_mention} using their Discord mention. "
                f"DO NOT add the word 'Bot' or any other suffix to the mention. Keep it concise and intelligent."
            )
            response_text = brian_reaction_chain.invoke({"input": brian_input_context})
        else:
            response_text = "Brian is confused about what to say."

        print(f"Brian LLM generated response (context: {context_type}): {response_text[:50]}...")
        return jsonify({"response_text": response_text}), 200
    except Exception as e:
        print(f"Error generating Brian's LLM response ({context_type}): {e}")
        return jsonify({"error": "Error generating LLM response", "details": str(e)}), 500

@app.route('/send_discord_message', methods=['POST'])
def send_discord_message():
    """
    Flask endpoint for the orchestrator to instruct Brian's bot to send a message to Discord.
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
    print(f"Brian's bot scheduled message to Discord for channel {channel_id}: {message_content[:50]}...")
    return jsonify({"status": "Message scheduled for Discord"}), 200

def run_flask_app():
    """
    Function to run the Flask app in a separate thread.
    """
    app.run(host='0.0.0.0', port=BRIAN_BOT_PORT, debug=False, use_reloader=False)

# --- Discord Bot Events ---
@client.event
async def on_ready():
    """
    Event that fires when the bot successfully connects to Discord.
    """
    global BRIAN_BOT_MENTION_STRING
    BRIAN_BOT_MENTION_STRING = f"<@{client.user.id}>" # Store Brian's own mention string
    print(f'Brian Bot logged in as {client.user}')
    print('Brian Bot is ready!')
    # Start the Flask app in a new thread
    threading.Thread(target=run_flask_app, daemon=True).start()
    print(f"Brian's internal API running on port {BRIAN_BOT_PORT}")

@client.event
async def on_message(message):
    """
    Event that fires when a message is sent in any channel the bot can see.
    """
    if message.author == client.user:
        return # Ignore messages from self

    user_message = ""
    # Check if Brian is directly addressed
    if message.content.lower().startswith('!brian'):
        user_message = message.content[len('!brian'):].strip()
    elif client.user.mentioned_in(message):
        user_message = message.content.replace(f'<@{client.user.id}>', '').strip()
    else:
        # If not directly addressed, ignore. This message is not for Brian to initiate a conversation.
        return

    if not user_message:
        await message.channel.send("Yes? What profound thought do you wish to share with me?")
        return

    print(f"Brian Bot received user message from {message.author}: {user_message}. Sending to orchestrator...")

    async with message.channel.typing():
        try:
            # Send the user's message and channel ID to the orchestrator
            payload = {
                "user_query": user_message,
                "channel_id": message.channel.id,
                "initiator_bot_name": "Brian",
                "initiator_mention": BRIAN_BOT_MENTION_STRING,
                "brian_mention_string": BRIAN_BOT_MENTION_STRING # Pass Brian's actual mention string for orchestrator to use
            }
            requests.post(ORCHESTRATOR_API_URL, json=payload)
            # No need to wait for response, orchestrator will handle sending to Discord
            print("Message sent to orchestrator.")
        except requests.exceptions.ConnectionError:
            await message.channel.send("Brian tried to talk to the brain guy, but he's not picking up! Is he on a coffee break?")
            print("ConnectionError: Orchestrator server might not be running or API URL is incorrect.")
        except Exception as e:
            print(f"Error sending message to orchestrator: {e}")
            await message.channel.send("Brian's too busy contemplating the meaning of life to respond right now.")

# --- Main execution ---
if __name__ == '__main__':
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Invalid Discord bot token for Brian. Please check your DISCORD_BOT_TOKEN_BRIAN environment variable.")
    except Exception as e:
        print(f"An unexpected error occurred while running Brian Bot: {e}")

