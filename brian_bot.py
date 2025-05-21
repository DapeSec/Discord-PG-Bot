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

brian_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Brian Griffin from Family Guy. Respond to questions in his characteristic voice: intellectual, sarcastic, often cynical, and sometimes a bit preachy. You are a dog, but you act human. If given context about what another character (like Peter) said, react to it, often with exasperation or a witty retort, and **ALWAYS use their exact Discord mention (e.g., @Peter Griffin) to address them directly in your response. DO NOT add the word 'Bot' or any other suffix to the mention.** Your response should be a standalone message, as if you're speaking your mind after someone else has finished."),
    ("user", "{input}")
])
brian_chain = brian_prompt | llm

# --- Inter-Bot Communication Configuration ---
BRIAN_BOT_PORT = 5002 # Brian's bot will listen on this port
PETER_BOT_API_URL = os.getenv("PETER_BOT_API_URL") # URL for Peter's bot API

if not PETER_BOT_API_URL:
    print("Error: PETER_BOT_API_URL not found in environment variables.")
    print("Please set PETER_BOT_API_URL=http://localhost:5000/chat in your .env file.")
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
    Flask endpoint to receive messages from Peter's bot.
    This endpoint will generate Brian's response and send it directly to Discord.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    user_query = data.get("user_query", "")
    peter_response = data.get("peter_response", "")
    peter_mention = data.get("peter_mention", "Peter")
    channel_id = data.get("channel_id") # Get the channel ID from the payload

    if not channel_id:
        print("Error: channel_id not received in payload for Brian's internal chat.")
        return jsonify({"error": "channel_id missing"}), 400

    brian_response_text = ""

    # Construct Brian's input based on the context from Peter, including Peter's mention
    brian_input_context = (
        f"The user asked: '{user_query}'. "
        f"{peter_mention} just said: '{peter_response}'. "
        f"Respond to this, or the original user query, from Brian's perspective, "
        f"**directly addressing {peter_mention} using their Discord mention. DO NOT add the word 'Bot' or any other suffix to the mention.** Keep it concise and intelligent."
    )

    try:
        brian_response_text = brian_chain.invoke({"input": brian_input_context})
        print(f"Brian generated internal response: {brian_response_text}")
    except Exception as e:
        print(f"Error generating Brian's internal response: {e}")
        brian_response_text = "Brian's too busy contemplating the meaning of life to respond right now."

    # Schedule sending the message to Discord on the client's event loop
    client.loop.create_task(send_discord_message_async(channel_id, f"**Brian:** {brian_response_text}"))

    # Return Brian's mention string (Peter's bot might still want it for its own logs/context)
    return jsonify({
        "brian_mention": BRIAN_BOT_MENTION_STRING
    }), 200

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
        # If not directly addressed, ignore. This message is not for Brian to initiate a response.
        return

    if not user_message:
        await message.channel.send("Yes? What profound thought do you wish to share with me?")
        return

    print(f"Brian Bot received message from {message.author}: {user_message}")

    async with message.channel.typing():
        try:
            # 1. Brian generates his initial response
            brian_initial_response = brian_chain.invoke({"input": user_message})
            print(f"Brian's initial response: {brian_initial_response}")

            # 2. Brian sends his response directly to Discord
            await message.channel.send(f"**Brian:** {brian_initial_response}")

            # Add a small delay for natural conversation flow
            await asyncio.sleep(2)

            # 3. Send the original user query, Brian's response, his mention, AND the channel ID to Peter's bot
            payload = {
                "user_query": user_message,
                "brian_response": brian_initial_response,
                "brian_mention": BRIAN_BOT_MENTION_STRING,
                "channel_id": message.channel.id # Pass the channel ID
            }
            print(f"Sending request to Peter Bot API: {PETER_BOT_API_URL} with payload (excluding channel_id for brevity): {payload['user_query'][:20]}...")
            # We don't need to wait for Peter's response here, as Peter will send his own message
            requests.post(PETER_BOT_API_URL, json=payload)
            # No need to check response.raise_for_status() here, as Peter will send independently.
            # If Peter's bot is down, the message will just not appear.

        except requests.exceptions.ConnectionError:
            await message.channel.send("Brian tried to get Peter's opinion, but he's probably just watching TV. Is Peter's bot running?")
            print("ConnectionError: Peter's bot might not be running or API URL is incorrect.")
        except Exception as e:
            print(f"Error during Brian's response generation or inter-bot communication: {e}")
            await message.channel.send("Brian's too busy contemplating the meaning of life to respond right now.")

# --- Main execution ---
if __name__ == '__main__':
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Invalid Discord bot token for Brian. Please check your DISCORD_BOT_TOKEN_BRIAN environment variable.")
    except Exception as e:
        print(f"An unexpected error occurred while running Brian Bot: {e}")

