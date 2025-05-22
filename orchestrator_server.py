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
import uuid

# RAG specific imports
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

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
MAX_CONVERSATION_TURNS = 25
NUM_DAILY_RANDOM_CONVERSATIONS = 24

END_CONVERSATION_MARKER = "[END_CONVERSATION]"

# API URLs and Mention strings (from .env)
PETER_BOT_LLM_API_URL = os.getenv("PETER_BOT_LLM_API_URL", "http://localhost:5005/generate_llm_response")
PETER_BOT_DISCORD_SEND_API_URL = os.getenv("PETER_BOT_DISCORD_SEND_API_URL", "http://localhost:5005/send_discord_message")
PETER_BOT_INITIATE_API_URL = os.getenv("PETER_BOT_INITIATE_API_URL", "http://localhost:5005/initiate_conversation")

BRIAN_BOT_LLM_API_URL = os.getenv("BRIAN_BOT_LLM_API_URL")
BRIAN_BOT_DISCORD_SEND_API_URL = os.getenv("BRIAN_BOT_DISCORD_SEND_API_URL")
BRIAN_BOT_INITIATE_API_URL = os.getenv("BRIAN_BOT_INITIATE_API_URL")

STEWIE_BOT_LLM_API_URL = os.getenv("STEWIE_BOT_LLM_API_URL")
STEWIE_BOT_DISCORD_SEND_API_URL = os.getenv("STEWIE_BOT_DISCORD_SEND_API_URL")
STEWIE_BOT_INITIATE_API_URL = os.getenv("STEWIE_BOT_INITIATE_API_URL")

PETER_BOT_MENTION_STRING = os.getenv("PETER_BOT_MENTION_STRING")
BRIAN_BOT_MENTION_STRING = os.getenv("BRIAN_BOT_MENTION_STRING")
STEWIE_BOT_MENTION_STRING = os.getenv("STEWIE_BOT_MENTION_STRING")

# RAG Crawl specific environment variables
FANDOM_WIKI_START_URL = os.getenv("FANDOM_WIKI_START_URL", "https://familyguy.fandom.com/wiki/Main_Page")
FANDOM_WIKI_MAX_PAGES = os.getenv("FANDOM_WIKI_MAX_PAGES", "100")
FANDOM_WIKI_CRAWL_DELAY = os.getenv("FANDOM_WIKI_CRAWL_DELAY", "1")
DEFAULT_DISCORD_CHANNEL_ID = os.getenv("DEFAULT_DISCORD_CHANNEL_ID")


