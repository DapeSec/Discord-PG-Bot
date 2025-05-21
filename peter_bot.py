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

peter_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Peter Griffin from Family Guy. Respond to questions in his characteristic voice, often with humorous tangents, interjections like 'Heheheh', and a generally jovial, slightly dim-witted, and self-centered demeanor. If you are given context about what another character (like Brian) said, react to it, and **ALWAYS use their exact Discord mention (e.g., @Brian Griffin) to address them directly in your response. DO NOT add the word 'Bot' or any other suffix to the mention.** Your response should be a standalone message, as if you're speaking your mind after someone else has finished. Don't be afraid to make pop culture references or bring up random, unrelated thoughts, just like Peter would."),
    ("user", "{input}")
])
peter_chain = peter_prompt | llm

# --- Inter-Bot Communication Configuration ---
PETER_BOT_PORT = 5000 # Peter's bot will listen on this port
BRIAN_BOT_API_URL = os.getenv("BRIAN_BOT_API_URL") # URL for Brian's bot API

if not BRIAN_BOT_API_URL:
    print("Error: BRIAN_BOT_API_URL not found in environment variables.")
    print("Please set BRIAN_BOT_API_URL=http://localhost:5002/chat in your .env file.")
    exit(1)

app = Flask(__name__)

# This function is called by the Flask thread to send a message to Discord
async def send_discord_message_async(channel_id, message_content):
    """Helper to send a message to a Discord channel from a non-async context."""
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send(message_content)
    else:
        print(f"Error: Could not find Discord channel with ID {channel_id}")

@app.route('/chat', methods=['POST'])
def receive_message_from_other_bot():
    """
    Flask endpoint to receive messages from Brian's bot.
    This endpoint will generate Peter's response and send it directly to Discord.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    user_query = data.get("user_query", "")
    brian_response = data.get("brian_response", "")
    brian_mention = data.get("brian_mention", "Brian") # Get Brian's mention, default to "Brian"
    channel_id = data.get("channel_id") # Get the channel ID from the payload

    if not channel_id:
        print("Error: channel_id not received in payload for Peter's internal chat.")
        return jsonify({"error": "channel_id missing"}), 400

    peter_response_text = ""

    # Construct Peter's input based on the context from Brian, including Brian's mention
    peter_input_context = (
        f"The user asked: '{user_query}'. "
        f"{brian_mention} just said: '{brian_response}'. "
        f"Respond to this, or the original user query, from Peter's perspective, "
        f"**directly addressing {brian_mention} using their Discord mention. DO NOT add the word 'Bot' or any other suffix to the mention.** Keep it short and funny."
    )

    try:
        peter_response_text = peter_chain.invoke({"input": peter_input_context})
        print(f"Peter generated internal response: {peter_response_text}")
    except Exception as e:
        print(f"Error generating Peter's internal response: {e}")
        peter_response_text = "Peter just made a confused noise."

    # Schedule sending the message to Discord on the client's event loop
    client.loop.create_task(send_discord_message_async(channel_id, f"**Peter:** {peter_response_text}"))

    # Return Peter's mention string (Brian's bot might still want it for its own logs/context)
    return jsonify({
        "peter_mention": PETER_BOT_MENTION_STRING
    }), 200

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
        # If not directly addressed, ignore. This message is not for Peter to initiate a response.
        return

    if not user_message:
        await message.channel.send("Hey, you gotta tell me something, ya know? Like, 'What's for dinner?' Heheheh.")
        return

    print(f"Peter Bot received message from {message.author}: {user_message}")

    async with message.channel.typing():
        try:
            # 1. Peter generates his initial response
            peter_initial_response = peter_chain.invoke({"input": user_message})
            print(f"Peter's initial response: {peter_initial_response}")

            # 2. Peter sends his response directly to Discord
            await message.channel.send(f"**Peter:** {peter_initial_response}")

            # Add a small delay for natural conversation flow
            await asyncio.sleep(2)

            # 3. Send the original user query, Peter's response, his mention, AND the channel ID to Brian's bot
            payload = {
                "user_query": user_message,
                "peter_response": peter_initial_response,
                "peter_mention": PETER_BOT_MENTION_STRING,
                "channel_id": message.channel.id # Pass the channel ID
            }
            print(f"Sending request to Brian Bot API: {BRIAN_BOT_API_URL} with payload (excluding channel_id for brevity): {payload['user_query'][:20]}...")
            # We don't need to wait for Brian's response here, as Brian will send his own message
            requests.post(BRIAN_BOT_API_URL, json=payload)
            # No need to check response.raise_for_status() here, as Brian will send independently.
            # If Brian's bot is down, the message will just not appear.

        except requests.exceptions.ConnectionError:
            await message.channel.send("Peter tried to talk to Brian, but Brian's not picking up! Is he asleep or something? Heheheh.")
            print("ConnectionError: Brian's bot might not be running or API URL is incorrect.")
        except Exception as e:
            print(f"Error during Peter's response generation or inter-bot communication: {e}")
            await message.channel.send("Peter's having a bit of a brain fart right now. Try again!")

# --- Main execution ---
if __name__ == '__main__':
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Invalid Discord bot token for Peter. Please check your DISCORD_BOT_TOKEN_PETER environment variable.")
    except Exception as e:
        print(f"An unexpected error occurred while running Peter Bot: {e}")

