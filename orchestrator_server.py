import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import threading
import time # For simulating delays

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)

# --- Orchestrator Configuration ---
ORCHESTRATOR_PORT = 5003 # The port this orchestrator server will listen on

# API URLs for Peter and Brian's bots (these will be new endpoints in their files)
PETER_BOT_LLM_API_URL = os.getenv("PETER_BOT_LLM_API_URL")
PETER_BOT_DISCORD_SEND_API_URL = os.getenv("PETER_BOT_DISCORD_SEND_API_URL")
BRIAN_BOT_LLM_API_URL = os.getenv("BRIAN_BOT_LLM_API_URL")
BRIAN_BOT_DISCORD_SEND_API_URL = os.getenv("BRIAN_BOT_DISCORD_SEND_API_URL")

# Check if all necessary environment variables are set
if not all([PETER_BOT_LLM_API_URL, PETER_BOT_DISCORD_SEND_API_URL,
            BRIAN_BOT_LLM_API_URL, BRIAN_BOT_DISCORD_SEND_API_URL]):
    print("Error: One or more orchestrator API URLs not found in environment variables.")
    print("Please set: PETER_BOT_LLM_API_URL, PETER_BOT_DISCORD_SEND_API_URL,")
    print("             BRIAN_BOT_LLM_API_URL, BRIAN_BOT_DISCORD_SEND_API_URL in your .env file.")
    exit(1)

@app.route('/orchestrate', methods=['POST'])
def orchestrate_conversation():
    """
    Main endpoint for the orchestrator.
    Receives the user's message and channel ID from Peter or Brian's bot.
    Manages the conversation flow between Peter and Brian.
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    user_query = data.get("user_query")
    channel_id = data.get("channel_id")
    initiator_bot_name = data.get("initiator_bot_name") # "Peter" or "Brian"
    initiator_mention = data.get("initiator_mention") # e.g., "<@PeterBotID>"

    if not all([user_query, channel_id, initiator_bot_name, initiator_mention]):
        return jsonify({"error": "Missing required data (user_query, channel_id, initiator_bot_name, initiator_mention)"}), 400

    print(f"Orchestrator received request from {initiator_bot_name} for user query: '{user_query}' in channel {channel_id}")

    peter_response = ""
    brian_response = ""

    try:
        # --- Step 1: Get Peter's initial response ---
        # Peter always responds first to the user's direct query
        print("Orchestrator requesting Peter's initial response...")
        peter_llm_payload = {
            "user_query": user_query,
            "context_type": "initial_response", # Indicate this is an initial response
            "other_bot_mention": initiator_mention # Pass the initiator's mention for context if needed
        }
        peter_llm_res = requests.post(PETER_BOT_LLM_API_URL, json=peter_llm_payload)
        peter_llm_res.raise_for_status()
        peter_response = peter_llm_res.json().get("response_text", "Peter is confused.")
        print(f"Peter's initial response generated: {peter_response[:50]}...")

        # --- Step 2: Instruct Peter to send his response to Discord ---
        print("Orchestrator instructing Peter to send to Discord...")
        peter_discord_payload = {
            "message_content": peter_response,
            "channel_id": channel_id
        }
        requests.post(PETER_BOT_DISCORD_SEND_API_URL, json=peter_discord_payload)
        # No need to wait for response, it's fire-and-forget for sending

        # --- Simulate a short delay for natural conversation ---
        time.sleep(2)

        # --- Step 3: Get Brian's reaction response ---
        # Brian reacts to both the user's query and Peter's response
        print("Orchestrator requesting Brian's reaction...")
        brian_llm_payload = {
            "user_query": user_query,
            "context_type": "reaction_response", # Indicate this is a reaction
            "other_bot_response": peter_response,
            "other_bot_mention": PETER_BOT_LLM_API_URL.split('/')[2].split(':')[0] # Placeholder if Peter's mention isn't passed directly
        }
        # We need Peter's actual mention string for Brian's prompt.
        # For now, let's assume Peter's bot will pass its own mention when it calls the orchestrator.
        # Or, the orchestrator needs to know Peter's bot ID to construct it.
        # For simplicity, let's assume PETER_BOT_MENTION_STRING is passed from Peter's bot
        # and BRIAN_BOT_MENTION_STRING is passed from Brian's bot to the orchestrator.
        # This will be handled in the updated Peter/Brian bots.

        # Let's refine the payload to Brian to include Peter's actual mention string
        brian_llm_payload = {
            "user_query": user_query,
            "context_type": "reaction_response",
            "other_bot_response": peter_response,
            "other_bot_mention": data.get("peter_mention_string") # This will come from Peter's bot
        }

        brian_llm_res = requests.post(BRIAN_BOT_LLM_API_URL, json=brian_llm_payload)
        brian_llm_res.raise_for_status()
        brian_response = brian_llm_res.json().get("response_text", "Brian is silent.")
        print(f"Brian's reaction generated: {brian_response[:50]}...")

        # --- Step 4: Instruct Brian to send his response to Discord ---
        print("Orchestrator instructing Brian to send to Discord...")
        brian_discord_payload = {
            "message_content": brian_response,
            "channel_id": channel_id
        }
        requests.post(BRIAN_BOT_DISCORD_SEND_API_URL, json=brian_discord_payload)

        return jsonify({"status": "Conversation orchestrated successfully"}), 200

    except requests.exceptions.ConnectionError as e:
        error_msg = f"Orchestrator Connection Error: One of the bot APIs is unreachable. Details: {e}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500
    except requests.exceptions.HTTPError as e:
        error_msg = f"Orchestrator HTTP Error: API returned an error. Status: {e.response.status_code}, Response: {e.response.text}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500
    except Exception as e:
        error_msg = f"Orchestrator General Error: {e}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500

def run_flask_app():
    """
    Function to run the Flask app in a separate thread.
    """
    print(f"Orchestrator server starting on port {ORCHESTRATOR_PORT}...")
    app.run(host='0.0.0.0', port=ORCHESTRATOR_PORT, debug=False, use_reloader=False)

if __name__ == '__main__':
    # Start the Flask app in a new thread
    threading.Thread(target=run_flask_app, daemon=True).start()
    print("Orchestrator server thread started. Waiting for requests...")
    # Keep the main thread alive if needed, or just let the Flask thread run.
    # For a simple server, this is fine. For more complex apps, you might have a main loop here.
    try:
        while True:
            time.sleep(1) # Keep main thread alive
    except KeyboardInterrupt:
        print("Orchestrator server stopped.")

