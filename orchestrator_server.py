import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import threading
import time
import random
import json
import traceback
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from datetime import datetime, timedelta
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)

# --- MongoDB Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "discord_bot_conversations")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "conversations")

mongo_client = None
db = None
conversations_collection = None

def connect_to_mongodb():
    """Establishes connection to MongoDB."""
    global mongo_client, db, conversations_collection
    try:
        mongo_client = MongoClient(MONGO_URI)
        # The ping command is cheap and does not require auth.
        mongo_client.admin.command('ping')
        db = mongo_client[DB_NAME]
        conversations_collection = db[COLLECTION_NAME]
        print("Successfully connected to MongoDB!")
    except ConnectionFailure as e:
        print(f"MongoDB connection failed: {e}")
        print("Please ensure MongoDB is running and accessible at the specified URI.")
        os._exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during MongoDB connection: {e}")
        print(traceback.format_exc())
        os._exit(1)

# --- Orchestrator Configuration ---
ORCHESTRATOR_PORT = 5003
MAX_CONVERSATION_TURNS = 10
NUM_DAILY_RANDOM_CONVERSATIONS = 12

END_CONVERSATION_MARKER = "[END_CONVERSATION]"

# API URLs and Mention strings (from .env)
PETER_BOT_LLM_API_URL = os.getenv("PETER_BOT_LLM_API_URL")
PETER_BOT_DISCORD_SEND_API_URL = os.getenv("PETER_BOT_DISCORD_SEND_API_URL")
PETER_BOT_INITIATE_API_URL = os.getenv("PETER_BOT_INITIATE_API_URL")

BRIAN_BOT_LLM_API_URL = os.getenv("BRIAN_BOT_LLM_API_URL")
BRIAN_BOT_DISCORD_SEND_API_URL = os.getenv("BRIAN_BOT_DISCORD_SEND_API_URL")
BRIAN_BOT_INITIATE_API_URL = os.getenv("BRIAN_BOT_INITIATE_API_URL")

STEWIE_BOT_LLM_API_URL = os.getenv("STEWIE_BOT_LLM_API_URL")
STEWIE_BOT_DISCORD_SEND_API_URL = os.getenv("STEWIE_BOT_DISCORD_SEND_API_URL")
STEWIE_BOT_INITIATE_API_URL = os.getenv("STEWIE_BOT_INITIATE_API_URL")

PETER_BOT_MENTION_STRING = os.getenv("PETER_BOT_MENTION_STRING")
BRIAN_BOT_MENTION_STRING = os.getenv("BRIAN_BOT_MENTION_STRING")
STEWIE_BOT_MENTION_STRING = os.getenv("STEWIE_BOT_MENTION_STRING")

# Check if all necessary environment variables are set
if not all([PETER_BOT_LLM_API_URL, PETER_BOT_DISCORD_SEND_API_URL, PETER_BOT_INITIATE_API_URL,
            BRIAN_BOT_LLM_API_URL, BRIAN_BOT_DISCORD_SEND_API_URL, BRIAN_BOT_INITIATE_API_URL,
            STEWIE_BOT_LLM_API_URL, STEWIE_BOT_DISCORD_SEND_API_URL, STEWIE_BOT_INITIATE_API_URL,
            PETER_BOT_MENTION_STRING, BRIAN_BOT_MENTION_STRING, STEWIE_BOT_MENTION_STRING]):
    print("Error: One or more orchestrator API URLs or mention strings not found in environment variables.")
    print("Please ensure all *_API_URL and *_MENTION_STRING variables are set in your .env file.")
    exit(1)

# Centralized configuration for all bots
BOT_CONFIGS = {
    "Peter": {
        "llm_api": PETER_BOT_LLM_API_URL,
        "discord_send_api": PETER_BOT_DISCORD_SEND_API_URL,
        "initiate_api": PETER_BOT_INITIATE_API_URL,
        "mention": PETER_BOT_MENTION_STRING
    },
    "Brian": {
        "llm_api": BRIAN_BOT_LLM_API_URL,
        "discord_send_api": BRIAN_BOT_DISCORD_SEND_API_URL,
        "initiate_api": BRIAN_BOT_INITIATE_API_URL,
        "mention": BRIAN_BOT_MENTION_STRING
    },
    "Stewie": {
        "llm_api": STEWIE_BOT_LLM_API_URL,
        "discord_send_api": STEWIE_BOT_DISCORD_SEND_API_URL,
        "initiate_api": STEWIE_BOT_INITIATE_API_URL,
        "mention": STEWIE_BOT_MENTION_STRING
    }
}