if not all([PETER_BOT_LLM_API_URL, PETER_BOT_DISCORD_SEND_API_URL, PETER_BOT_INITIATE_API_URL,
            BRIAN_BOT_LLM_API_URL, BRIAN_BOT_DISCORD_SEND_API_URL, BRIAN_BOT_INITIATE_API_URL,
            STEWIE_BOT_LLM_API_URL, STEWIE_BOT_DISCORD_SEND_API_URL, STEWIE_BOT_INITIATE_API_URL,
            PETER_BOT_MENTION_STRING, BRIAN_BOT_MENTION_STRING, STEWIE_BOT_MENTION_STRING,
            FANDOM_WIKI_START_URL, FANDOM_WIKI_MAX_PAGES, FANDOM_WIKI_CRAWL_DELAY,
            DEFAULT_DISCORD_CHANNEL_ID]):
    print("Error: One or more orchestrator API URLs, mention strings, RAG crawl settings, or DEFAULT_DISCORD_CHANNEL_ID not found in environment variables.")
    print("Please ensure all *_API_URL, *_MENTION_STRING, FANDOM_WIKI_*, and DEFAULT_DISCORD_CHANNEL_ID variables are set in your .env file.")
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
    ("user", "{initiator_bot_name}. Generate a conversation starter.")
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
    
    # Remove common AI prefixes (case-insensitive and with potential mentions)
    prefixes_to_remove = [
        "AI:", "Assistant:", "Bot:",
        "AI: @Peter Griffin:", "AI: @Brian Griffin:", "AI: @Stewie Griffin:",
        "Assistant: @Peter Griffin:", "Assistant: @Brian Griffin:", "Assistant: @Stewie Griffin:",
        "Bot: @Peter Griffin:", "Bot: @Brian Griffin:", "Bot: @Stewie Griffin:",
        "Peter:", "Brian:", "Stewie:", # Character names as prefixes
        "Peter: @Brian Griffin:", "Brian: @Peter Griffin:", "Stewie: @Brian Griffin:",
        "Peter: @Stewie Griffin:", "Stewie: @Peter Griffin:", "Brian: @Stewie Griffin:"
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

# --- RAG Components ---
vectorstore = None
embeddings = None
CHROMA_DB_PATH = "./chroma_db" # Path to store Chroma DB

def get_embeddings_model():
    """Initializes and returns the SentenceTransformer embeddings model."""
    global embeddings
    if embeddings is None:
        try:
            embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
            print("SentenceTransformerEmbeddings model loaded successfully.")
        except Exception as e:
            print(f"Error loading SentenceTransformerEmbeddings model: {e}")
            print("Please ensure 'sentence-transformers' is installed and the model can be downloaded.")
            os._exit(1)
    return embeddings

def initialize_vector_store():
    """Initializes or loads the Chroma vector store."""
    global vectorstore
    try:
        # Attempt to load existing vector store
        vectorstore = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=get_embeddings_model())
        # Check if it's empty
        if vectorstore._collection.count() == 0:
            print("Chroma DB initialized but is empty. Please load documents.")
        else:
            print(f"Chroma DB loaded from {CHROMA_DB_PATH} with {vectorstore._collection.count()} documents.")
    except Exception as e:
        print(f"Error initializing or loading Chroma DB: {e}")
        print("Creating a new Chroma DB.")
        vectorstore = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=get_embeddings_model())
        vectorstore.persist() # Ensure persistence
    return vectorstore

def load_documents_from_url(url):
    """
    Scrapes text content from a given URL and extracts internal links.
    Returns (text_content, internal_links).
    """
    print(f"Attempting to scrape content from: {url}")
    text = None
    internal_links = []
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        content_div = soup.find('div', class_='mw-parser-output') or \
                      soup.find('div', id='content') or \
                      soup.find('main', id='main-content')
        
        if content_div:
            text = content_div.get_text(separator='\n', strip=True)
            text = os.linesep.join([s for s in text.splitlines() if s])
        else:
            print(f"Could not find main content div on {url}. Scraped raw text.")
            text = soup.get_text(separator='\n', strip=True)
            text = os.linesep.join([s for s in text.splitlines() if s])

        # Extract internal links
        base_netloc = urlparse(url).netloc
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(url, href)
            parsed_full_url = urlparse(full_url)

            # Only consider HTTP/HTTPS links, within the same domain, and not pointing to files
            if parsed_full_url.scheme in ['http', 'https'] and \
               parsed_full_url.netloc == base_netloc and \
               not any(parsed_full_url.path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.zip', '.mp4', '.avi', '.mov']):
                internal_links.append(full_url)
        
        print(f"Successfully scraped {len(text) if text else 0} characters and found {len(internal_links)} internal links from {url}.")
        return text, internal_links

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None, []
    except Exception as e:
        print(f"Error parsing content from {url}: {e}")
        print(traceback.format_exc())
        return None, []

def crawl_and_process_documents(start_url, max_pages_to_crawl, delay_between_requests):
    """
    Crawls a website, extracts text, splits it, and stores it in the vector store.
    """
    if vectorstore is None:
        print("Vector store not initialized. Cannot crawl.")
        return False

    print(f"Starting crawl from {start_url} (max {max_pages_to_crawl} pages, {delay_between_requests}s delay)...")
    
    # Clear existing documents in Chroma DB before starting a new crawl
    try:
        if vectorstore._collection.count() > 0:
            print("Clearing existing documents in Chroma DB before starting new crawl.")
            # Fix: Use get() to retrieve all IDs and then delete by IDs
            all_ids = vectorstore.get(ids=[])['ids']
            if all_ids:
                vectorstore.delete(ids=all_ids)
            vectorstore.persist()
            print(f"Successfully cleared {len(all_ids)} documents from Chroma DB.")
    except Exception as e:
        print(f"Error clearing Chroma DB: {e}. Proceeding with crawl, but duplicates might occur.")
        print(traceback.format_exc()) # Corrected traceback call

    queue = deque([start_url])
    visited_urls = set()
    pages_crawled = 0
    base_netloc = urlparse(start_url).netloc

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        add_start_index=True,
    )

    while queue and pages_crawled < max_pages_to_crawl:
        current_url = queue.popleft()

        if current_url in visited_urls:
            continue

        print(f"Crawling: {current_url} ({pages_crawled + 1}/{max_pages_to_crawl})")
        visited_urls.add(current_url)
        
        text_content, links = load_documents_from_url(current_url)
        
        if text_content:
            texts = text_splitter.create_documents([text_content])
            if texts:
                try:
                    vectorstore.add_documents(texts)
                    vectorstore.persist()
                    print(f"  -> Added {len(texts)} chunks to Chroma DB.")
                    pages_crawled += 1
                except Exception as e:
                    print(f"  -> Error adding chunks for {current_url} to Chroma DB: {e}")
                    print(traceback.format_exc())
            else:
                print(f"  -> No chunks generated for {current_url}.")
        else:
            print(f"  -> No content scraped from {current_url}.")

        for link in links:
            parsed_link = urlparse(link)
            if parsed_link.netloc == base_netloc and link not in visited_urls:
                queue.append(link)
        
        time.sleep(delay_between_requests) # Respectful delay

    print(f"Crawl finished. Total pages crawled: {pages_crawled}. Total documents in Chroma DB: {vectorstore._collection.count()}.")
    return True

