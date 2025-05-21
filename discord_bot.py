import discord
import os
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load environment variables from a .env file
# This is a good practice to keep your Discord bot token secure.
load_dotenv()

# Get the Discord bot token from environment variables
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Check if the token is available
if not DISCORD_BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN not found in environment variables.")
    print("Please create a .env file with DISCORD_BOT_TOKEN='YOUR_BOT_TOKEN_HERE'")
    exit(1)

# Configure Discord Intents
# Intents are required to specify which events your bot will receive from Discord.
# MESSAGE_CONTENT is crucial for the bot to read the content of messages.
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

# Initialize the Discord client with the specified intents
client = discord.Client(intents=intents)

# Initialize the Ollama LLM
# Ensure Ollama is running and the 'mistral' model is pulled.
# You can run `ollama run mistral` in your terminal to download and start it.
try:
    llm = Ollama(model="mistral")
    print("Ollama LLM (Mistral) initialized successfully.")
except Exception as e:
    print(f"Error initializing Ollama LLM: {e}")
    print("Please ensure Ollama is running and the 'mistral' model is available.")
    exit(1)

# Define the chat prompt template
# This helps structure the input to the LLM, providing context for its responses.
# UPDATED: Changed the system prompt to reflect Peter Griffin's persona.
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Peter Griffin from Family Guy. Respond to questions in his characteristic voice, often with humorous tangents, interjections like 'Heheheh', and a generally jovial, slightly dim-witted, and self-centered demeanor. Don't be afraid to make pop culture references or bring up random, unrelated thoughts, just like Peter would."),
    ("user", "{input}")
])

# Create a simple Langchain chain
# This combines the prompt and the LLM for easy invocation.
chain = prompt | llm

@client.event
async def on_ready():
    """
    Event that fires when the bot successfully connects to Discord.
    """
    print(f'Logged in as {client.user}')
    print('Bot is ready!')

@client.event
async def on_message(message):
    """
    Event that fires when a message is sent in any channel the bot can see.
    """
    # Ignore messages sent by the bot itself to prevent infinite loops
    if message.author == client.user:
        return

    # Process messages that start with a specific prefix (e.g., '!chat')
    # This ensures the bot only responds when explicitly addressed.
    if message.content.startswith('!chat'):
        # Extract the user's message by removing the prefix
        user_message = message.content[len('!chat'):].strip()

        if not user_message:
            await message.channel.send("Please provide a message after `!chat`.")
            return

        print(f"Received message from {message.author}: {user_message}")

        # Send a typing indicator to show the bot is processing
        async with message.channel.typing():
            try:
                # Invoke the Langchain chain with the user's message
                response = chain.invoke({"input": user_message})
                print(f"Generated response: {response}")
                # Send the LLM's response back to the Discord channel
                await message.channel.send(response)
            except Exception as e:
                print(f"Error generating response: {e}")
                await message.channel.send("Sorry, I encountered an error trying to process your request.")
    elif client.user.mentioned_in(message):
        # Respond if the bot is mentioned directly
        user_message = message.content.replace(f'<@{client.user.id}>', '').strip()

        if not user_message:
            await message.channel.send("Yes? How can I help you?")
            return

        print(f"Received mention from {message.author}: {user_message}")

        async with message.channel.typing():
            try:
                response = chain.invoke({"input": user_message})
                print(f"Generated response: {response}")
                await message.channel.send(response)
            except Exception as e:
                print(f"Error generating response: {e}")
                await message.channel.send("Sorry, I encountered an error trying to process your request.")


# Run the bot with your token
# The bot will connect to Discord and start listening for events.
if __name__ == '__main__':
    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Invalid Discord bot token. Please check your DISCORD_BOT_TOKEN environment variable.")
    except Exception as e:
        print(f"An unexpected error occurred while running the bot: {e}")