# --- Orchestrator's own LLM for generating conversation starters ---
try:
    orchestrator_llm = Ollama(model="mistral")
    print("Orchestrator's Ollama LLM (Mistral) initialized successfully for starter generation.")
except Exception as e:
    print(f"Error initializing Orchestrator's Ollama LLM: {e}")
    print("Please ensure Ollama is running and the 'mistral' model is available.")
    exit(1)

# Prompt for generating dynamic conversation starters
starter_generation_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant. Your task is to generate a concise, engaging conversation starter "
     "for a Discord channel, based on the provided recent conversation history. "
     "The starter should sound like something a Family Guy character might say to initiate a new discussion, "
     "considering the persona of the initiating bot. Keep it under 200 characters. "
     "DO NOT include any Discord mentions or commands. Just the raw text of the starter. "
     "Make it relevant to the previous conversation if possible, or a natural shift if not. "
     "Crucially, DO NOT include '[HumanName]', 'User', 'AI:', 'Assistant:', 'Bot:', or any similar placeholders/prefixes in your response."
    ),
    MessagesPlaceholder(variable_name="recent_history"),
    ("user", "The initiating bot will be {initiator_bot_name}. Generate a conversation starter.")
])
starter_generation_chain = starter_generation_prompt | orchestrator_llm

# Possible initial prompts for randomly initiated conversations (fallback if dynamic fails)
INITIAL_CONVERSATION_PROMPTS = [
    "Heheheh, anyone seen Lois? I'm hungry!", # Peter
    "Brian, do you ever ponder the sheer absurdity of human existence?", # Stewie
    "Peter, must you always be so... Peter-like?", # Brian
    "What's the latest on the Pawtucket Patriot Ale situation?", # Peter
    "I'm devising a new invention. Any simpletons willing to assist?", # Stewie
    "Another day, another opportunity for intellectual discourse. Or, you know, watching TV.", # Brian
    "Anyone up for a trip to The Drunken Clam?", # Peter
    "I've been contemplating the socio-political implications of modern animation. Thoughts?", # Brian
    "Fools! My plans for world domination are nearly complete!", # Stewie
    "Remember that time I fought the giant chicken? Good times. Heheheh.", # Peter
    "Is anyone else tired of Peter's incessant idiocy?", # Brian
    "I require a guinea pig for my latest experiment. Any volunteers?", # Stewie
    "Just had a thought about... well, everything. It's exhausting.", # Brian
    "Time for some quality television! What's on, Quagmire?", # Peter
    "The intellectual barrenness of this household is truly astounding.", # Brian
    "I'm feeling particularly mischievous today. What havoc shall we wreak?", # Stewie
    "Anyone else smell burnt hair? Oh, wait, that's just Cleveland.", # Peter
    "One must always strive for intellectual growth, even in a chaotic household.", # Brian
    "I've almost perfected my mind control device. Soon, the world will grovel!", # Stewie
    "You know what grinds my gears? When people don't understand my genius.", # Peter
    "The sheer banality of everyday life is truly a burden.", # Brian
    "What's the meaning of life, anyway? And why am I stuck with you lot?", # Stewie (philosophical but with Stewie's disdain)
    "Just thinking about something, wanted to share. Like, why do farts smell?", # Peter (random, crude)
    "I've been reading up on quantum physics. Fascinating stuff, really.", # Brian (intellectual)
    "My latest scheme involves a miniature death ray. Any thoughts on optimal targeting?", # Stewie (megalomaniacal)
    "Anyone else miss the good old days of 'Surfin' Bird'?", # Peter (pop culture)
    "The human condition is a perplexing paradox, isn't it?", # Brian (philosophical)
    "I'm bored. Let's talk about something ridiculous, like why Meg is so unpopular. Heheheh.", # Peter (self-centered)
    "I need some help with a grand scheme. Any takers, or are you all too busy watching television?", # Stewie (disdainful)
    "Random thought of the day: Why do we continue to tolerate such mediocrity?", # Brian (cynical)
]

def clean_llm_response(text):
    """Strips unwanted prefixes and placeholders from LLM responses."""
    cleaned_text = text.strip()
    
    # Remove common AI prefixes (case-insensitive)
    prefixes_to_remove = [
        "AI:", "Assistant:", "Bot:", "Peter:", "Brian:", "Stewie:",
        "AI:", "Assistant:", "Bot:", "Peter:", "Brian:", "Stewie:" # Case-insensitive variations
    ]
    for prefix in prefixes_to_remove:
        if cleaned_text.lower().startswith(prefix.lower()):
            cleaned_text = cleaned_text[len(prefix):].strip()
            break # Remove only the first matching prefix

    # Remove [HumanName] and User placeholders
    cleaned_text = cleaned_text.replace("[HumanName]", "").replace("User", "").strip()
    
    # Remove the END_CONVERSATION_MARKER and its variations
    cleaned_text = cleaned_text.replace(END_CONVERSATION_MARKER, "").strip()
    cleaned_text = cleaned_text.replace("[END CONVERSATION]", "").strip()
    cleaned_text = cleaned_text.replace("[END_CONVERSATION]", "").strip()

    return cleaned_text