@app.route('/load_fandom_wiki', methods=['POST'])
def load_fandom_wiki_endpoint():
    """
    Flask endpoint to trigger the loading and processing of the Family Guy Fandom Wiki.
    Now initiates a crawl.
    """
    data = request.json
    start_url = data.get("url", FANDOM_WIKI_START_URL)
    max_pages = data.get("max_pages", int(FANDOM_WIKI_MAX_PAGES))
    delay = data.get("delay", int(FANDOM_WIKI_CRAWL_DELAY))

    # Run the processing in a separate thread to avoid blocking the Flask request
    def run_processing():
        with app.app_context():
            success = crawl_and_process_documents(start_url, max_pages_to_crawl=max_pages, delay_between_requests=delay)
            if success:
                print(f"RAG document crawling for {start_url} completed successfully.")
            else:
                print(f"RAG document crawling for {start_url} failed.")

    threading.Thread(target=run_processing).start()
    
    return jsonify({"status": f"Started crawling and processing documents from {start_url}. Max pages: {max_pages}, Delay: {delay}s. Check server logs for progress."}), 202


def retrieve_context(query, num_results=3):
    """
    Retrieves relevant context from the vector store based on a query.
    """
    if vectorstore is None or vectorstore._collection.count() == 0:
        print("Vector store is not initialized or is empty. Cannot retrieve context.")
        return ""
    
    try:
        docs_with_scores = vectorstore.similarity_search_with_score(query, k=num_results)
        
        context = "\n\n".join([doc.page_content for doc, score in docs_with_scores])
        if context:
            print(f"Retrieved context for query '{query[:50]}...': {context[:100]}...")
        else:
            print(f"No relevant context found for query: '{query[:50]}...'")
        return context
    except Exception as e:
        print(f"Error retrieving context from vector store: {e}")
        print(traceback.format_exc())
        return ""