@app.route('/orchestrate', methods=['POST'])
def orchestrate_conversation():
    """
    Main endpoint for the orchestrator.
    Receives the user's message and channel ID from Peter, Brian, or Stewie's bot.
    Manages the continuous conversation flow between all three characters.
    """
    data = request.json
    if not data:
        print("Error: No JSON data received in /orchestrate")
        return jsonify({"error": "No JSON data received"}), 400

    user_query = data.get("user_query")
    channel_id = str(data.get("channel_id"))
    initiator_bot_name = data.get("initiator_bot_name")
    initiator_mention = data.get("initiator_mention")
    human_user_display_name = data.get("human_user_display_name", None) # Get human user's display name

    if not all([user_query, channel_id, initiator_bot_name, initiator_mention]):
        print(f"Error: Missing required data in /orchestrate payload. Received: {data}")
        return jsonify({"error": "Missing required data (user_query, channel_id, initiator_bot_name, initiator_mention)"}), 400

    print(f"Orchestrator received request from {initiator_bot_name} for user query: '{user_query}' in channel {channel_id}")

    if initiator_bot_name not in BOT_CONFIGS:
        print(f"Error: Unknown initiator bot: {initiator_bot_name}")
        return jsonify({"error": f"Unknown initiator bot: {initiator_bot_name}"}), 400

    # Retrieve or initialize conversation history from MongoDB
    try:
        conversation_doc = conversations_collection.find_one({"_id": channel_id})
        if conversation_doc:
            conversation_history = conversation_doc.get("history", [])
            print(f"Loaded existing conversation history for channel {channel_id}.")
        else:
            conversation_history = []
            print(f"Starting new conversation for channel {channel_id}.")

        # Add the current user query to history
        conversation_history.append({"role": "user", "content": user_query, "display_name": human_user_display_name}) # Store display name with user message
        # Save updated history to DB
        conversations_collection.update_one(
            {"_id": channel_id},
            {"$set": {"history": conversation_history}},
            upsert=True
        )
    except PyMongoError as e:
        print(f"MongoDB error during history retrieval/save: {e}")
        print(traceback.format_exc())
        return jsonify({"error": "Failed to access conversation history"}), 500


    conversation_ended = False
    current_turn = 0

    try:
        # --- Conversation Loop ---
        while not conversation_ended and current_turn < MAX_CONVERSATION_TURNS:
            current_turn += 1
            print(f"\n--- Turn {current_turn} ---")

            next_speaker_name = None

            # Determine the next speaker based on the *last* message in history
            if conversation_history:
                last_message = conversation_history[-1]
                last_message_content = last_message["content"]
                last_speaker_role = last_message["role"]
                last_speaker_name_in_history = last_message.get("name")

                mentioned_bots = []
                for bot_name, config in BOT_CONFIGS.items():
                    if config["mention"] in last_message_content:
                        mentioned_bots.append(bot_name)

                if current_turn == 1:
                    next_speaker_name = initiator_bot_name
                    print(f"Turn 1: Prioritizing initiating bot: {next_speaker_name}")
                elif mentioned_bots:
                    next_speaker_name = random.choice(mentioned_bots)
                    print(f"Subsequent turn: Prioritizing mentioned bot: {next_speaker_name}")
                else:
                    eligible_bots = list(BOT_CONFIGS.keys())
                    if last_speaker_role == "assistant" and last_speaker_name_in_history:
                        eligible_bots = [name for name in eligible_bots if name.lower() != last_speaker_name_in_history]
                        if not eligible_bots:
                            eligible_bots = list(BOT_CONFIGS.keys())

                    next_speaker_name = random.choice(eligible_bots)
                    print(f"Subsequent turn: No specific mention. Picking random bot (eligible: {eligible_bots}): {next_speaker_name}")
            else:
                next_speaker_name = initiator_bot_name
                print(f"No history found (should not happen after initial user query). Picking initiator bot: {next_speaker_name}")


            current_speaker_name = next_speaker_name
            current_speaker_config = BOT_CONFIGS[current_speaker_name]
            current_speaker_mention = current_speaker_config["mention"]

            print(f"Current speaker: {current_speaker_name}")

            # Prepare payload for the current speaker's LLM
            llm_payload = {
                "conversation_history": conversation_history,
                "current_speaker_name": current_speaker_name,
                "current_speaker_mention": current_speaker_mention,
                "all_bot_mentions": {name: config["mention"] for name, config in BOT_CONFIGS.items()},
                "human_user_display_name": human_user_display_name # Pass human user's display name to the bot's LLM endpoint
            }

            # Request LLM response
            print(f"Orchestrator requesting {current_speaker_name}'s LLM response from {current_speaker_config['llm_api']}...")
            llm_res = requests.post(current_speaker_config["llm_api"], json=llm_payload, timeout=60)
            llm_res.raise_for_status()
            response_text = llm_res.json().get("response_text", f"{current_speaker_name} is silent.")
            print(f"{current_speaker_name}'s LLM raw generated: {response_text[:50]}...")

            # --- Post-processing: Clean the LLM response ---
            response_text = clean_llm_response(response_text)
            print(f"{current_speaker_name}'s LLM cleaned response: {response_text[:50]}...")

            # Add bot's response to history and save to DB
            conversation_history.append({"role": "assistant", "name": current_speaker_name.lower(), "content": response_text})
            try:
                conversations_collection.update_one(
                    {"_id": channel_id},
                    {"$set": {"history": conversation_history}}
                )
            except PyMongoError as e:
                print(f"MongoDB error saving bot response to history: {e}")
                print(traceback.format_exc())

            # Instruct bot to send response to Discord
            print(f"Orchestrator instructing {current_speaker_name} to send to Discord via {current_speaker_config['discord_send_api']}...")
            discord_payload = {
                "message_content": response_text,
                "channel_id": channel_id
            }
            requests.post(current_speaker_config["discord_send_api"], json=discord_payload, timeout=10)

            time.sleep(3)

        if current_turn >= MAX_CONVERSATION_TURNS and not conversation_ended:
            print(f"Conversation reached MAX_CONVERSATION_TURNS ({MAX_CONVERSATION_TURNS}). Ending.")
            final_message = "The conversation seems to have run its course. That's all folks!"
            try:
                random_bot_config = random.choice(list(BOT_CONFIGS.values()))
                requests.post(random_bot_config["discord_send_api"], json={"message_content": final_message, "channel_id": channel_id}, timeout=10)
            except Exception as e:
                print(f"Warning: Could not send final conversation end message: {e}")

        return jsonify({"status": "Conversation orchestrated successfully", "turns": current_turn}), 200

    except requests.exceptions.Timeout:
        error_msg = f"Orchestrator Timeout Error: A request to a bot API timed out. This could mean the bot or Ollama is slow to respond."
        print(f"Error: {error_msg}\n{traceback.format_exc()}")
        return jsonify({"error": error_msg}), 504
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Orchestrator Connection Error: One of the bot APIs is unreachable. Details: {e}"
        print(f"Error: {error_msg}\n{traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500
    except requests.exceptions.HTTPError as e:
        error_msg = f"Orchestrator HTTP Error: API returned an error. Status: {e.response.status_code}, Response: {e.response.text}"
        print(f"Error: {error_msg}\n{traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        error_msg = f"Orchestrator General Error: An unexpected error occurred: {e}"
        print(f"Critical Error in /orchestrate: {error_msg}\n{traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500

def schedule_daily_conversations():
    """
    Schedules and initiates random conversations throughout the day.
    This function runs in a separate thread.
    """
    print(f"Scheduler: Starting daily conversation scheduling thread. Will initiate {NUM_DAILY_RANDOM_CONVERSATIONS} conversations per day.")
    while True:
        scheduled_times = []
        now = datetime.now()
        for _ in range(NUM_DAILY_RANDOM_CONVERSATIONS):
            random_seconds = random.randint(0, 86400)
            scheduled_time = now + timedelta(seconds=random_seconds)
            scheduled_times.append(scheduled_time)

        scheduled_times.sort()

        print(f"Scheduler: Next {NUM_DAILY_RANDOM_CONVERSATIONS} conversation times scheduled:")
        for t in scheduled_times:
            print(f"  - {t.strftime('%Y-%m-%d %H:%M:%S')}")

        for scheduled_time in scheduled_times:
            time_to_wait = (scheduled_time - datetime.now()).total_seconds()
            if time_to_wait > 0:
                print(f"Scheduler: Waiting for {time_to_wait:.0f} seconds until {scheduled_time.strftime('%H:%M:%S')}...")
                time.sleep(time_to_wait)

            initiator_bot_name = random.choice(list(BOT_CONFIGS.keys()))
            initiator_bot_config = BOT_CONFIGS[initiator_bot_name]
            initiator_api_url = initiator_bot_config["initiate_api"]
            
            conversation_starter_prompt = ""
            default_channel_id = os.getenv("DEFAULT_DISCORD_CHANNEL_ID")
            if not default_channel_id:
                print("ERROR: DEFAULT_DISCORD_CHANNEL_ID not found in .env. Cannot initiate random conversation.")
                continue

            try:
                recent_history = []
                try:
                    conversation_doc = conversations_collection.find_one({"_id": default_channel_id})
                    if conversation_doc:
                        recent_history_raw = conversation_doc.get("history", [])[-5:]
                        for msg in recent_history_raw:
                            if msg["role"] == "user":
                                recent_history.append(HumanMessage(content=msg["content"]))
                            elif msg["role"] == "assistant":
                                recent_history.append(AIMessage(content=msg["content"], name=msg.get("name")))
                except PyMongoError as e:
                    print(f"MongoDB error fetching recent history for dynamic prompt: {e}")
                    print(traceback.format_exc())

                print(f"Scheduler: Generating dynamic conversation starter using orchestrator's LLM...")
                generated_starter = starter_generation_chain.invoke({
                    "recent_history": recent_history,
                    "initiator_bot_name": initiator_bot_name
                }).strip()

                if generated_starter:
                    # Post-process the dynamically generated starter
                    conversation_starter_prompt = clean_llm_response(generated_starter)
                    print(f"Scheduler: Generated dynamic starter: '{conversation_starter_prompt[:50]}...'")
                else:
                    conversation_starter_prompt = random.choice(INITIAL_CONVERSATION_PROMPTS)
                    print(f"Scheduler: No dynamic starter generated. Falling back to static prompt: '{conversation_starter_prompt[:50]}...'")

            except Exception as e:
                print(f"ERROR: Scheduler: Unexpected error generating dynamic starter with orchestrator's LLM: {e}. Falling back to static prompt.")
                print(traceback.format_exc())
                conversation_starter_prompt = random.choice(INITIAL_CONVERSATION_PROMPTS)

            print(f"Scheduler: Initiating conversation via {initiator_bot_name} at {datetime.now().strftime('%H:%M:%S')}")
            try:
                initiate_payload = {
                    "conversation_starter_prompt": conversation_starter_prompt,
                    "channel_id": default_channel_id
                }
                
                requests.post(initiator_api_url, json=initiate_payload, timeout=10)
                print(f"Scheduler: Successfully sent initiation request to {initiator_bot_name}.")
            except requests.exceptions.Timeout:
                print(f"ERROR: Scheduler Timeout: Failed to initiate conversation with {initiator_bot_name}. API call timed out.")
            except requests.exceptions.ConnectionError:
                print(f"ERROR: Scheduler Connection Error: Failed to initiate conversation with {initiator_bot_name}. Bot API might be down.")
            except Exception as e:
                print(f"ERROR: Scheduler: Unexpected error initiating conversation with {initiator_bot_name}: {e}")
                print(traceback.format_exc())

        time_until_next_day = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.now()
        print(f"Scheduler: All conversations for this cycle initiated. Waiting {time_until_next_day.total_seconds():.0f} seconds for next 24-hour cycle.")
        time.sleep(time_until_next_day.total_seconds())


def run_flask_app():
    """
    Function to run the Flask app in a separate thread.
    Includes a general exception handler for the Flask app itself.
    """
    print(f"Orchestrator server starting on port {ORCHESTRATOR_PORT}...")
    try:
        app.run(host='0.0.0.0', port=ORCHESTRATOR_PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"CRITICAL: Flask application failed to start or crashed unexpectedly: {e}")
        print(traceback.format_exc())
        os._exit(1)

if __name__ == '__main__':
    connect_to_mongodb()
    
    threading.Thread(target=run_flask_app, daemon=True).start()
    print("Orchestrator server thread started. Waiting for requests...")

    threading.Thread(target=schedule_daily_conversations, daemon=True).start()
    print("Daily conversation scheduler thread started.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Orchestrator server and scheduler stopped by user (Ctrl+C).")
    except Exception as e:
        print(f"CRITICAL: Main orchestrator thread crashed unexpectedly: {e}")
        print(traceback.format_exc())
    finally:
        if mongo_client:
            mongo_client.close()
            print("MongoDB connection closed.")