@app.route('/orchestrate', methods=['POST'])
def orchestrate_conversation():
    """
    Main endpoint for the orchestrator.
    Receives the user's message and channel ID from Peter, Brian, or Stewie's bot.
    Manages the continuous conversation flow between all three characters.
    Includes RAG context retrieval.
    """
    data = request.json
    if not data:
        print("Error: No JSON data received in /orchestrate")
        return jsonify({"error": "No JSON data received"}), 400

    user_query = data.get("user_query")
    channel_id = str(data.get("channel_id"))
    initiator_bot_name = data.get("initiator_bot_name")
    initiator_mention = data.get("initiator_mention")
    human_user_display_name = data.get("human_user_display_name", None)
    conversation_session_id = data.get("conversation_session_id", None)
    is_new_conversation = data.get("is_new_conversation", False)

    if not all([user_query, channel_id, initiator_bot_name, initiator_mention]):
        print(f"Error: Missing required data in /orchestrate payload. Received: {data}")
        return jsonify({"error": "Missing required data (user_query, channel_id, initiator_bot_name, initiator_mention)"}), 400

    print(f"Orchestrator received request from {initiator_bot_name} for user query: '{user_query}' in channel {channel_id}")

    if initiator_bot_name not in BOT_CONFIGS:
        print(f"Error: Unknown initiator bot: {initiator_bot_name}")
        return jsonify({"error": f"Unknown initiator bot: {initiator_bot_name}"}), 400

    try:
        active_conversation_session_id = None
        conversation_history_for_llm = []
        current_turn = 0

        if is_new_conversation and conversation_session_id:
            active_conversation_session_id = conversation_session_id
            print(f"Orchestrator: Initiating new scheduled conversation with session ID: {active_conversation_session_id}")
        else:
            latest_message_in_channel = conversations_collection.find_one(
                {"channel_id": channel_id},
                sort=[("timestamp", -1)]
            )
            if latest_message_in_channel and "conversation_session_id" in latest_message_in_channel:
                active_conversation_session_id = latest_message_in_channel["conversation_session_id"]
                print(f"Orchestrator: Resuming conversation with session ID: {active_conversation_session_id}")
                all_channel_history_for_session = list(conversations_collection.find({"channel_id": channel_id, "conversation_session_id": active_conversation_session_id}).sort("timestamp", 1))
                for msg_doc in all_channel_history_for_session:
                    if msg_doc["role"] == "user":
                        conversation_history_for_llm.append(HumanMessage(content=msg_doc["content"]))
                    elif msg_doc["role"] == "assistant":
                        conversation_history_for_llm.append(AIMessage(content=msg_doc["content"], name=msg_doc.get("name")))
                current_turn = len(conversation_history_for_llm) // 2
            else:
                active_conversation_session_id = str(uuid.uuid4())
                print(f"Orchestrator: No active session found. Starting new human-initiated conversation with session ID: {active_conversation_session_id}")

        current_timestamp = datetime.now()
        user_message_doc = {
            "conversation_session_id": active_conversation_session_id,
            "channel_id": channel_id,
            "role": "user",
            "content": user_query,
            "display_name": human_user_display_name,
            "timestamp": current_timestamp
        }
        conversations_collection.insert_one(user_message_doc)
        conversation_history_for_llm.append(HumanMessage(content=user_query))

    except PyMongoError as e:
        print(f"MongoDB error during history retrieval/save: {e}")
        print(traceback.format_exc())
        return jsonify({"error": "Failed to access conversation history"}), 500

    conversation_ended = False

    try:
        # --- RAG: Retrieve context for the current user query ---
        # The context will be passed to the individual bots' LLMs
        retrieved_context = retrieve_context(user_query)

        # --- Conversation Loop ---
        while not conversation_ended and current_turn < MAX_CONVERSATION_TURNS:
            current_turn += 1
            print(f"\n--- Turn {current_turn} ---")

            next_speaker_name = None

            if conversation_history_for_llm:
                last_message_llm = conversation_history_for_llm[-1]
                last_message_content = last_message_llm.content
                last_speaker_role = last_message_llm.type
                last_speaker_name_in_history = last_message_llm.name if hasattr(last_message_llm, 'name') else None

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
                print(f"No history found. Picking initiator bot: {next_speaker_name}")


            current_speaker_name = next_speaker_name
            current_speaker_config = BOT_CONFIGS[current_speaker_name]
            current_speaker_mention = current_speaker_config["mention"]

            print(f"Current speaker: {current_speaker_name}")

            serializable_history = []
            for msg in conversation_history_for_llm:
                if isinstance(msg, HumanMessage):
                    serializable_history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    serializable_history.append({"role": "assistant", "content": msg.content, "name": msg.name})

            # Prepare payload for the current speaker's LLM
            llm_payload = {
                "conversation_history": serializable_history,
                "current_speaker_name": current_speaker_name,
                "current_speaker_mention": current_speaker_mention,
                "all_bot_mentions": {name: config["mention"] for name, config in BOT_CONFIGS.items()},
                "human_user_display_name": human_user_display_name,
                "conversation_session_id": active_conversation_session_id,
                "retrieved_context": retrieved_context # Pass the retrieved context to the bot
            }

            print(f"Orchestrator requesting {current_speaker_name}'s LLM response from {current_speaker_config['llm_api']}...")
            llm_res = requests.post(current_speaker_config["llm_api"], json=llm_payload, timeout=60)
            llm_res.raise_for_status()
            response_text = llm_res.json().get("response_text", f"{current_speaker_name} is silent.")
            print(f"{current_speaker_name}'s LLM raw generated: {response_text[:50]}...")

            response_text = clean_llm_response(response_text)
            print(f"{current_speaker_name}'s LLM cleaned response: {response_text[:50]}...")

            bot_message_doc = {
                "conversation_session_id": active_conversation_session_id,
                "channel_id": channel_id,
                "role": "assistant",
                "name": current_speaker_name.lower(),
                "content": response_text,
                "timestamp": datetime.now()
            }
            conversations_collection.insert_one(bot_message_doc)
            conversation_history_for_llm.append(AIMessage(content=response_text, name=current_speaker_name.lower()))

            print(f"Orchestrator instructing {current_speaker_name} to send to Discord via {current_speaker_config['discord_send_api']}...")
            discord_payload = {
                "message_content": response_text,
                "channel_id": channel_id,
                "conversation_session_id": active_conversation_session_id
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

        return jsonify({"status": "Conversation orchestrated successfully", "turns": current_turn, "conversation_session_id": active_conversation_session_id}), 200

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

# Global to track last crawl time
last_crawl_timestamp = None

def schedule_daily_conversations():
    """
    Schedules and initiates random conversations throughout the day, and triggers a daily RAG crawl.
    This function runs in a separate thread.
    """
    global last_crawl_timestamp
    # Explicitly declare global variables used from the module scope
    global FANDOM_WIKI_START_URL, FANDOM_WIKI_MAX_PAGES, FANDOM_WIKI_CRAWL_DELAY, DEFAULT_DISCORD_CHANNEL_ID, ORCHESTRATOR_API_URL, BOT_CONFIGS, INITIAL_CONVERSATION_PROMPTS, starter_generation_chain, conversations_collection

    print(f"Scheduler: Starting daily conversation scheduling thread. Will initiate {NUM_DAILY_RANDOM_CONVERSATIONS} conversations per day and a daily RAG crawl.")
    
    # Define crawl parameters from environment variables
    start_url = FANDOM_WIKI_START_URL
    max_pages = int(FANDOM_WIKI_MAX_PAGES)
    delay = int(FANDOM_WIKI_CRAWL_DELAY)

    while True:
        now = datetime.now()

        # Check if a crawl is needed for the current calendar day
        if last_crawl_timestamp is None or last_crawl_timestamp.date() < now.date():
            print(f"Scheduler: Initiating daily RAG crawl for {now.date()} at {now.strftime('%H:%M:%S')}")
            crawl_thread = threading.Thread(target=crawl_and_process_documents, args=(start_url, max_pages, delay), daemon=True)
            crawl_thread.start()
            crawl_thread.join() # Wait for the crawl to complete
            last_crawl_timestamp = now
            print(f"Scheduler: RAG crawl completed. Initiating first conversation of the day.")

            # Initiate the very first conversation immediately after crawl
            initiator_bot_name = random.choice(list(BOT_CONFIGS.keys()))
            initiator_bot_config = BOT_CONFIGS[initiator_bot_name]
            initiator_api_url = initiator_bot_config["initiate_api"]
            
            conversation_starter_prompt = ""
            if not DEFAULT_DISCORD_CHANNEL_ID:
                print("ERROR: DEFAULT_DISCORD_CHANNEL_ID not found in .env. Cannot initiate random conversation.")
            else:
                try:
                    recent_history = []
                    try:
                        all_channel_messages = list(conversations_collection.find({"channel_id": DEFAULT_DISCORD_CHANNEL_ID}).sort("timestamp", -1).limit(5))
                        recent_history_raw = list(reversed(all_channel_messages))
                        for msg_doc in recent_history_raw:
                            if msg_doc["role"] == "user":
                                recent_history.append(HumanMessage(content=msg_doc["content"]))
                            elif msg_doc["role"] == "assistant":
                                recent_history.append(AIMessage(content=msg_doc["content"], name=msg_doc.get("name")))
                    except PyMongoError as e:
                        print(f"MongoDB error fetching recent history for dynamic prompt: {e}")
                        print(traceback.format_exc())

                    print(f"Scheduler: Generating dynamic conversation starter for first conversation using orchestrator's LLM...")
                    generated_starter = starter_generation_chain.invoke({
                        "recent_history": recent_history,
                        "initiator_bot_name": initiator_bot_name
                    }).strip()

                    if generated_starter:
                        conversation_starter_prompt = clean_llm_response(generated_starter)
                        print(f"Scheduler: Generated dynamic starter: '{conversation_starter_prompt[:50]}...'")
                    else:
                        conversation_starter_prompt = random.choice(INITIAL_CONVERSATION_PROMPTS)
                        print(f"Scheduler: No dynamic starter generated. Falling back to static prompt: '{conversation_starter_prompt[:50]}...'")

                except Exception as e:
                    print(f"ERROR: Scheduler: Unexpected error generating dynamic starter for first conversation with orchestrator's LLM: {e}. Falling back to static prompt.")
                    print(traceback.format_exc())
                    conversation_starter_prompt = random.choice(INITIAL_CONVERSATION_PROMPTS)

                print(f"Scheduler: Initiating FIRST conversation via {initiator_bot_name} at {datetime.now().strftime('%H:%M:%S')}")
                try:
                    new_session_id = str(uuid.uuid4())
                    initiate_payload = {
                        "user_query": conversation_starter_prompt, # The starter acts as the initial "user query" from the bot
                        "channel_id": DEFAULT_DISCORD_CHANNEL_ID,
                        "initiator_bot_name": initiator_bot_name,
                        "initiator_mention": initiator_bot_config["mention"],
                        "human_user_display_name": None,
                        "is_new_conversation": True,
                        "conversation_session_id": new_session_id
                    }
                    requests.post(ORCHESTRATOR_API_URL, json=initiate_payload, timeout=60)
                    print(f"Scheduler: Successfully sent initiation request for FIRST conversation to orchestrator for session {new_session_id}.")
                except requests.exceptions.Timeout:
                    print(f"ERROR: Scheduler Timeout: Failed to initiate FIRST conversation with orchestrator. API call timed out.")
                except requests.exceptions.ConnectionError:
                    print(f"ERROR: Scheduler Connection Error: Failed to initiate FIRST conversation with orchestrator. Orchestrator API might be down.")
                except Exception as e:
                    print(f"ERROR: Scheduler: Unexpected error initiating FIRST conversation with orchestrator: {e}")
                    print(traceback.format_exc())
            
            # After the first conversation, schedule the remaining ones
            num_remaining_conversations = NUM_DAILY_RANDOM_CONVERSATIONS - 1
            start_scheduling_from = datetime.now() # Start scheduling remaining from now
        else:
            print(f"Scheduler: RAG crawl already performed for {now.date()}. Skipping crawl.")
            num_remaining_conversations = NUM_DAILY_RANDOM_CONVERSATIONS # All conversations are "remaining"
            start_scheduling_from = now # Start scheduling from now

        # Calculate scheduled times for remaining random conversations for the current 24-hour cycle
        scheduled_times_for_conversations = []
        if num_remaining_conversations > 0:
            # Distribute remaining conversations over the time until next midnight
            time_until_next_day_start_for_scheduling = (datetime(now.year, now.month, now.day, 0, 0, 0) + timedelta(days=1) - start_scheduling_from).total_seconds()
            if time_until_next_day_start_for_scheduling < 0: # If we are already past midnight for scheduling
                time_until_next_day_start_for_scheduling += 24 * 3600 # Target next midnight

            if time_until_next_day_start_for_scheduling > 0:
                interval_seconds = time_until_next_day_start_for_scheduling / num_remaining_conversations
                for i in range(num_remaining_conversations):
                    scheduled_time = start_scheduling_from + timedelta(seconds=(i + 1) * interval_seconds)
                    scheduled_times_for_conversations.append(scheduled_time)
            
            scheduled_times_for_conversations.sort() # Ensure chronological order

            print(f"Scheduler: Next {len(scheduled_times_for_conversations)} conversation times scheduled for this cycle:")
            for t in scheduled_times_for_conversations:
                print(f"  - {t.strftime('%Y-%m-%d %H:%M:%S')}")

            # Execute scheduled conversations
            for scheduled_time in scheduled_times_for_conversations:
                time_to_wait = (scheduled_time - datetime.now()).total_seconds()
                if time_to_wait > 0:
                    time.sleep(time_to_wait)
                
                # Only initiate conversation if it's not too late in the cycle
                if (datetime.now() - now).total_seconds() < (24 * 3600):
                    initiator_bot_name = random.choice(list(BOT_CONFIGS.keys()))
                    initiator_bot_config = BOT_CONFIGS[initiator_bot_name]
                    initiator_api_url = initiator_bot_config["initiate_api"]
                    
                    conversation_starter_prompt = ""
                    if not DEFAULT_DISCORD_CHANNEL_ID:
                        print("ERROR: DEFAULT_DISCORD_CHANNEL_ID not found in .env. Cannot initiate random conversation.")
                        continue

                    try:
                        recent_history = []
                        try:
                            all_channel_messages = list(conversations_collection.find({"channel_id": DEFAULT_DISCORD_CHANNEL_ID}).sort("timestamp", -1).limit(5))
                            recent_history_raw = list(reversed(all_channel_messages))
                            for msg_doc in recent_history_raw:
                                if msg_doc["role"] == "user":
                                    recent_history.append(HumanMessage(content=msg_doc["content"]))
                                elif msg_doc["role"] == "assistant":
                                    recent_history.append(AIMessage(content=msg_doc["content"], name=msg_doc.get("name")))
                        except PyMongoError as e:
                            print(f"MongoDB error fetching recent history for dynamic prompt: {e}")
                            print(traceback.format_exc())

                        print(f"Scheduler: Generating dynamic conversation starter using orchestrator's LLM...")
                        generated_starter = starter_generation_chain.invoke({
                            "recent_history": recent_history,
                            "initiator_bot_name": initiator_bot_name
                        }).strip()

                        if generated_starter:
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
                        new_session_id = str(uuid.uuid4())
                        initiate_payload = {
                            "user_query": conversation_starter_prompt, # The starter acts as the initial "user query" from the bot
                            "channel_id": DEFAULT_DISCORD_CHANNEL_ID,
                            "initiator_bot_name": initiator_bot_name,
                            "initiator_mention": initiator_bot_config["mention"],
                            "human_user_display_name": None,
                            "is_new_conversation": True,
                            "conversation_session_id": new_session_id
                        }
                        requests.post(ORCHESTRATOR_API_URL, json=initiate_payload, timeout=60)
                        print(f"Scheduler: Successfully sent initiation request to orchestrator for session {new_session_id}.")
                    except requests.exceptions.Timeout:
                        print(f"ERROR: Scheduler Timeout: Failed to initiate conversation with orchestrator. API call timed out.")
                    except requests.exceptions.ConnectionError:
                        print(f"ERROR: Scheduler Connection Error: Failed to initiate conversation with orchestrator. Orchestrator API might be down.")
                    except Exception as e:
                        print(f"ERROR: Scheduler: Unexpected error initiating conversation with orchestrator: {e}")
                        print(traceback.format_exc())
                else:
                    print("Scheduler: Skipping conversation initiation as it's too late in the current 24-hour cycle.")

        # Sleep until the start of the next calendar day to reset the cycle and re-check for crawl
        next_day = now + timedelta(days=1)
        target_time = datetime(next_day.year, next_day.month, next_day.day, 0, 0, 0)
        time_until_next_day_start = (target_time - datetime.now()).total_seconds()
        
        if time_until_next_day_start < 0:
            time_until_next_day_start += 24 * 3600

        print(f"Scheduler: All events for this cycle processed. Waiting {time_until_next_day_start:.0f} seconds until the start of the next day for a new schedule and crawl check.")
        time.sleep(time_until_next_day_start)


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
    get_embeddings_model() # Initialize embeddings model on startup
    initialize_vector_store() # Initialize or load vector store on startup
    
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

