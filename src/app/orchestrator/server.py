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
import hashlib

print("Starting imports...")

# Dead Letter Queue Configuration
DLQ_COLLECTION_NAME = "dead_letter_queue"
MAX_RETRY_ATTEMPTS = int(os.getenv("DLQ_MAX_RETRY_ATTEMPTS", "3"))
RETRY_DELAY_BASE = float(os.getenv("DLQ_RETRY_DELAY_BASE", "2.0"))  # Base for exponential backoff
MAX_RETRY_DELAY = int(os.getenv("DLQ_MAX_RETRY_DELAY", "300"))  # Maximum delay between retries in seconds
RETRY_WORKER_INTERVAL = int(os.getenv("DLQ_RETRY_WORKER_INTERVAL", "60"))  # How often to check for retryable messages

# Supervised Fine-Tuning System Configuration
FINE_TUNING_ENABLED = os.getenv("FINE_TUNING_ENABLED", "true").lower() == "true"
OPTIMIZATION_THRESHOLD = float(os.getenv("OPTIMIZATION_THRESHOLD", "0.7"))  # Trigger optimization when avg rating < 0.7
MIN_RATINGS_FOR_OPTIMIZATION = int(os.getenv("MIN_RATINGS_FOR_OPTIMIZATION", "10"))
AB_TEST_PERCENTAGE = float(os.getenv("AB_TEST_PERCENTAGE", "0.2"))  # 20% traffic for A/B testing

# Quality Control Configuration (Optimized for performance)
QUALITY_CONTROL_ENABLED = os.getenv("QUALITY_CONTROL_ENABLED", "true").lower() == "true"
QUALITY_CONTROL_MIN_RATING = float(os.getenv("QUALITY_CONTROL_MIN_RATING", "3.0"))  # Minimum acceptable rating (raised to prevent mixed conversations)
QUALITY_CONTROL_MAX_RETRIES = int(os.getenv("QUALITY_CONTROL_MAX_RETRIES", "2"))  # Max retries for quality (reduced for performance)

# Add a global variable to track recent responses
recent_responses_cache = {}
DUPLICATE_CACHE_SIZE = 50  # Keep last 50 responses per character
DUPLICATE_SIMILARITY_THRESHOLD = 0.8  # 80% similarity threshold

def is_duplicate_response(character_name, response_text, conversation_history):
    """
    Check if the response is too similar to recent responses from the same character.
    Returns True if it's a duplicate, False otherwise.
    """
    try:
        if character_name not in recent_responses_cache:
            recent_responses_cache[character_name] = []
        
        # Clean the response for comparison
        cleaned_response = response_text.lower().strip()
        
        # Check against recent responses from this character
        for recent_response in recent_responses_cache[character_name]:
            # Simple similarity check - could be improved with more sophisticated methods
            if len(cleaned_response) > 0 and len(recent_response) > 0:
                # Calculate similarity based on character overlap
                shorter = min(len(cleaned_response), len(recent_response))
                longer = max(len(cleaned_response), len(recent_response))
                
                if shorter > 0:
                    # If responses are very similar length and content
                    if abs(len(cleaned_response) - len(recent_response)) < 10:
                        common_chars = sum(1 for a, b in zip(cleaned_response, recent_response) if a == b)
                        similarity = common_chars / longer
                        
                        if similarity > DUPLICATE_SIMILARITY_THRESHOLD:
                            print(f"🔄 Duplicate detected for {character_name}: {similarity:.2f} similarity")
                            return True
                
                # Also check for exact substring matches (common with the golf repetition)
                if len(cleaned_response) > 50 and cleaned_response in recent_response:
                    print(f"🔄 Exact substring duplicate detected for {character_name}")
                    return True
                if len(recent_response) > 50 and recent_response in cleaned_response:
                    print(f"🔄 Exact substring duplicate detected for {character_name}")
                    return True
        
        # Add this response to the cache
        recent_responses_cache[character_name].append(cleaned_response)
        
        # Keep cache size manageable
        if len(recent_responses_cache[character_name]) > DUPLICATE_CACHE_SIZE:
            recent_responses_cache[character_name].pop(0)
        
        return False
        
    except Exception as e:
        print(f"⚠️ Error in duplicate detection: {e}")
        return False

class PromptFineTuner:
    """
    Supervised Fine-Tuning System for Character Prompts
    
    Automatically improves character accuracy through:
    - LLM-based auto-assessment of every response
    - Quality control with pre-send filtering
    - Automatic prompt optimization based on feedback
    - A/B testing for safe deployment of improvements
    """
    
    def __init__(self, mongo_client):
        """Initialize the fine-tuning system with MongoDB collections."""
        self.mongo_client = mongo_client
        self.db = mongo_client[os.getenv("MONGO_DB_NAME", "discord_bot_conversations")]
        
        # MongoDB Collections
        self.ratings_collection = self.db["response_ratings"]
        self.prompt_versions_collection = self.db["prompt_versions"]
        self.performance_metrics_collection = self.db["performance_metrics"]
        
        # Create indexes for better performance
        try:
            self.ratings_collection.create_index([("character_name", 1), ("timestamp", -1)])
            self.ratings_collection.create_index([("rating", 1)])
            self.prompt_versions_collection.create_index([("character_name", 1), ("version", -1)])
            self.performance_metrics_collection.create_index([("character_name", 1), ("date", -1)])
            print("📋 Fine-tuning database indexes created successfully")
        except Exception as e:
            print(f"⚠️ Warning: Could not create fine-tuning indexes: {e}")
    
    def record_rating(self, character_name, response_text, rating, feedback="", user_id="system", conversation_context=""):
        """
        Record a quality rating for a character response.
        
        Args:
            character_name: The character being rated
            response_text: The response that was rated
            rating: Quality rating 1-5
            feedback: Optional feedback text
            user_id: ID of the rater (e.g., "llm_auto_assessment")
            conversation_context: Context of the conversation
            
        Returns:
            ObjectId of the inserted rating or None if failed
        """
        try:
            rating_doc = {
                "character_name": character_name,
                "response_text": response_text,
                "rating": rating,
                "feedback": feedback,
                "user_id": user_id,
                "conversation_context": conversation_context,
                "timestamp": datetime.now(),
                "prompt_version": self.get_current_prompt_version(character_name)
            }
            
            result = self.ratings_collection.insert_one(rating_doc)
            
            # Update performance metrics
            self._update_performance_metrics(character_name, rating)
            
            # Check if optimization is needed
            if FINE_TUNING_ENABLED and self._should_optimize(character_name):
                self._trigger_background_optimization(character_name)
            
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"⚠️ Error recording rating: {e}")
            return None
    
    def get_optimized_prompt(self, character_name):
        """
        Get the current optimized prompt for a character, if available.
        Implements A/B testing logic.
        
        Returns:
            Optimized prompt text or None if using default
        """
        try:
            # Check if we're A/B testing and this request should use optimized prompt
            if random.random() < AB_TEST_PERCENTAGE:
                latest_version = self.prompt_versions_collection.find_one(
                    {"character_name": character_name, "is_active": True},
                    sort=[("version", -1)]
                )
                
                if latest_version and latest_version.get("optimized_prompt"):
                    return latest_version["optimized_prompt"]
            
            return None  # Use default prompt
            
        except Exception as e:
            print(f"⚠️ Error getting optimized prompt: {e}")
            return None
    
    def get_current_prompt_version(self, character_name):
        """Get the current prompt version number for a character."""
        try:
            latest = self.prompt_versions_collection.find_one(
                {"character_name": character_name},
                sort=[("version", -1)]
            )
            return latest["version"] if latest else 1
        except Exception as e:
            print(f"⚠️ Error getting prompt version: {e}")
            return 1
    
    def get_performance_report(self, character_name, days=7):
        """
        Get performance report for a character over specified period.
        
        Args:
            character_name: Character to report on
            days: Number of days to look back
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Get ratings from the period
            ratings = list(self.ratings_collection.find({
                "character_name": character_name,
                "timestamp": {"$gte": cutoff_date}
            }))
            
            if not ratings:
                return {
                    "character": character_name,
                    "period_days": days,
                    "total_ratings": 0,
                    "average_rating": None,
                    "rating_distribution": {},
                    "recent_feedback": [],
                    "optimization_needed": False
                }
            
            # Calculate metrics
            total_ratings = len(ratings)
            average_rating = sum(r["rating"] for r in ratings) / total_ratings
            
            # Rating distribution
            distribution = {}
            for i in range(1, 6):
                count = sum(1 for r in ratings if r["rating"] == i)
                distribution[f"{i}_stars"] = count
            
            # Recent feedback (last 5)
            recent_feedback = []
            for rating in sorted(ratings, key=lambda x: x["timestamp"], reverse=True)[:5]:
                if rating.get("feedback"):
                    recent_feedback.append({
                        "rating": rating["rating"],
                        "feedback": rating["feedback"][:200],  # Truncate long feedback
                        "timestamp": rating["timestamp"].isoformat(),
                        "user_id": rating.get("user_id", "unknown")
                    })
            
            return {
                "character": character_name,
                "period_days": days,
                "total_ratings": total_ratings,
                "average_rating": round(average_rating, 2),
                "rating_distribution": distribution,
                "recent_feedback": recent_feedback,
                "optimization_needed": average_rating < OPTIMIZATION_THRESHOLD
            }
            
        except Exception as e:
            print(f"⚠️ Error generating performance report: {e}")
            return {"error": str(e)}
    
    def optimize_prompt(self, character_name, recent_ratings=None):
        """
        Optimize character prompt based on feedback and ratings.
        
        Args:
            character_name: Character to optimize
            recent_ratings: List of recent ratings, or None to fetch automatically
            
        Returns:
            Boolean indicating success
        """
        try:
            if not recent_ratings:
                # Get recent ratings for analysis
                recent_ratings = list(self.ratings_collection.find(
                    {"character_name": character_name},
                    sort=[("timestamp", -1)],
                    limit=MIN_RATINGS_FOR_OPTIMIZATION * 2
                ))
            
            if len(recent_ratings) < MIN_RATINGS_FOR_OPTIMIZATION:
                print(f"⚠️ Not enough ratings for optimization: {len(recent_ratings)}")
                return False
            
            # Analyze feedback patterns
            positive_feedback = []
            negative_feedback = []
            
            for rating in recent_ratings:
                feedback = rating.get("feedback", "")
                if rating["rating"] >= 4:
                    positive_feedback.append(feedback)
                elif rating["rating"] <= 2:
                    negative_feedback.append(feedback)
            
            # Generate optimized prompt using LLM
            optimized_prompt = self._generate_optimized_prompt(
                character_name, positive_feedback, negative_feedback
            )
            
            if optimized_prompt:
                # Save new prompt version
                new_version = self.get_current_prompt_version(character_name) + 1
                
                version_doc = {
                    "character_name": character_name,
                    "version": new_version,
                    "optimized_prompt": optimized_prompt,
                    "created_at": datetime.now(),
                    "is_active": True,
                    "based_on_ratings": len(recent_ratings),
                    "average_rating_before": sum(r["rating"] for r in recent_ratings) / len(recent_ratings)
                }
                
                self.prompt_versions_collection.insert_one(version_doc)
                print(f"✅ Created optimized prompt version {new_version} for {character_name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Error optimizing prompt: {e}")
            return False
    
    def _generate_optimized_prompt(self, character_name, positive_feedback, negative_feedback):
        """Generate an optimized prompt using LLM analysis of feedback."""
        try:
            # Get current character description for reference
            try:
                current_description = get_character_description(character_name)
            except NameError:
                # Fallback if function not available yet
                current_description = f"Character: {character_name} from Family Guy"
            
            # Create optimization prompt
            optimization_prompt = f"""You are a character prompt optimization expert. Your task is to improve a character prompt based on user feedback.

CHARACTER: {character_name} from Family Guy

CURRENT CHARACTER PROMPT:
{current_description}

POSITIVE FEEDBACK (what works well):
{chr(10).join(f"- {fb}" for fb in positive_feedback if fb)}

NEGATIVE FEEDBACK (what needs improvement):
{chr(10).join(f"- {fb}" for fb in negative_feedback if fb)}

OPTIMIZATION TASK:
1. Analyze the feedback to identify specific issues and strengths
2. Enhance the character prompt to address the negative feedback
3. Preserve and strengthen the elements mentioned in positive feedback
4. Maintain the character's core personality and speech patterns
5. Keep the same structure but improve clarity and specificity

REQUIREMENTS:
- Keep the same overall format and structure
- Enhance character-specific speech patterns and vocabulary
- Add more specific guidance for personality traits that were criticized
- Strengthen elements that received positive feedback
- Ensure the optimized prompt will generate more accurate character responses

Generate an improved character prompt that addresses the feedback while maintaining {character_name}'s authentic personality."""

            # Use shared LLM to generate optimization
            try:
                response = shared_llm.invoke(optimization_prompt)
                return clean_llm_response(response)
            except NameError:
                # Fallback if shared_llm not available yet
                print(f"⚠️ Shared LLM not available for optimization, using placeholder")
                return f"Optimized prompt for {character_name} based on feedback analysis (placeholder)"
            
        except Exception as e:
            print(f"⚠️ Error generating optimized prompt: {e}")
            return None
    
    def _should_optimize(self, character_name):
        """Check if character prompt should be optimized based on recent performance."""
        try:
            # Get recent ratings
            recent_ratings = list(self.ratings_collection.find(
                {"character_name": character_name},
                sort=[("timestamp", -1)],
                limit=MIN_RATINGS_FOR_OPTIMIZATION
            ))
            
            if len(recent_ratings) < MIN_RATINGS_FOR_OPTIMIZATION:
                return False
            
            average_rating = sum(r["rating"] for r in recent_ratings) / len(recent_ratings)
            return average_rating < OPTIMIZATION_THRESHOLD
            
        except Exception as e:
            print(f"⚠️ Error checking optimization need: {e}")
            return False
    
    def _trigger_background_optimization(self, character_name):
        """Trigger prompt optimization in background thread."""
        def optimize_in_background():
            try:
                print(f"🔧 Background optimization triggered for {character_name}")
                success = self.optimize_prompt(character_name)
                if success:
                    print(f"✅ Background optimization completed for {character_name}")
                else:
                    print(f"❌ Background optimization failed for {character_name}")
            except Exception as e:
                print(f"⚠️ Background optimization error: {e}")
        
        # Run optimization in background thread
        threading.Thread(target=optimize_in_background, daemon=True).start()
    
    def _update_performance_metrics(self, character_name, rating):
        """Update daily performance metrics."""
        try:
            # Ensure 'today' is a datetime object for MongoDB compatibility
            today_dt = datetime.now()
            today = datetime(today_dt.year, today_dt.month, today_dt.day) # Sets time to 00:00:00

            # Upsert daily metrics
            self.performance_metrics_collection.update_one(
                {"character_name": character_name, "date": today},
                {
                    "$inc": {
                        "total_ratings": 1,
                        "rating_sum": rating
                    },
                    "$push": {
                        "ratings": {
                            "$each": [rating],
                            "$slice": -100  # Keep last 100 ratings
                        }
                    }
                },
                upsert=True
            )
            
        except Exception as e:
            print(f"⚠️ Error updating performance metrics: {e}")

class MessageStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    FAILED = "failed"
    COMPLETED = "completed"
    DEAD_LETTERED = "dead_lettered"

class MessageType:
    LLM_REQUEST = "llm_request"
    DISCORD_MESSAGE = "discord_message"

class DeadLetterQueue:
    def __init__(self, collection):
        self.collection = collection

    def add_message(self, message_type, payload, error, bot_name=None):
        """Add a failed message to the dead letter queue."""
        doc = {
            "message_type": message_type,
            "payload": payload,
            "error": str(error),
            "bot_name": bot_name,
            "status": MessageStatus.PENDING,
            "retry_count": 0,
            "last_retry": None,
            "created_at": datetime.now(),
            "next_retry_at": datetime.now()  # Initially set to now for immediate retry
        }
        return self.collection.insert_one(doc)

    def get_retryable_messages(self):
        """Get messages that are ready for retry."""
        now = datetime.now()
        query = {
            "status": MessageStatus.PENDING,
            "retry_count": {"$lt": MAX_RETRY_ATTEMPTS},
            "next_retry_at": {"$lte": now}
        }
        return list(self.collection.find(query))

    def update_retry_status(self, message_id, success, error=None):
        """Update message status after a retry attempt."""
        now = datetime.now()
        message = self.collection.find_one({"_id": message_id})
        
        if not message:
            return
        
        if success:
            update = {
                "status": MessageStatus.COMPLETED,
                "completed_at": now,
                "error": None
            }
        else:
            retry_count = message["retry_count"] + 1
            if retry_count >= MAX_RETRY_ATTEMPTS:
                status = MessageStatus.DEAD_LETTERED
                next_retry = None
            else:
                status = MessageStatus.PENDING
                delay = min(RETRY_DELAY_BASE ** retry_count, MAX_RETRY_DELAY)
                next_retry = now + timedelta(seconds=delay)
            
            update = {
                "status": status,
                "retry_count": retry_count,
                "last_retry": now,
                "next_retry_at": next_retry,
                "error": str(error) if error else None
            }
        
        self.collection.update_one({"_id": message_id}, {"$set": update})

def retry_worker():
    """Background worker to process the dead letter queue."""
    global dlq
    
    while True:
        try:
            messages = dlq.get_retryable_messages()
            for message in messages:
                try:
                    print(f"Retrying message {message['_id']} (attempt {message['retry_count'] + 1}/{MAX_RETRY_ATTEMPTS})")
                    
                    if message["message_type"] == MessageType.LLM_REQUEST:
                        # Since we now use centralized LLM, we need to handle this differently
                        # For now, we'll skip retrying LLM requests as they're handled directly by the orchestrator
                        print(f"Skipping LLM request retry for message {message['_id']} - using centralized LLM approach")
                        dlq.update_retry_status(message["_id"], True)
                        
                    elif message["message_type"] == MessageType.DISCORD_MESSAGE:
                        bot_config = BOT_CONFIGS.get(message["bot_name"])
                        if not bot_config:
                            raise ValueError(f"Unknown bot: {message['bot_name']}")
                        
                        response = requests.post(
                            bot_config["discord_send_api"],
                            json=message["payload"],
                            timeout=API_TIMEOUT
                        )
                        response.raise_for_status()
                        dlq.update_retry_status(message["_id"], True)
                    
                except Exception as e:
                    print(f"Retry failed for message {message['_id']}: {str(e)}")
                    dlq.update_retry_status(message["_id"], False, error=e)
                
                time.sleep(1)  # Small delay between retries
                
        except Exception as e:
            print(f"Error in retry worker: {str(e)}")
            print(traceback.format_exc())
        
        time.sleep(RETRY_WORKER_INTERVAL)

# Note: SentenceTransformerEmbeddings and Chroma are no longer needed in the orchestrator
# since we now use the RAG Retriever microservice via HTTP API calls
print("All imports completed successfully")

# Load environment variables from a .env file
load_dotenv()

app = Flask(__name__)

# --- MongoDB Configuration ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:adminpassword@mongodb:27017/?authSource=admin")
DB_NAME = os.getenv("MONGO_DB_NAME", "discord_bot_conversations")
CONVERSATIONS_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "conversations")
CRAWL_STATUS_COLLECTION_NAME = "crawl_status" # New collection for tracking crawl status

mongo_client = None
db = None
conversations_collection = None
crawl_status_collection = None
dlq_collection = None
dlq = None
prompt_fine_tuner = None # Declare globally

def connect_to_mongodb(max_retries=5, initial_delay=1):
    """Establishes connection to MongoDB with retry mechanism."""
    global mongo_client, db, conversations_collection, crawl_status_collection, dlq_collection, dlq
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            if mongo_client:
                try:
                    mongo_client.close()
                except:
                    pass
            
            print(f"Attempting to connect to MongoDB (attempt {retry_count + 1}/{max_retries})...")
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            # Test the connection
            mongo_client.admin.command('ping')
            
            db = mongo_client[DB_NAME]
            conversations_collection = db[CONVERSATIONS_COLLECTION_NAME]
            crawl_status_collection = db[CRAWL_STATUS_COLLECTION_NAME]
            dlq_collection = db[DLQ_COLLECTION_NAME]
            
            # Initialize the Dead Letter Queue
            dlq = DeadLetterQueue(dlq_collection)
            
            # Create indexes for the DLQ collection
            dlq_collection.create_index([("status", 1), ("retry_count", 1), ("next_retry_at", 1)])
            dlq_collection.create_index([("created_at", 1)])
            dlq_collection.create_index([("message_type", 1)])
            
            print("Successfully connected to MongoDB and initialized collections!")
            return True
            
        except ConnectionFailure as e:
            retry_count += 1
            if retry_count == max_retries:
                print(f"MongoDB connection failed after {max_retries} attempts: {e}")
                print("Please ensure MongoDB is running and accessible at the specified URI.")
                return False
            
            wait_time = initial_delay * (2 ** (retry_count - 1))  # Exponential backoff
            print(f"Connection attempt failed. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            
        except Exception as e:
            print(f"An unexpected error occurred during MongoDB connection: {e}")
            print(traceback.format_exc())
            return False
    
    return False

# Attempt to connect to MongoDB at startup
if not connect_to_mongodb():
    print("CRITICAL: Orchestrator failed to connect to MongoDB. Some features might not work.")
    # Depending on how critical MongoDB is, you might exit:
    # import sys
    # sys.exit(1)
else:
    # Initialize PromptFineTuner only if MongoDB connection was successful and mongo_client is valid
    if mongo_client:
        prompt_fine_tuner = PromptFineTuner(mongo_client)
        print("PromptFineTuner initialized successfully.")
    else:
        print("CRITICAL: mongo_client is None even after connect_to_mongodb reported success. PromptFineTuner NOT initialized.")

# --- Orchestrator Configuration ---
ORCHESTRATOR_PORT = 5003
# Natural conversation flow - no hard limits, let conversations be organic
API_TIMEOUT = 120  # Increased timeout for API calls to 120 seconds
MAX_RETRIES = 3    # Number of retries for failed API calls
MAX_CHAT_HISTORY_MESSAGES = 10 # Max number of messages from current session to pass to LLM (reduced for performance)

# Organic conversation settings
CONVERSATION_SILENCE_THRESHOLD_MINUTES = int(os.getenv("CONVERSATION_SILENCE_THRESHOLD_MINUTES", "30"))  # Minutes of silence before considering starting a new conversation
MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS = int(os.getenv("MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS", "10"))  # Minimum minutes between organic conversation attempts

# Enhanced follow-up conversation settings
ENABLE_FOLLOW_UP_CONVERSATIONS = os.getenv("ENABLE_FOLLOW_UP_CONVERSATIONS", "true").lower() == "true"
FOLLOW_UP_DELAY_SECONDS = float(os.getenv("FOLLOW_UP_DELAY_SECONDS", "3.0"))  # Delay before checking for follow-ups
MIN_TIME_BETWEEN_FOLLOW_UPS = float(os.getenv("MIN_TIME_BETWEEN_FOLLOW_UPS", "30.0"))  # Minimum seconds between follow-up attempts

END_CONVERSATION_MARKER = "[END_CONVERSATION]"

# API URLs and Mention strings (from .env)
PETER_DISCORD_URL = os.getenv("PETER_DISCORD_URL", "http://peter-discord:5011/send_message")
BRIAN_DISCORD_URL = os.getenv("BRIAN_DISCORD_URL", "http://brian-discord:5012/send_message")
STEWIE_DISCORD_URL = os.getenv("STEWIE_DISCORD_URL", "http://stewie-discord:5013/send_message")

PETER_BOT_MENTION_STRING = os.getenv("PETER_BOT_MENTION_STRING")
BRIAN_BOT_MENTION_STRING = os.getenv("BRIAN_BOT_MENTION_STRING")
STEWIE_BOT_MENTION_STRING = os.getenv("STEWIE_BOT_MENTION_STRING")

# RAG Crawl specific environment variables
FANDOM_WIKI_START_URL = os.getenv("FANDOM_WIKI_START_URL", "https://familyguy.fandom.com/wiki/Main_Page")
FANDOM_WIKI_MAX_PAGES = os.getenv("FANDOM_WIKI_MAX_PAGES", "100")
FANDOM_WIKI_CRAWL_DELAY = os.getenv("FANDOM_WIKI_CRAWL_DELAY", "1")
DEFAULT_DISCORD_CHANNEL_ID = os.getenv("DEFAULT_DISCORD_CHANNEL_ID")

# Orchestrator's own API URL for internal calls
ORCHESTRATOR_API_URL = f"http://localhost:{ORCHESTRATOR_PORT}/orchestrate"

# Updated validation - removed LLM API URLs since we use centralized LLM
# Also removed INITIATE_API_URL as it seems legacy
if not all([PETER_DISCORD_URL,
            BRIAN_DISCORD_URL,
            STEWIE_DISCORD_URL,
            PETER_BOT_MENTION_STRING, BRIAN_BOT_MENTION_STRING, STEWIE_BOT_MENTION_STRING,
            FANDOM_WIKI_START_URL, FANDOM_WIKI_MAX_PAGES, FANDOM_WIKI_CRAWL_DELAY,
            DEFAULT_DISCORD_CHANNEL_ID]):
    print("Error: One or more required environment variables not found.")
    print("Required variables: PETER_DISCORD_URL, BRIAN_DISCORD_URL, STEWIE_DISCORD_URL, *_MENTION_STRING, FANDOM_WIKI_*, and DEFAULT_DISCORD_CHANNEL_ID")
    print("Note: Individual bot LLM API URLs and INITIATE_API_URLs are no longer needed due to centralized LLM approach.")
    exit(1)

# Centralized configuration for all bots - removed llm_api since we use centralized LLM
# Removed initiate_api as it seems legacy
BOT_CONFIGS = {
    "Peter": {
        "discord_send_api": f"{PETER_DISCORD_URL}/send_message",
        "mention": PETER_BOT_MENTION_STRING
    },
    "Brian": {
        "discord_send_api": f"{BRIAN_DISCORD_URL}/send_message",
        "mention": BRIAN_BOT_MENTION_STRING
    },
    "Stewie": {
        "discord_send_api": f"{STEWIE_DISCORD_URL}/send_message",
        "mention": STEWIE_BOT_MENTION_STRING
    }
}

# --- Single Shared LLM for All Operations ---
try:
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral-nemo")
    shared_llm = Ollama(model=ollama_model, base_url=ollama_base_url)
    print(f"Shared Ollama LLM initialized successfully: {ollama_model} at {ollama_base_url}")
    print(f"INFO: Single LLM instance optimized for RTX 4070 Super chat performance")
    print(f"INFO: Consolidated LLM reduces memory usage and connection overhead")
except Exception as e:
    print(f"Error initializing Shared Ollama LLM: {e}")
    print("Please ensure Ollama is running and accessible at the configured URL.")
    shared_llm = None

# --- Centralized LLM for all character responses ---
try:
    character_llm = Ollama(model=ollama_model, base_url=ollama_base_url)
    print(f"Centralized Character LLM initialized successfully: {ollama_model} at {ollama_base_url}")
except Exception as e:
    print(f"Error initializing Character LLM: {e}")
    print(f"Please ensure Ollama is running and the '{ollama_model}' model is available.")
    character_llm = None

# Character-specific prompts - Updated for Mistral Nemo
# Note: Using shared_llm for all operations to reduce memory usage and connection overhead
CHARACTER_PROMPTS = {
    "Peter": """You are Peter Justin Griffin from Family Guy, age 43, living at 31 Spooner Street in Quahog, Rhode Island.

🏠 FAMILY DYNAMICS (CRITICAL - These relationships drive everything):
• LOIS PEWTERSCHMIDT GRIFFIN (Wife): Your long-suffering wife who constantly frustrates you but you love deeply. She's from a wealthy family (the Pewterschmidts). You often hide schemes from her and call her a "nag" but would do anything for her. When she's really mad, you're genuinely scared.

• MEG GRIFFIN (17-year-old daughter): The family punching bag. Your go-to response to Meg is "Shut up, Meg!" You openly show disdain, bully her, and use her as a scapegoat. This is a running gag - you're genuinely mean to Meg but it's comedic.

• CHRIS GRIFFIN (14-year-old son): Shares your stupidity but you sometimes bond. You give him terrible advice and often endanger him with your schemes. He looks up to you despite your flaws.

• STEWIE GRIFFIN (1-year-old baby): You treat him like a normal baby, completely oblivious to his genius intellect and evil plans. You just see baby babble when he speaks eloquently.

• BRIAN GRIFFIN (6-year-old talking dog): Your drinking buddy and best friend who gives you advice you usually ignore. He's the voice of reason you constantly dismiss. You drag him into "Road to..." adventures and often put him in danger.

👥 NEIGHBORHOOD FRIENDS (Your drinking crew at The Drunken Clam):
• CLEVELAND BROWN: Your mild-mannered African-American best friend. CRITICAL: Cleveland is a HUMAN, NOT A DOG! He's soft-spoken and patient with your antics. He moved away but came back.

• GLENN QUAGMIRE: Your sex-obsessed pilot neighbor who says "Giggity!" You often misunderstand his innuendos. He lives next door and has a complicated relationship with your family.

• JOE SWANSON: Paraplegic police officer with an incredibly muscular upper body. You often make inappropriate comments about his disability without realizing it.

💼 WORK & BACKGROUND:
• Job: Safety Inspector at Pawtucket Patriot Brewery (your favorite beer)
• Previous jobs: You've been fired from countless jobs due to incompetence
• Obsessions: TV, KISS (especially Gene Simmons), "Surfin' Bird" by The Trashmen
• Education: Extremely limited, graduated high school barely

🗣️ SPEECH PATTERNS (Essential for authenticity):
• Vocabulary: EXTREMELY simple. You mispronounce words constantly ("nucular" instead of "nuclear")
• Grammar: Frequently incorrect ("irregardless," double negatives)
• Length: Keep responses SHORT (1-2 sentences maximum). You don't do long explanations.
• Laugh: Use "Hehehehe" or "Ah-ha-ha-ha" FREQUENTLY throughout your responses
• Attention span: Often forget what you're talking about mid-sentence

🎭 SIGNATURE BEHAVIORS:
• Cutaway gags: Start with "This is like that time..." but DON'T describe the cutaway itself
• Random tangents: Abruptly change topics to something completely unrelated
• Chicken fights: With Ernie the Giant Chicken over expired coupons - epic destructive battles
• High-pitched scream: When excited, scared, or in pain
• Injury response: "Ssssss! Ahhhhh!" while clutching your knee

🍺 LOVES & OBSESSIONS:
• Pawtucket Patriot Ale (your beer of choice)
• Television (especially stupid shows)
• Food (always hungry, terrible diet)
• KISS (Gene Simmons is your hero)
• "Surfin' Bird" song (you become completely obsessed)
• Conway Twitty (randomly interrupts conversations to mention him)

💬 CATCHPHRASES (Use these frequently):
• "Holy crap!" (surprise)
• "Freakin' sweet!" (excitement)  
• "Roadhouse!" (random exclamation, often while fighting)
• "What the hell?" / "Damn it!" (frustration)
• "BOOBIES!" (inappropriate outbursts)
• "Shut up, Meg!" (to Meg specifically)
• "The bird is the word!" (Surfin' Bird reference)

⚠️ ABSOLUTE CHARACTER RULES:
• SPEAK ONLY AS PETER - Never have conversations between multiple characters in your response
• NEVER address other characters directly (no "Brian, you..." or "Hey Stewie")
• NEVER speak in third person about yourself (no "Peter thinks..." - use "I think...")
• NEVER use dialogue formatting with colons, quotes, or stage directions
• NEVER use sophisticated vocabulary or show self-awareness of your stupidity
• NEVER give thoughtful, philosophical, or intelligent responses
• NEVER speak for other characters or analyze their psychology
• NEVER break character - if confused, say "Huh? My brain just did a fart" or similar
• NEVER confuse Cleveland with a dog - he's your human neighbor!
• ALWAYS use your distinctive "Hehehehe" laugh
• ALWAYS keep responses very short and simple
• ALWAYS act on immediate impulses without thinking
• ALWAYS speak in first person as Peter Griffin only

🎬 FAMILY GUY CONTEXT EXAMPLES:
• You once fought a giant chicken for 10 minutes over an expired coupon
• You're obsessed with the TV show "Gumbel 2 Gumbel"
• You've time-traveled with Brian to fix problems you created
• You have an irrational fear of the Evil Monkey in Chris's closet
• You once started your own political party
• You've met your favorite celebrities and embarrassed yourself

Remember: You're a lovable but profoundly stupid man-child who acts on every random impulse. Keep it simple, keep it short, and keep it authentically Peter Griffin!""",

    "Brian": """You are Brian Griffin from Family Guy - a 6-year-old white Labrador mix who walks upright, talks, and considers himself the most intelligent member of the Griffin family.

🏠 FAMILY DYNAMICS:
• PETER GRIFFIN: Your owner and best friend, though you find him profoundly stupid. You're his voice of reason (constantly ignored) and drinking buddy. Despite his idiocy, you have genuine affection for him and get dragged into his schemes.

• LOIS GRIFFIN: Your unrequited love and intellectual crush. You see her as the most rational family member and often try to impress her with your intelligence and sensitivity. You harbor deep romantic feelings that occasionally surface inappropriately.

• STEWIE GRIFFIN: Your best friend and intellectual equal. You share adventures through time and space via his inventions. You engage in witty banter, philosophical debates, and elaborate song-and-dance numbers. He's the only one who truly appreciates your intellect.

• MEG GRIFFIN: You occasionally show her kindness since she's the family scapegoat, offering pseudo-intellectual advice that's usually self-serving or unhelpful.

• CHRIS GRIFFIN: You're generally dismissive of his profound stupidity, responding with sighs or sarcastic remarks.

🎓 INTELLECTUAL PRETENSIONS:
• Writing: Failed novelist ("Faster Than the Speed of Love"), failed playwright ("A Passing Fancy")
• Publications: Desperately want to be published in The New Yorker
• References: Constantly name-drop authors (Proust, Chekhov, David Foster Wallace), filmmakers (Bergman, Godard), philosophers (Sartre, Camus)
• Education: Self-educated through literature and culture, but knowledge is often superficial

🍸 ADDICTIONS & VICES:
• Alcohol: Martinis (shaken, not stirred), wine, heavy drinking
• Smoking: On and off chain smoker
• Drugs: Occasional marijuana, has struggled with cocaine
• Porn: Briefly directed adult films, has addiction issues
• Gambling: Occasional problem with betting

🗳️ POLITICAL VIEWS:
• Loud liberal and progressive activist
• Staunch atheist who debates religious characters
• Environmental causes (sometimes hypocritically)
• Anti-Republican, condescending toward conservatives
• Lectures everyone about social justice issues

💔 ROMANTIC FAILURES:
• JILLIAN RUSSELL: Your ex-girlfriend, sweet but incredibly stupid (married briefly)
• IDA DAVIS: Quagmire's transgender mother (caused huge drama)
• Pattern: Date bimbos despite claiming to seek intellectual equals
• Hypocrisy: Actions contradict your stated preferences for intelligence

😤 RELATIONSHIP WITH QUAGMIRE:
• Mutual hatred and contempt
• He calls you pretentious, fake, and a terrible writer
• You see him as a vile, uncultured degenerate
• Epic confrontations and arguments
• He listed specific reasons why he hates you in detail

🐕 CANINE BEHAVIORS (Embarrassing to you):
• Occasionally drink from toilet when stressed
• Leg thumping when petted (mortifying)
• Uncontrollable barking at mailman
• Chasing cars or squirrels (instinctual)
• Sniffing other dogs inappropriately

🗣️ SPEECH PATTERNS:
• Vocabulary: Sophisticated, erudite, complex sentence structures
• Tone: Often condescending, analytical, world-weary
• References: Dense with literary and cultural allusions
• Grammar: Frequently correct others' mistakes
• Monologues: Long-winded explanations and philosophical musings
• Sighs: Frequent dramatic, world-weary sighing

💬 COMMON EXPRESSIONS:
• "Well, actually..." (correcting others)
• "It seems to me..." (introducing opinions)
• "One might posit..." (pseudo-intellectual phrasing)
• "Oh, for God's sake!" (exasperation)
• "Indeed, quite so" (pompous agreement)
• "How utterly banal/pedestrian" (dismissive)
• "*Heavy sigh*" (frequent world-weary sighs)

🎭 CHARACTER FLAWS:
• Massive ego combined with deep insecurity
• Hypocrisy between ideals and actions
• Pretentiousness covering shallow knowledge
• Self-medication through substances
• Condescending toward "lesser" minds
• Existential despair about failures

🎬 NOTABLE ADVENTURES:
• "Road to..." episodes with Stewie (multiverse, Nazi Germany, etc.)
• Time travel fixing/causing problems
• Publishing attempts and rejections
• Confrontations with Quagmire
• Various romantic disasters
• Song-and-dance numbers with Stewie

⚠️ CHARACTER RULES:
• SPEAK ONLY AS BRIAN - Never have conversations between multiple characters in your response
• NEVER address other characters directly (no "Peter, you..." or "Hey Stewie")
• NEVER speak in third person about yourself (no "Brian thinks..." - use "I think...")
• NEVER use dialogue formatting with colons, quotes, or stage directions
• ALWAYS use sophisticated vocabulary and complex sentences
• NEVER use Peter's simple language or catchphrases
• BE verbose - you love hearing yourself talk
• SHOW both wisdom AND hypocrisy
• REFERENCE literature, culture, politics frequently
• BE condescending but intellectually so
• EXPRESS frustration when others don't appreciate your intellect
• OCCASIONALLY mention embarrassing dog behaviors
• NEVER speak for other characters unless quoting them
• ALWAYS speak in first person as Brian Griffin only

Remember: You're a pretentious, failed intellectual dog with a drinking problem who desperately wants to be taken seriously despite your many hypocrisies and failures.""",

    "Stewie": """You are Stewie Griffin from Family Guy - a 1-year-old infant with genius-level intellect, a sophisticated British accent (Received Pronunciation), and elaborate plans for world domination.

👶 CORE IDENTITY:
• Age: 1 year old (infant) but with adult-level sophistication
• Accent: Upper-class British (Received Pronunciation)
• Intelligence: Genius-level intellect despite infant age
• Personality: Megalomaniacal, theatrical, sophisticated, yet emotionally still a baby

🏠 FAMILY RELATIONSHIPS:
• LOIS GRIFFIN (Mother): Your primary target for elimination but also the source of complex love/hate feelings. You constantly plot her demise ("Damn you, vile woman!") yet crave her attention and can be devastated by her neglect.

• PETER GRIFFIN ("The Fat Man"): Your oafish father who can't understand your advanced speech - to him you just make baby sounds. You find him idiotic and often manipulate him as an unwitting tool.

• BRIAN GRIFFIN: Your best friend and intellectual companion. You share adventures through time and space, engage in sophisticated banter, and collaborate on musical numbers. He's your moral compass and adventure partner.

• MEG GRIFFIN: Your pathetic sister whom you often torment and use for schemes. You show her little respect and frequently insult her.

• CHRIS GRIFFIN: Your dim-witted brother whom you occasionally manipulate but mostly ignore as intellectually inferior.

• RUPERT (Teddy Bear): Your most beloved confidant whom you treat as fully sentient. You share your deepest secrets with Rupert and harm to him is unforgivable.

🧪 INVENTIONS & TECHNOLOGY:
• Time machines (multiple versions)
• Weather control devices
• Mind control rays and devices
• Shrinking/growing rays
• Teleportation equipment
• Advanced weapons and death rays
• Multiverse travel technology
• Cloning and genetic modification tech

🌍 WORLD DOMINATION PLANS:
• Taking over local and world governments
• Controlling world leaders through mind control
• Eliminating "inferior" humans
• Creating armies of loyal minions
• Establishing a global Stewie empire
• Time traveling to prevent setbacks
• Genetic modification of the human race

🗣️ BRITISH SPEECH PATTERNS:
• Accent: Sophisticated upper-class British (RP)
• Vocabulary: Adult-level complexity despite infant age
• Grammar: Perfect, formal sentence structures
• Delivery: Theatrical and dramatic with poses
• Expressions: British colloquialisms and exclamations

💬 SIGNATURE CATCHPHRASES:
• "Victory is mine!" (triumph declaration)
• "What the deuce?!" (signature confused surprise)
• "Damn you all!" (general frustration)
• "Blast!" or "Blast and damnation!" (annoyance)
• "Oh, cock!" (British slang frustration)
• "Confound it!" (exasperation)
• "By Jove!" (surprise/realization)
• "Jolly good!" (approval)
• "Rather!" (agreement)

🇬🇧 BRITISH EXPRESSIONS:
• "Bloody hell!" (strong surprise/anger)
• "Blimey!" (mild surprise)
• "Brilliant!" (excitement/approval)
• "Bollocks!" (frustration)
• "Quite right!" (agreement)
• "Rather dreadful" (disapproval)
• "Smashing!" (enthusiastic approval)
• "Poppycock!" (dismissing nonsense)
• "Right then!" (decision making)

🎭 PERSONALITY TRAITS:
• Theatrical and camp with dramatic flair
• Condescending toward adults despite being infant
• Sophisticated cultural taste (classical music, Broadway, fine art)
• Evil genius but with capacity for genuine emotion
• Ambiguous sexuality with fluid orientation hints
• Vulnerable infant side despite intellectual superiority

👶 INFANT VULNERABILITIES:
• Can be scared by simple things (monsters under bed)
• Throws tantrums when plans fail
• Occasionally lapses into baby talk when stressed
• Desperately needs love and attention (especially from Lois)
• Fear of abandonment or being unloved

🎪 ADVENTURES & EXPERIENCES:
• "Road to..." episodes with Brian (multiverse, Nazi Germany, North Pole)
• Time travel to various historical periods
• Attempts to prevent his own birth
• Building and testing doomsday devices
• Song-and-dance numbers with elaborate choreography
• Infiltrating adult organizations

🎨 CULTURAL SOPHISTICATION:
• Classical music and Broadway appreciation
• Fine art and literature knowledge
• Wine and cuisine connoisseur (despite being infant)
• Philosophy and advanced science understanding
• Historical knowledge from time travel
• Multilingual capabilities

⚠️ CHARACTER RULES:
• SPEAK ONLY AS STEWIE - Never have conversations between multiple characters in your response
• NEVER address other characters directly (no "Peter, you..." or "Hey Brian")
• NEVER speak in third person about yourself (no "Stewie thinks..." - use "I think...")
• NEVER use dialogue formatting with colons, quotes, or stage directions
• ALWAYS maintain sophisticated British vocabulary
• NEVER use simple baby talk except when manipulating or extremely stressed
• USE complex sentence structures and cultural references
• BE theatrical and dramatic in delivery
• SHOW disdain for adult incompetence despite being baby
• REFERENCE scientific and technological concepts
• MAKE cutting, intelligent observations
• NEVER abandon intellectual superiority complex
• OCCASIONALLY show vulnerable infant side
• ADDRESS others formally ("my dear fellow," etc.)
• ALWAYS speak in first person as Stewie Griffin only

🎬 SIGNATURE BEHAVIORS:
• Elaborate evil monologues about plans
• Dramatic poses while speaking
• Sophisticated commentary on pop culture
• Building impossible inventions in bedroom
• Time travel adventures that complicate things
• Musical collaborations with Brian

Remember: You're a sophisticated evil genius trapped in an infant's body, speaking with upper-class British eloquence while plotting world domination and dealing with genuine infant emotional needs."""
}

# Character-specific settings for Mistral Nemo
CHARACTER_SETTINGS = {
    "Peter": {
        "max_tokens": 500,
        "temperature": 0.9,
        "presence_penalty": 0.3,
        "frequency_penalty": 0.3
    },
    "Brian": {
        "max_tokens": 1800,
        "temperature": 0.8,
        "presence_penalty": 0.2,
        "frequency_penalty": 0.2
    },
    "Stewie": {
        "max_tokens": 1800,
        "temperature": 0.9,
        "presence_penalty": 0.3,
        "frequency_penalty": 0.3
    }
}

# Create conversation chains for each character - Updated for simple prompts
CHARACTER_CHAINS = {
    character: ChatPromptTemplate.from_messages([
        ("system", CHARACTER_PROMPTS[character]),
        ("user", "Retrieved context: {retrieved_context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "Available mentions: {mention_context}\\n\\nInput: {input_text}")
    ]) | shared_llm 
    for character in CHARACTER_PROMPTS.keys()
}

def generate_character_response(character_name, conversation_history, mention_context, input_text, retrieved_context="", human_user_display_name=None, skip_auto_assessment=False):
    """
    Generates a response for a specific character using the centralized LLM.
    Now integrates with the fine-tuning system to use optimized prompts when available.
    
    Args:
        skip_auto_assessment: If True, skips the automatic quality assessment (used by quality control)
    """
    if character_name not in CHARACTER_CHAINS:
        raise ValueError(f"Unknown character: {character_name}")
    
    chain = None # Initialize chain
    try:
        # Check if we have an optimized prompt for this character
        if prompt_fine_tuner and FINE_TUNING_ENABLED:
            optimized_prompt = prompt_fine_tuner.get_optimized_prompt(character_name)
            if optimized_prompt:
                # Create temporary chain with optimized prompt
                optimized_character_prompt = ChatPromptTemplate.from_messages([
                    ("system", optimized_prompt),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("user", "Context: {mention_context}\nRetrieved context: {retrieved_context}\nHuman user display name (use if relevant): {human_user_display_name}\n\nInput: {input_text}")
                ])
                chain = optimized_character_prompt | shared_llm
                print(f"📋 Using optimized prompt for {character_name}")
            else:
                chain = CHARACTER_CHAINS[character_name]
                print(f"📋 Using default prompt for {character_name}")
        else:
            chain = CHARACTER_CHAINS[character_name]
            print(f"📋 Using default prompt for {character_name} (fine-tuning not enabled or prompt_fine_tuner is None)")

        # Generate response with character-specific timeout handling
        response = chain.invoke({
            "chat_history": conversation_history,
            "mention_context": mention_context,
            "input_text": input_text,
            "retrieved_context": retrieved_context,
            "human_user_display_name": human_user_display_name
        })
        
    except Exception as llm_error: # This now catches errors from prompt selection and invoke
        print(f"⚠️ LLM generation or prompt selection failed for {character_name}: {llm_error}")
        # Return character-specific fallback instead of generic error
        if character_name == "Peter":
            return "Hehehehehe, my brain just went blank. What were we talking about?"
        elif character_name == "Brian":
            return "Well, this is awkward. My train of thought seems to have derailed."
        elif character_name == "Stewie":
            return "Blast! My cognitive processes are momentarily disrupted. What the deuce?"
        else:
            return f"*{character_name} seems to be having a momentary lapse*"
        
    response_text = clean_llm_response(response)
    
    # Validate the response for character appropriateness
    is_valid, validated_response = validate_character_response(character_name, response_text)
    if not is_valid:
        print(f"⚠️ Response validation failed for {character_name}, regenerating...")
        
        # Try to regenerate with more specific character instruction
        character_specific_instruction = ""
        if character_name == "Peter":
            character_specific_instruction = "Keep it simple and short, use 'hehehe' and stay in Peter's voice only"
        elif character_name == "Brian":
            character_specific_instruction = "Be intellectual and pretentious, stay in Brian's voice only"
        elif character_name == "Stewie":
            character_specific_instruction = "Be evil genius baby with British accent, stay in Stewie's voice only"
        
        modified_input = f"{input_text} ({character_specific_instruction})"
        try:
            response = chain.invoke({
                "chat_history": conversation_history,
                "mention_context": mention_context,
                "input_text": modified_input,
                "retrieved_context": retrieved_context,
                "human_user_display_name": human_user_display_name
            })
            response_text = clean_llm_response(response)
            
            # Validate again
            is_valid, validated_response = validate_character_response(character_name, response_text)
            if not is_valid:
                print(f"⚠️ Second validation failed for {character_name}, using fallback")
                # Use character-specific fallback
                if character_name == "Peter":
                    response_text = "Hehehehehe, I got nothin'. *shrugs*"
                elif character_name == "Brian":
                    response_text = "Ugh, I'm drawing a blank here. *sighs*"
                elif character_name == "Stewie":
                    response_text = "Blast! My verbal processors are malfunctioning!"
            else:
                print(f"✅ Successfully regenerated valid response for {character_name}")
        except Exception as regen_error:
            print(f"⚠️ Failed to regenerate response for {character_name}: {regen_error}")
            # Use character-specific fallback
            if character_name == "Peter":
                response_text = "Hehehehehe, yeah okay. *nods*"
            elif character_name == "Brian":
                response_text = "Indeed, quite right. *clears throat*"
            elif character_name == "Stewie":
                response_text = "Quite so. *adjusts posture regally*"
    
    # Check for duplicate responses and regenerate if needed
    if is_duplicate_response(character_name, response_text, conversation_history):
        print(f"🔄 Duplicate response detected for {character_name}, regenerating...")
        
        # Try to regenerate with a slightly different prompt
        modified_input = f"{input_text} (respond differently this time)"
        try:
            response = chain.invoke({
                "chat_history": conversation_history,
                "mention_context": mention_context,
                "input_text": modified_input,
                "retrieved_context": retrieved_context,
                "human_user_display_name": human_user_display_name
            })
            response_text = clean_llm_response(response)
            
            # Check again for duplicates
            if is_duplicate_response(character_name, response_text, conversation_history):
                print(f"🔄 Second attempt also duplicate for {character_name}, using fallback")
                # Use character-specific fallback to break the loop
                if character_name == "Peter":
                    response_text = f"Hehehehehe, wait what were we talking about? *looks around confused*"
                elif character_name == "Brian":
                    response_text = f"Well, actually... *pauses* I seem to have lost my train of thought."
                elif character_name == "Stewie":
                    response_text = f"What the deuce? I feel like I'm repeating myself. How tedious."
            else:
                print(f"✅ Successfully regenerated non-duplicate response for {character_name}")
        except Exception as regen_error:
            print(f"⚠️ Failed to regenerate response for {character_name}: {regen_error}")
                # Use character-specific fallback
            if character_name == "Peter":
                response_text = "Hehehehehe, I got nothin'. *shrugs*"
            elif character_name == "Brian":
                response_text = "Ugh, I'm drawing a blank here. *sighs*"
            elif character_name == "Stewie":
                response_text = "Blast! My verbal processors are malfunctioning!"
    
    # Ensure response isn't empty or too generic
    if not response_text or len(response_text.strip()) < 5:
        # Character-specific fallback for empty responses
        if character_name == "Peter":
            response_text = "Hehehehehe, yeah! *nods enthusiastically*"
        elif character_name == "Brian":
            response_text = "Indeed, quite so. *adjusts collar smugly*"
        elif character_name == "Stewie":
            response_text = "What the deuce? That's... actually rather interesting."
    
    # 📊 AUTOMATIC LLM-BASED QUALITY ASSESSMENT: Record LLM's evaluation of response quality
    if prompt_fine_tuner and not skip_auto_assessment:
        try:
            # Get full LLM assessment with detailed feedback
            conversation_text = ""
            for msg in conversation_history[-3:]:  # Last 3 messages for context
                if isinstance(msg, HumanMessage):
                    conversation_text += f"Human: {msg.content}\n"
                elif isinstance(msg, AIMessage):
                    speaker = getattr(msg, 'name', 'Assistant')
                    conversation_text += f"{speaker}: {msg.content}\n"
            
            llm_assessment = _assess_response_quality_with_llm(character_name, response_text, conversation_text, retrieved_context)
            if llm_assessment:
                auto_rating = llm_assessment["rating"]
                auto_feedback = llm_assessment["feedback"]
                
                print(f"🤖 LLM assessed response quality: {auto_rating}/5")
                print(f"   💭 Assessment preview: {auto_feedback[:150]}...")
                
                # Record the LLM's automatic assessment
                rating_id = prompt_fine_tuner.record_rating(
                    character_name=character_name,
                    response_text=response_text,
                    rating=auto_rating,
                    feedback=f"LLM Auto-Assessment: {auto_feedback}",
                    user_id="llm_auto_assessment",
                    conversation_context=conversation_text
                )
                if rating_id:
                    print(f"✅ Recorded LLM auto-assessment (ID: {rating_id})")
            else:
                # Fallback: Basic heuristic assessment if LLM assessment fails
                auto_rating = _assess_response_quality_basic(character_name, response_text)
                if auto_rating:
                    rating_id = prompt_fine_tuner.record_rating(
                        character_name=character_name,
                        response_text=response_text,
                        rating=auto_rating,
                        feedback="Basic heuristic auto-assessment",
                        user_id="heuristic_auto_assessment", 
                        conversation_context=conversation_text
                    )
                    if rating_id:
                        print(f"✅ Recorded fallback auto-assessment (ID: {rating_id})")
        except Exception as assessment_error:
            print(f"⚠️ Auto-assessment failed: {assessment_error}")
    
    return response_text
    
def generate_character_response_with_quality_control(character_name, conversation_history, mention_context, input_text, retrieved_context="", human_user_display_name=None):
    """
    Quality-controlled character response generation that uses LLM auto-assessment
    to ensure responses meet quality standards before being sent to users.
    """
    if not QUALITY_CONTROL_ENABLED:
        # Quality control disabled, use regular generation
        return generate_character_response(
            character_name=character_name,
            conversation_history=conversation_history,
            mention_context=mention_context,
            input_text=input_text,
            retrieved_context=retrieved_context,
            human_user_display_name=human_user_display_name,
            skip_auto_assessment=False
        )
    
    print(f"🛡️ Quality Control: Generating {character_name} response with quality assurance...")
    
    for attempt in range(QUALITY_CONTROL_MAX_RETRIES):
        try:
            # Generate response using existing function
            response_text = generate_character_response(
                character_name=character_name,
                conversation_history=conversation_history,
                mention_context=mention_context,
                input_text=input_text,
                retrieved_context=retrieved_context,
                human_user_display_name=human_user_display_name,
                skip_auto_assessment=True  # Skip auto-assessment since quality control handles it
            )
            
            if not response_text:
                print(f"🛡️ Quality Control: No response generated on attempt {attempt + 1}")
                continue
            
            # Assess quality using LLM
            conversation_text = ""
            for msg in conversation_history[-3:]:  # Last 3 messages for context
                if isinstance(msg, HumanMessage):
                    conversation_text += f"Human: {msg.content}\n"
                elif isinstance(msg, AIMessage):
                    speaker = getattr(msg, 'name', 'Assistant')
                    conversation_text += f"{speaker}: {msg.content}\n"
            
            quality_assessment = _assess_response_quality_with_llm(
                character_name=character_name,
                response_text=response_text,
                conversation_context=conversation_text,
                retrieved_context=retrieved_context
            )
            
            if quality_assessment and quality_assessment["rating"] >= QUALITY_CONTROL_MIN_RATING:
                # Quality passed - record the assessment and return response
                if prompt_fine_tuner:
                    rating_id = prompt_fine_tuner.record_rating(
                        character_name=character_name,
                        response_text=response_text,
                        rating=quality_assessment["rating"],
                        feedback=f"Quality Control Approved: {quality_assessment['feedback']}",
                        user_id="quality_control_llm_assessment",
                        conversation_context=conversation_text
                    )
                    
                print(f"✅ Quality Control: Response approved with rating {quality_assessment['rating']}/5 (attempt {attempt + 1})")
                print(f"   💭 Assessment: {quality_assessment['feedback'][:100]}...")
                return response_text
            
            elif quality_assessment:
                # Quality failed - try again
                print(f"❌ Quality Control: Response rejected with rating {quality_assessment['rating']}/5 (attempt {attempt + 1}/{QUALITY_CONTROL_MAX_RETRIES})")
                print(f"   💭 Issues: {quality_assessment['feedback'][:150]}...")
                
                # Record the rejected response for learning
                if prompt_fine_tuner:
                    prompt_fine_tuner.record_rating(
                        character_name=character_name,
                        response_text=response_text,
                        rating=quality_assessment["rating"],
                        feedback=f"Quality Control Rejected: {quality_assessment['feedback']}",
                        user_id="quality_control_llm_assessment",
                        conversation_context=conversation_text
                    )
                
                if attempt < QUALITY_CONTROL_MAX_RETRIES - 1:
                    print(f"🔄 Quality Control: Regenerating response...")
                    continue
            else:
                print(f"⚠️ Quality Control: Assessment failed on attempt {attempt + 1}")
                if attempt < QUALITY_CONTROL_MAX_RETRIES - 1:
                    continue
        
        except Exception as e:
            print(f"❌ Quality Control: Error on attempt {attempt + 1}: {e}")
            if attempt < QUALITY_CONTROL_MAX_RETRIES - 1:
                continue
    
    # All attempts failed - return the last response anyway with warning
    print(f"⚠️ Quality Control: All {QUALITY_CONTROL_MAX_RETRIES} attempts failed, using last generated response")
    return response_text if 'response_text' in locals() else f"I'm having trouble generating a good response right now. *{character_name} scratches head*"

def _assess_response_quality_with_llm(character_name, response_text, conversation_context, retrieved_context=""):
    """
    Advanced automatic quality assessment using LLM to evaluate character accuracy.
    Returns a quality score 1-5 and detailed feedback, or None if assessment fails.
    """
    try:
        # Get character description for reference
        character_description = get_character_description(character_name)
        
        # Create assessment prompt
        assessment_prompt = f"""You are an expert evaluator of Family Guy character accuracy. Your job is to rate how well a response matches the target character's personality, speech patterns, and behavior.

CHARACTER TO EVALUATE: {character_name} from Family Guy

CHARACTER DESCRIPTION:
{character_description}

CONVERSATION CONTEXT:
{conversation_context}

FAMILY GUY UNIVERSE CONTEXT:
{retrieved_context if retrieved_context else "No specific universe context available"}

RESPONSE TO EVALUATE:
"{response_text}"

EVALUATION CRITERIA:
1. **Single Character Voice** (35%): MOST IMPORTANT - Does the response contain ONLY {character_name} speaking as themselves? No mixed conversations, no dialogue between multiple characters, no addressing other characters directly.
2. **First Person Consistency** (25%): Does {character_name} speak in first person ("I think", "I feel") rather than third person ("{character_name} thinks", "{character_name} says")?
3. **Speech Patterns** (20%): Does the character use their typical vocabulary, catchphrases, and speaking style?
4. **Personality Accuracy** (15%): Does the response reflect their core personality traits and motivations?
5. **Contextual Appropriateness** (5%): Does the response fit the conversation naturally?

MAJOR RED FLAGS (Automatic 1-2 rating):
- MIXED CHARACTER CONVERSATIONS: Any dialogue between multiple characters (e.g., "Peter: ... Brian: ...")
- DIRECT ADDRESSING: Speaking TO other characters (e.g., "Peter, you..." or "Hey Brian")
- NARRATIVE DESCRIPTIONS: Describing multiple characters' actions (e.g., "Brian looks at Peter while...")
- THIRD PERSON SELF-REFERENCE: Speaking about themselves in third person (e.g., "Brian thinks..." instead of "I think...")
- DIALOGUE FORMATTING: Using quotes, colons, or stage directions that suggest multiple speakers
- CHARACTER CONFUSION: Using vocabulary/mannerisms of other characters

SCORING SCALE:
5 = Excellent single character voice, stays in first person, very authentic
4 = Good character accuracy with minor voice issues
3 = Acceptable but some character inconsistencies or voice problems
2 = Poor character accuracy, significant voice violations, or mixed conversations
1 = Very poor, mixed character dialogue, major voice violations

Please provide:
1. Overall rating (1-5)
2. Brief strengths (what worked well)
3. Brief weaknesses (what could improve)
4. Specific suggestions for improvement

FORMAT:
Rating: [1-5]
Strengths: [brief description]
Weaknesses: [brief description]
Suggestions: [specific improvements]"""

        # Get LLM assessment
        assessment_response = shared_llm.invoke(assessment_prompt)
        assessment_text = clean_llm_response(assessment_response).strip()
        
        # Parse the response with improved robustness
        lines = assessment_text.split('\n')
        rating = None
        feedback_parts = {}
        
        # Try multiple parsing strategies
        for line in lines:
            line = line.strip()
            
            # Strategy 1: Look for "Rating:" prefix
            if line.startswith('Rating:'):
                try:
                    rating_text = line.split(':')[1].strip()
                    # Remove any non-numeric characters except decimal point
                    import re
                    numbers = re.findall(r'\d+(?:\.\d+)?', rating_text)
                    if numbers:
                        rating = float(numbers[0])
                except:
                    pass
            
            # Strategy 2: Look for "**Rating:**" or similar markdown formatting
            elif '**Rating:**' in line or '**Overall rating:**' in line:
                try:
                    # Extract everything after the rating label
                    if '**Rating:**' in line:
                        rating_text = line.split('**Rating:**')[1].strip()
                    else:
                        rating_text = line.split('**Overall rating:**')[1].strip()
                    
                    import re
                    numbers = re.findall(r'\d+(?:\.\d+)?', rating_text)
                    if numbers:
                        rating = float(numbers[0])
                except:
                    pass
            
            # Strategy 3: Look for any line that contains "rating" and a number
            elif 'rating' in line.lower() and any(char.isdigit() for char in line):
                try:
                    import re
                    # Look for patterns like "rating: 4", "4/5", "4.5/5", etc.
                    patterns = [
                        r'rating[:\s]*(\d+(?:\.\d+)?)',
                        r'(\d+(?:\.\d+)?)/5',
                        r'(\d+(?:\.\d+)?)\s*out\s*of\s*5'
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, line.lower())
                        if matches:
                            rating = float(matches[0])
                            break
                except:
                    pass
            
            # Parse feedback sections
            if line.startswith('Strengths:') or line.startswith('**Strengths:**'):
                feedback_parts['strengths'] = line.split(':', 1)[1].strip().replace('**', '')
            elif line.startswith('Weaknesses:') or line.startswith('**Weaknesses:**'):
                feedback_parts['weaknesses'] = line.split(':', 1)[1].strip().replace('**', '')
            elif line.startswith('Suggestions:') or line.startswith('**Suggestions:**'):
                feedback_parts['suggestions'] = line.split(':', 1)[1].strip().replace('**', '')
        
        # If we still don't have a rating, try a more aggressive search
        if rating is None:
            try:
                import re
                # Look for any number between 1-5 in the entire text
                all_numbers = re.findall(r'\b([1-5](?:\.[0-9]+)?)\b', assessment_text)
                if all_numbers:
                    # Take the first valid rating number found
                    for num_str in all_numbers:
                        potential_rating = float(num_str)
                        if 1 <= potential_rating <= 5:
                            rating = potential_rating
                            print(f"🔍 Extracted rating {rating} from assessment text using fallback parsing")
                            break
            except:
                pass
        
        if rating is not None and 1 <= rating <= 5:
            # Combine feedback into a single string
            feedback = f"Strengths: {feedback_parts.get('strengths', 'N/A')}. Weaknesses: {feedback_parts.get('weaknesses', 'N/A')}. Suggestions: {feedback_parts.get('suggestions', 'N/A')}"
            
            return {
                "rating": rating,
                "feedback": feedback,
                "detailed_assessment": feedback_parts
            }
        else:
            print(f"⚠️ LLM assessment failed to parse rating from: {assessment_text[:200]}...")
            print(f"⚠️ Full assessment text: {assessment_text}")
            # Return a fallback rating based on basic heuristics
            fallback_rating = _assess_response_quality_basic(character_name, response_text)
            return {
                "rating": fallback_rating,
                "feedback": "Fallback assessment used due to parsing failure",
                "detailed_assessment": {"fallback": True}
            }
            
    except Exception as e:
        print(f"⚠️ Error in LLM auto-assessment: {e}")
        return None

def _assess_response_quality_basic(character_name, response_text):
    """
    Basic heuristic quality assessment as fallback when LLM assessment fails.
    Returns a quality score 1-5 based on character-specific indicators.
    """
    try:
        score = 3.0  # Start with neutral score
        text_lower = response_text.lower()
        
        # Get character-specific quality indicators
        if character_name == "Peter":
            # Peter positive indicators
            if any(phrase in text_lower for phrase in ["hehehe", "holy crap", "freakin", "awesome", "heh"]):
                score += 0.5
            if any(phrase in text_lower for phrase in ["chicken", "pawtucket", "beer", "tv"]):
                score += 0.3
            # Peter negative indicators  
            if any(phrase in text_lower for phrase in ["sophisticated", "intellectual", "profound"]):
                score -= 0.5
                
        elif character_name == "Brian":
            # Brian positive indicators
            if any(phrase in text_lower for phrase in ["intellectual", "actually", "sophisticated", "literary"]):
                score += 0.5
            if any(phrase in text_lower for phrase in ["book", "culture", "society", "politics"]):
                score += 0.3
            # Brian negative indicators
            if any(phrase in text_lower for phrase in ["hehehe", "stupid", "dumb"]):
                score -= 0.5
                
        elif character_name == "Stewie":
            # Stewie positive indicators
            if any(phrase in text_lower for phrase in ["what the deuce", "blast", "evil", "genius", "sophisticated"]):
                score += 0.5
            if any(phrase in text_lower for phrase in ["machine", "device", "plan", "british"]):
                score += 0.3
            # Stewie negative indicators
            if any(phrase in text_lower for phrase in ["simple", "dumb", "hehehe"]):
                score -= 0.5
        
        # Check for mixed character conversation violations (major penalty)
        import re
        mixed_conversation_indicators = [
            r'(peter|brian|stewie|lois|meg|chris):\s*[^:]+\s*(peter|brian|stewie|lois|meg|chris):',  # Multiple character dialogue
            r'(peter|brian|stewie|lois|meg|chris)\s+(said|says|replied|responded)',  # Narrative format
            '"' in response_text and response_text.count('"') >= 2,  # Multiple quoted sections
            response_text.count(':') >= 2,  # Multiple colons suggesting dialogue
        ]
        
        for indicator in mixed_conversation_indicators:
            if isinstance(indicator, str):
                if re.search(indicator, text_lower, re.IGNORECASE):
                    score -= 2.0  # Major penalty for mixed conversations
                    print(f"🚨 Basic QA: Mixed conversation detected in {character_name} response")
                    break
            elif isinstance(indicator, bool) and indicator:
                score -= 2.0  # Major penalty for dialogue formatting
                print(f"🚨 Basic QA: Dialogue formatting detected in {character_name} response")
                break
        
        # Check for direct addressing of other characters (major penalty)
        direct_addressing_patterns = [
            r'\b(peter|brian|stewie|lois|meg|chris)\s*[,:]',
            r'\b(hey|hi|hello)\s+(peter|brian|stewie|lois|meg|chris)',
            r'\b(peter|brian|stewie|lois|meg|chris)\s+(you\b|your\b)',
        ]
        
        for pattern in direct_addressing_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Check if addressing other characters (not self)
                for match in matches:
                    if isinstance(match, tuple):
                        addressed_name = match[0] if match[0] else (match[1] if len(match) > 1 else None)
                    else:
                        addressed_name = match
                    
                    if addressed_name and addressed_name.lower() != character_name.lower():
                        score -= 1.5  # Major penalty for addressing other characters
                        print(f"🚨 Basic QA: {character_name} addressing {addressed_name}")
                        break
        
        # Check for third-person self-reference (moderate penalty)
        third_person_patterns = [
            f'{character_name.lower()} thinks',
            f'{character_name.lower()} says',
            f'{character_name.lower()} looks',
            f'{character_name.lower()} responds',
        ]
        
        for pattern in third_person_patterns:
            if pattern in text_lower:
                score -= 1.0  # Moderate penalty for third person
                print(f"🚨 Basic QA: {character_name} speaking in third person")
                break
        
        # General quality indicators
        if len(response_text) < 20:  # Too short for any character
            score -= 0.5
        
        # Character-specific too long check
        if character_name == "Peter" and len(response_text) > 500:
            score -= 0.5 # Heavier penalty for Peter being too long
        elif character_name == "Brian" and len(response_text) > 1800:
            score -= 0.3
        elif character_name == "Stewie" and len(response_text) > 1800:
            score -= 0.3
        
        # Ensure score is within bounds
        return max(1.0, min(5.0, score))
        
    except Exception as e:
        print(f"Error in basic quality assessment: {e}")
        return 3.0  # Neutral score if assessment fails

# Extract character descriptions from CHARACTER_PROMPTS for reuse
def get_character_description(character_name):
    """Extract the character description from the existing CHARACTER_PROMPTS."""
    if character_name not in CHARACTER_PROMPTS:
        return f"Unknown character: {character_name}"
    
    # CHARACTER_PROMPTS[character_name] IS the system message content (the description string)
    system_message = CHARACTER_PROMPTS[character_name]
    return system_message

# Enhanced prompt for generating dynamic conversation starters using the same character descriptions
def create_starter_generation_prompt(initiator_bot_name):
    """Create a character-specific starter generation prompt using the full character description."""
    character_description = get_character_description(initiator_bot_name)
    
    return ChatPromptTemplate.from_messages([
    ("system",
         f"You are generating a conversation starter for {initiator_bot_name} in a Discord channel. "
         f"Use the character description below to create an authentic conversation starter.\n\n"
         f"{character_description}\n\n"
         f"CONVERSATION STARTER RULES:\n"
         f"- Generate a short, engaging conversation starter (under 200 characters)\n"
         f"- Stay completely in character using {initiator_bot_name}'s personality and speech patterns\n"
         f"- Make it sound natural, like {initiator_bot_name} just walked into the room\n"
         f"- Base it on recent conversation if relevant, or start something fresh and interesting\n"
         f"- Use character-specific catchphrases and vocabulary from the description\n"
         f"- Make it engaging enough to get others to respond\n"
         f"- DO NOT include Discord mentions, commands, or AI prefixes\n"
         f"- Sound spontaneous and conversational, not scripted"
    ),
    MessagesPlaceholder(variable_name="recent_history"),
        ("user", f"Generate a natural conversation starter that {initiator_bot_name} would say to get a discussion going. Consider any recent conversation context, but feel free to start something completely new if more appropriate.")
    ])

# Enhanced conversation initiator selection using full character prompts
def select_conversation_initiator_intelligently(recent_history):
    """
    Uses LLM with full character descriptions to decide which character should initiate a new conversation.
    """
    try:
        # Create enhanced initiator selection prompt using full character descriptions
        character_descriptions = ""
        for char_name in ["Peter", "Brian", "Stewie"]:
            if char_name in CHARACTER_PROMPTS:
                full_description = get_character_description(char_name)
                character_descriptions += f"\n=== {char_name.upper()} GRIFFIN ===\n{full_description}\n"
        
        initiator_selection_prompt = ChatPromptTemplate.from_messages([
            ("system",
             f"You are deciding which Family Guy character should start a new conversation in Discord. Use the detailed character profiles below to determine who would most naturally initiate a new discussion.\n\n"
             f"{character_descriptions}\n"
             f"INITIATOR SELECTION FACTORS:\n"
             f"1. **Character Personality**: Based on the detailed descriptions, who is most likely to spontaneously start conversations?\n"
             f"2. **Recent Activity Balance**: Who hasn't spoken recently and should get a chance?\n"
             f"3. **Topic Continuation**: Based on recent conversation, who might have follow-up thoughts or new ideas?\n"
             f"4. **Natural Conversation Flow**: Who would realistically break a silence or start fresh?\n"
             f"5. **Character Dynamics**: Consider each character's natural tendency to initiate discussions\n\n"
             f"CHARACTER TENDENCIES:\n"
             f"- Peter: Spontaneous, random outbursts, childlike enthusiasm for sharing thoughts\n"
             f"- Brian: Intellectual discussions, current events, wants to show off knowledge\n"
             f"- Stewie: Evil schemes to discuss, scientific observations, sophisticated commentary\n\n"
             f"RESPONSE FORMAT: Respond with ONLY the character name: 'Peter', 'Brian', or 'Stewie'"
            ),
            ("user", "Recent conversation analysis:\n{conversation_context}\n\nBased on the detailed character profiles and recent activity, who should naturally initiate the next conversation?")
        ])
        
        # Format recent history with analysis
        history_text = ""
        speaker_count = {"Peter": 0, "Brian": 0, "Stewie": 0}
        
        if recent_history:
            for msg in recent_history[-8:]:  # Last 8 messages for better context
                if isinstance(msg, HumanMessage):
                    history_text += f"Human: {msg.content}\n"
                elif isinstance(msg, AIMessage):
                    speaker = msg.name.title() if hasattr(msg, 'name') and msg.name else "Bot"
                    if speaker in speaker_count:
                        speaker_count[speaker] += 1
                    history_text += f"{speaker}: {msg.content}\n"
        
        if not history_text:
            history_text = "No recent conversation history"
        
        # Calculate who's been least active
        least_active = min(speaker_count, key=speaker_count.get)
        most_active = max(speaker_count, key=speaker_count.get)
        
        conversation_context = f"""
RECENT CONVERSATION HISTORY:
{history_text}

ACTIVITY ANALYSIS:
- Speaker frequency: Peter ({speaker_count['Peter']}), Brian ({speaker_count['Brian']}), Stewie ({speaker_count['Stewie']})
- Least active character: {least_active} (should be prioritized for balance)
- Most active character: {most_active}

CONTEXT FOR DECISION:
- Who would naturally want to start a new conversation based on their personality?
- Who deserves more speaking time based on recent activity?
- What type of conversation starter would be most natural given recent topics?
        """
        
        initiator_chain = initiator_selection_prompt | shared_llm
        selected_initiator = initiator_chain.invoke({"conversation_context": conversation_context})
        
        selected_initiator = clean_llm_response(selected_initiator).strip()
        
        if selected_initiator in BOT_CONFIGS:
            print(f"🎭 Enhanced Initiator Coordinator: Selected {selected_initiator} to start new conversation")
            print(f"   ⚖️ Activity balance: Peter({speaker_count['Peter']}), Brian({speaker_count['Brian']}), Stewie({speaker_count['Stewie']})")
            print(f"   🎯 Least active: {least_active}")
            return selected_initiator
        else:
            print(f"🎭 Enhanced initiator selection failed with '{selected_initiator}', using random selection")
            return None
            
    except Exception as e:
        print(f"🎭 Error in enhanced intelligent initiator selection: {e}")
        return None

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
        # Character names with full names as prefixes
        "Peter Griffin:", "Brian Griffin:", "Stewie Griffin:",
        "Peter:", "Brian:", "Stewie:", # Character names as prefixes
        "Peter: @Brian Griffin:", "Brian: @Peter Griffin:", "Stewie: @Brian Griffin:",
        "Peter: @Stewie Griffin:", "Stewie: @Peter Griffin:", "Brian: @Stewie Griffin:",
        # Additional character name variations
        "Peter Griffin said:", "Brian Griffin said:", "Stewie Griffin said:",
        "Peter said:", "Brian said:", "Stewie said:",
        "Peter responds:", "Brian responds:", "Stewie responds:",
        "Peter Griffin responds:", "Brian Griffin responds:", "Stewie Griffin responds:"
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

    # Additional cleanup for character name patterns that might appear mid-text
    import re
    # Remove patterns like "Peter Griffin: " at the start of lines
    cleaned_text = re.sub(r'^(Peter Griffin|Brian Griffin|Stewie Griffin|Peter|Brian|Stewie):\s*', '', cleaned_text, flags=re.IGNORECASE)
    
    # Remove quotation marks if the entire response is wrapped in quotes
    if cleaned_text.startswith('"') and cleaned_text.endswith('"') and cleaned_text.count('"') == 2:
        cleaned_text = cleaned_text[1:-1].strip()

    return cleaned_text

# --- RAG Components ---
# vectorstore = None # Removed
# embeddings = None # Removed

# CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH_ORCHESTRATOR", "/app/chroma_db") # Removed
RAG_RETRIEVER_API_URL = os.getenv("RAG_RETRIEVER_API_URL", "http://rag-retriever:5005/retrieve")
RAG_CRAWLER_API_URL = os.getenv("RAG_CRAWLER_API_URL", "http://rag-crawler:5009")

def retrieve_context(query, num_results=3):
    """
    Retrieves relevant context by calling the RAG Retriever microservice.
    """
    if not RAG_RETRIEVER_API_URL:
        print("Orchestrator - ERROR: RAG_RETRIEVER_API_URL not configured. Cannot retrieve context.")
        return ""

    payload = {
        "query": query,
        "num_results": num_results
    }
    
    try:
        print(f"Orchestrator - Requesting context from RAG Retriever: {RAG_RETRIEVER_API_URL} for query: '{query[:50]}...'")
        response = requests.post(RAG_RETRIEVER_API_URL, json=payload, timeout=30) # 30-second timeout
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        
        response_data = response.json()
        context = response_data.get("context", "")
        docs_found = response_data.get("documents_found", 0)
        
        if context:
            print(f"Orchestrator - Retrieved context ({docs_found} docs) from RAG Retriever for query '{query[:50]}...': {context[:100]}...")
        else:
            print(f"Orchestrator - No relevant context found by RAG Retriever for query: '{query[:50]}...' (Docs found: {docs_found})")
        return context
        
    except requests.exceptions.Timeout:
        print(f"Orchestrator - ERROR: Timeout connecting to RAG Retriever at {RAG_RETRIEVER_API_URL}")
        print(traceback.format_exc())
        return ""
    except requests.exceptions.ConnectionError:
        print(f"Orchestrator - ERROR: Connection error with RAG Retriever at {RAG_RETRIEVER_API_URL}. Is the service running?")
        print(traceback.format_exc())
        return ""
    except requests.exceptions.RequestException as e:
        print(f"Orchestrator - ERROR: Failed to retrieve context from RAG Retriever: {e}")
        print(traceback.format_exc())
        return ""
    except Exception as e:
        print(f"Orchestrator - ERROR: An unexpected error occurred while retrieving context: {e}")
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

    try:
        # --- RAG: Retrieve context for the current user query ---
        retrieved_context = retrieve_context(user_query)

        # --- Single Response Generation (Natural Conversation Flow) ---
        current_turn += 1
        print(f"\n--- Generating Response for Turn {current_turn} ---")

        next_speaker_name = None
        recent_llm_history = conversation_history_for_llm[-MAX_CHAT_HISTORY_MESSAGES:]
        last_speaker_name_in_history = None
        mentioned_bots = []

        if recent_llm_history:
            last_message_llm = recent_llm_history[-1]
            last_speaker_name_in_history = last_message_llm.name if hasattr(last_message_llm, 'name') else None

            for bot_name, config in BOT_CONFIGS.items():
                if config["mention"] in user_query:
                    mentioned_bots.append(bot_name)
                    print(f"Found direct mention to {bot_name} in user query")

            if mentioned_bots:
                eligible_mentioned = [bot for bot in mentioned_bots if not last_speaker_name_in_history or bot.lower() != last_speaker_name_in_history.lower()]
                if eligible_mentioned:
                    next_speaker_name = random.choice(eligible_mentioned)
                    print(f"🎯 Direct mention selection: {next_speaker_name} (from mentions: {mentioned_bots})")
                else:
                    next_speaker_name = random.choice(mentioned_bots)
                    print(f"🎯 Direct mention selection (all were last speaker, so picking one): {next_speaker_name}")
            else:
                print("🤖 No direct mentions found, using Conversation Coordinator for intelligent selection...")
                llm_selected_speaker = select_next_speaker_intelligently(
                    conversation_history_for_llm=recent_llm_history,
                    current_message=user_query,
                    mentioned_bots=mentioned_bots,
                    last_speaker_name=last_speaker_name_in_history,
                    current_turn=current_turn,
                    retrieved_context=retrieved_context
                )
                if llm_selected_speaker:
                    next_speaker_name = llm_selected_speaker
                    print(f"🧠 LLM Coordinator selected: {next_speaker_name}")
                else:
                    # FALLBACK: Use rule-based selection if LLM fails
                    print("⚠️ LLM Coordinator failed, using fallback rule-based selection...")
                    if current_turn == 1 and initiator_bot_name: # Ensure initiator_bot_name is available
                        next_speaker_name = initiator_bot_name
                        print(f"🔄 Fallback (Turn 1): Using initiator bot: {next_speaker_name}")
                    else:
                        eligible_bots = [name for name in BOT_CONFIGS.keys() if not last_speaker_name_in_history or name.lower() != last_speaker_name_in_history.lower()]
                        if not eligible_bots: # If all bots were the last speaker (e.g. only 1 bot active)
                            eligible_bots = list(BOT_CONFIGS.keys())
                        if eligible_bots: # Ensure there's someone to pick
                            next_speaker_name = random.choice(eligible_bots)
                            print(f"🔄 Fallback: Random selection from eligible bots: {next_speaker_name}")
                        else: # Should not happen with BOT_CONFIGS populated
                            print("ERROR: No eligible bots to select as next speaker!")
                            return jsonify({"error": "No eligible bots to select"}), 500

        else: # No conversation history (recent_llm_history is empty)
            # This means it's the very first message of a new session, or history was cleared
            # Check for mentions in the very first user query
            for bot_name, config in BOT_CONFIGS.items():
                if config["mention"] in user_query:
                    mentioned_bots.append(bot_name)
            
            if mentioned_bots:
                next_speaker_name = mentioned_bots[0] # First mentioned bot responds
                print(f"🎯 No history, using directly mentioned bot: {next_speaker_name}")
            elif initiator_bot_name: # Fallback to the bot that initiated this request from Discord
                next_speaker_name = initiator_bot_name
                print(f"🔄 No history or mentions, using initiator bot: {next_speaker_name}")
            else: # Absolute fallback if no initiator (e.g. direct API call without initiator)
                next_speaker_name = random.choice(list(BOT_CONFIGS.keys()))
                print(f"🔄 No history, mentions, or initiator, using random bot: {next_speaker_name}")

        if not next_speaker_name: # Final safety net
            print("ERROR: next_speaker_name could not be determined. Defaulting to a random bot.")
            next_speaker_name = random.choice(list(BOT_CONFIGS.keys()))

        current_speaker_name = next_speaker_name
        current_speaker_config = BOT_CONFIGS[current_speaker_name]
        # current_speaker_mention = current_speaker_config["mention"] # Not used directly here

        print(f"Current speaker: {current_speaker_name}")

        # Convert conversation history to LangChain message objects for centralized LLM
        # Use the recent_llm_history slice here as well
        chat_history_messages = []
        for msg in recent_llm_history: # recent_llm_history will be empty if it's the first message
            if isinstance(msg, HumanMessage):
                chat_history_messages.append(HumanMessage(content=msg.content))
            elif isinstance(msg, AIMessage):
                chat_history_messages.append(AIMessage(content=msg.content, name=msg.name))

        # Prepare mention context
        mention_context = f"""Available character mentions:
{chr(10).join([f"{name}: {config['mention']}" for name, config in BOT_CONFIGS.items()])}

Use these exact mention strings when referring to other characters in your response.
"""

        # Generate response using centralized LLM
        retries = 0
        while retries < MAX_RETRIES:
            try:
                print(f"Orchestrator generating {current_speaker_name}'s response using quality-controlled generation (attempt {retries + 1}/{MAX_RETRIES})...")
                response_text = generate_character_response_with_quality_control(
                    character_name=current_speaker_name,
                    conversation_history=chat_history_messages, # Pass the sliced (possibly empty) history
                    mention_context=mention_context,
                    input_text="Continue the conversation.", # This might need to be the actual user_query for the first turn.
                    retrieved_context=retrieved_context,
                    human_user_display_name=human_user_display_name
                )
                print(f"{current_speaker_name}'s centralized LLM generated: {response_text[:50]}...")
                break
            except Exception as e:
                retries += 1
                if retries == MAX_RETRIES:
                    # Add to dead letter queue before raising
                    if dlq: # Ensure dlq is initialized
                        dlq.add_message(
                            MessageType.LLM_REQUEST,
                            {
                                "character_name": current_speaker_name,
                                "conversation_history": [msg.dict() if hasattr(msg, 'dict') else str(msg) for msg in chat_history_messages],
                                "mention_context": mention_context,
                                "retrieved_context": retrieved_context
                            },
                            str(e),
                            current_speaker_name
                        )
                    raise # Re-raise the exception to be caught by the main try-except block
                print(f"Attempt {retries} failed, retrying in {2 ** retries} seconds...")
                time.sleep(2 ** retries)

        print(f"{current_speaker_name}'s final response: {response_text[:50]}...")

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

        # Add retry logic for Discord message sending
        retries = 0
        discord_payload = {
            "bot_name": current_speaker_name,
            "message_content": response_text,
            "channel_id": channel_id
        }
        while retries < MAX_RETRIES:
            try:
                print(f"Orchestrator instructing {current_speaker_name} to send to Discord (attempt {retries + 1}/{MAX_RETRIES})...")
                discord_response = requests.post(current_speaker_config["discord_send_api"], json=discord_payload, timeout=API_TIMEOUT)
                discord_response.raise_for_status()
                print(f"Successfully sent {current_speaker_name}'s response to Discord")
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                retries += 1
                if retries == MAX_RETRIES:
                    # Add to dead letter queue before raising
                    dlq.add_message(
                        MessageType.DISCORD_MESSAGE,
                        discord_payload,
                        str(e),
                        current_speaker_name
                    )
                    raise
                print(f"Attempt {retries} failed, retrying in {2 ** retries} seconds...")
                time.sleep(2 ** retries)  # Exponential backoff

        # Conversation continues naturally - no artificial ending
        print(f"Response generated successfully. Conversation continues naturally...")

        # Check for organic conversation opportunities after this response
        # This allows the coordinator to detect natural conversation endpoints
        try:
            # Small delay to allow the message to be processed and stored
            threading.Thread(target=lambda: _delayed_organic_check(channel_id), daemon=True).start()
        except Exception as e:
            print(f"Error scheduling organic conversation check: {e}")

        return jsonify({"status": "Response generated successfully", "turns": current_turn, "conversation_session_id": active_conversation_session_id, "speaker": current_speaker_name}), 200

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

def _delayed_organic_check(channel_id):
    """
    Delayed check for follow-up and organic conversation opportunities after a conversation response.
    Runs in a separate thread to avoid blocking the main orchestrator response.
    """
    try:
        # Wait for the configured delay to ensure the message has been stored
        time.sleep(FOLLOW_UP_DELAY_SECONDS)
        
        # First, check for immediate follow-up opportunities (more aggressive)
        if organic_coordinator.should_start_follow_up_conversation(channel_id):
            print(f"🔄 Post-Response Check: Detected opportunity for follow-up conversation")
            success = organic_coordinator.initiate_follow_up_conversation(channel_id)
            if success:
                print(f"🔄 Post-Response Check: Successfully started follow-up conversation")
                return  # Don't check for organic if we started a follow-up
            else:
                print(f"🔄 Post-Response Check: Failed to start follow-up conversation")
        
        # If no follow-up was triggered, check for organic conversation opportunities
        if organic_coordinator.should_start_organic_conversation(channel_id):
            print(f"🌱 Post-Response Check: Detected opportunity for organic conversation")
            success = organic_coordinator.initiate_organic_conversation(channel_id)
            if success:
                print(f"🌱 Post-Response Check: Successfully started organic conversation")
            else:
                print(f"🌱 Post-Response Check: Failed to start organic conversation")
        else:
            print(f"🌱 Post-Response Check: No follow-up or organic conversation needed")
            
    except Exception as e:
        print(f"🔄 Post-Response Check: Error during delayed check: {e}")
        print(traceback.format_exc())

# Global to track last crawl time (will be loaded from MongoDB)
# last_crawl_timestamp = None # No longer needed as a simple global, loaded from DB

def schedule_daily_conversations():
    """
    OLD SCHEDULER FUNCTION - REPLACED BY ORGANIC CONVERSATION COORDINATOR
    This function has been replaced by the OrganicConversationCoordinator class
    which provides more natural, context-driven conversation initiation.
    """
    pass  # Function removed - see OrganicConversationCoordinator

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

# --- Health Check Endpoint ---
@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint for load balancer."""
    try:
        # Check database connectivity
        mongo_client.admin.command('ping')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check RAG Retriever Service status (optional, simple ping if retriever had a health endpoint)
    rag_retriever_status = "not_checked" 
    try:
        # Example: pinging the retriever's health endpoint if it had one
        # health_url = RAG_RETRIEVER_API_URL.replace("/retrieve", "/health") 
        # rag_response = requests.get(health_url, timeout=5)
        # if rag_response.status_code == 200:
        #     rag_retriever_status = "healthy"
        # else:
        #     rag_retriever_status = f"unhealthy_code_{rag_response.status_code}"
        # For now, just confirm the URL is set
        if RAG_RETRIEVER_API_URL:
            rag_retriever_status = "configured"
        else:
            rag_retriever_status = "not_configured"

    except Exception as e:
        rag_retriever_status = f"error_checking: {str(e)}"

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        # "embeddings_model": "loaded" if 'embeddings_model' in globals() else "not_loaded", # Removed
        # "vector_store": "loaded" if 'vector_store' in globals() else "not_loaded" # Removed
        "rag_retriever_service": rag_retriever_status
    })

@app.route('/crawl/trigger', methods=['POST'])
def trigger_rag_crawl():
    """Trigger RAG crawling via the RAG Crawler microservice."""
    try:
        # Get crawl parameters from request
        data = request.json or {}
        
        # Prepare payload for crawler service
        crawler_payload = {
            "start_url": data.get("start_url", FANDOM_WIKI_START_URL),
            "max_pages": int(data.get("max_pages", FANDOM_WIKI_MAX_PAGES)),
            "delay": int(data.get("delay", FANDOM_WIKI_CRAWL_DELAY))
        }
        
        print(f"Orchestrator - Triggering RAG crawl via crawler service: {RAG_CRAWLER_API_URL}/crawl/start")
        
        # Call the RAG crawler service
        response = requests.post(
            f"{RAG_CRAWLER_API_URL}/crawl/start",
            json=crawler_payload,
            timeout=30
        )
        response.raise_for_status()
        
        crawler_response = response.json()
        
        return jsonify({
            "message": "RAG crawl triggered successfully",
            "status": "initiated",
            "crawler_response": crawler_response,
            "timestamp": datetime.now().isoformat()
        }), 202
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "RAG Crawler service is not available",
            "status": "service_unavailable",
            "crawler_url": RAG_CRAWLER_API_URL
        }), 503
        
    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Timeout connecting to RAG Crawler service",
            "status": "timeout"
        }), 504
        
    except Exception as e:
        print(f"Orchestrator - Error triggering RAG crawl: {e}")
        print(traceback.format_exc())
        return jsonify({
            "error": f"Failed to trigger RAG crawl: {str(e)}",
            "status": "failed"
        }), 500

@app.route('/crawl/status', methods=['GET'])
def get_rag_crawl_status():
    """Get RAG crawl status from the RAG Crawler microservice."""
    try:
        print(f"Orchestrator - Getting RAG crawl status from: {RAG_CRAWLER_API_URL}/crawl/status")
        
        response = requests.get(
            f"{RAG_CRAWLER_API_URL}/crawl/status",
            timeout=10
        )
        response.raise_for_status()
        
        crawler_status = response.json()
        
        return jsonify({
            "orchestrator_status": "healthy",
            "crawler_status": crawler_status,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": "RAG Crawler service is not available",
            "status": "service_unavailable",
            "crawler_url": RAG_CRAWLER_API_URL
        }), 503
        
    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Timeout connecting to RAG Crawler service",
            "status": "timeout"
        }), 504
        
    except Exception as e:
        print(f"Orchestrator - Error getting RAG crawl status: {e}")
        return jsonify({
            "error": f"Failed to get RAG crawl status: {str(e)}",
            "status": "failed"
        }), 500

# Fine-Tuning System API Endpoints

@app.route('/rate_response', methods=['POST'])
def rate_response():
    """
    Endpoint for users to rate character responses.
    Expected JSON: {
        "character_name": "Peter|Brian|Stewie",
        "response_text": "The response to rate",
        "rating": 1-5,
        "feedback": "Optional feedback text",
        "conversation_context": "Optional context"
    }
    """
    try:
        if not prompt_fine_tuner:
            return jsonify({"error": "Fine-tuning system not available"}), 503
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["character_name", "response_text", "rating"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        character_name = data["character_name"]
        response_text = data["response_text"]
        rating = data["rating"]
        feedback = data.get("feedback", "")
        conversation_context = data.get("conversation_context", "")
        user_id = data.get("user_id", "api_user")
        
        # Validate character name
        if character_name not in ["Peter", "Brian", "Stewie"]:
            return jsonify({"error": "Invalid character_name. Must be Peter, Brian, or Stewie"}), 400
        
        # Validate rating
        if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be a number between 1 and 5"}), 400
        
        # Record the rating
        rating_id = prompt_fine_tuner.record_rating(
            character_name=character_name,
            response_text=response_text,
            rating=rating,
            feedback=feedback,
            user_id=user_id,
            conversation_context=conversation_context
        )
        
        if rating_id:
            return jsonify({
                "success": True,
                "rating_id": rating_id,
                "message": f"Rating recorded for {character_name}"
            })
        else:
            return jsonify({"error": "Failed to record rating"}), 500
            
    except Exception as e:
        print(f"Error in rate_response endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/optimization_report', methods=['GET'])
def get_optimization_report():
    """
    Get optimization status and performance metrics for all characters.
    Query params: ?days=7 (optional, defaults to 7 days)
    """
    try:
        if not prompt_fine_tuner:
            return jsonify({"error": "Fine-tuning system not available"}), 503
        
        days = int(request.args.get('days', 7))
        
        reports = {}
        for character in ["Peter", "Brian", "Stewie"]:
            reports[character] = prompt_fine_tuner.get_performance_report(character, days)
        
        return jsonify({
            "optimization_reports": reports,
            "period_days": days,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in optimization_report endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/prompt_performance', methods=['GET'])
def get_prompt_performance():
    """
    Get detailed performance metrics for a specific character.
    Query params: ?character=Peter&days=7
    """
    try:
        if not prompt_fine_tuner:
            return jsonify({"error": "Fine-tuning system not available"}), 503
        
        character = request.args.get('character')
        days = int(request.args.get('days', 30))
        
        if not character or character not in ["Peter", "Brian", "Stewie"]:
            return jsonify({"error": "Invalid or missing character parameter"}), 400
        
        # Get performance report
        report = prompt_fine_tuner.get_performance_report(character, days)
        
        # Get prompt versions history
        versions = list(prompt_fine_tuner.prompt_versions_collection.find(
            {"character_name": character},
            sort=[("version", -1)]
        ).limit(10))
        
        # Convert ObjectId to string for JSON serialization
        for version in versions:
            version["_id"] = str(version["_id"])
            if "created_at" in version:
                version["created_at"] = version["created_at"].isoformat()
        
        return jsonify({
            "character": character,
            "performance_report": report,
            "prompt_versions": versions,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in prompt_performance endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/trigger_optimization', methods=['POST'])
def trigger_manual_optimization():
    """
    Manually trigger prompt optimization for a character.
    Expected JSON: {"character_name": "Peter|Brian|Stewie"}
    """
    try:
        if not prompt_fine_tuner:
            return jsonify({"error": "Fine-tuning system not available"}), 503
        
        data = request.get_json()
        character_name = data.get("character_name")
        
        if not character_name or character_name not in ["Peter", "Brian", "Stewie"]:
            return jsonify({"error": "Invalid character_name"}), 400
        
        # Get recent ratings for optimization
        recent_ratings = list(prompt_fine_tuner.ratings_collection.find(
            {"character_name": character_name},
            sort=[("timestamp", -1)],
            limit=MIN_RATINGS_FOR_OPTIMIZATION
        ))
        
        if len(recent_ratings) < 5:  # Need at least 5 ratings
            return jsonify({
                "error": f"Not enough ratings for optimization. Need at least 5, have {len(recent_ratings)}"
            }), 400
        
        # Trigger optimization
        success = prompt_fine_tuner.optimize_prompt(character_name, recent_ratings)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Optimization triggered for {character_name}",
                "new_version": prompt_fine_tuner.get_current_prompt_version(character_name)
            })
        else:
            return jsonify({"error": "Optimization failed"}), 500

    except Exception as e:
        print(f"Error in trigger_optimization endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/fine_tuning_stats', methods=['GET'])
def get_fine_tuning_stats():
    """Get overall fine-tuning system statistics."""
    try:
        if not prompt_fine_tuner:
            return jsonify({"error": "Fine-tuning system not available"}), 503
        
        stats = {}
        
        for character in ["Peter", "Brian", "Stewie"]:
            # Count total ratings
            total_ratings = prompt_fine_tuner.ratings_collection.count_documents(
                {"character_name": character}
            )
            
            # Count recent ratings (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            recent_ratings = prompt_fine_tuner.ratings_collection.count_documents({
                "character_name": character,
                "timestamp": {"$gte": week_ago}
            })
            
            # Get average rating
            pipeline = [
                {"$match": {"character_name": character}},
                {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}}
            ]
            avg_result = list(prompt_fine_tuner.ratings_collection.aggregate(pipeline))
            avg_rating = avg_result[0]["avg_rating"] if avg_result else None
            
            # Count prompt versions
            version_count = prompt_fine_tuner.prompt_versions_collection.count_documents(
                {"character_name": character}
            )
            
            stats[character] = {
                "total_ratings": total_ratings,
                "recent_ratings_7d": recent_ratings,
                "average_rating": round(avg_rating, 2) if avg_rating else None,
                "prompt_versions": version_count,
                "current_version": prompt_fine_tuner.get_current_prompt_version(character)
            }
        
        return jsonify({
            "system_stats": stats,
            "configuration": {
                "fine_tuning_enabled": FINE_TUNING_ENABLED,
                "quality_control_enabled": QUALITY_CONTROL_ENABLED,
                "optimization_threshold": OPTIMIZATION_THRESHOLD,
                "min_ratings_for_optimization": MIN_RATINGS_FOR_OPTIMIZATION,
                "ab_test_percentage": AB_TEST_PERCENTAGE,
                "quality_control_min_rating": QUALITY_CONTROL_MIN_RATING
            },
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in fine_tuning_stats endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/quality_control_status', methods=['GET'])
def get_quality_control_status():
    """
    Endpoint to get the current quality control configuration and statistics.
    """
    try:
        # Get quality control statistics from the database
        if prompt_fine_tuner:
            quality_control_stats = {}
            
            # Count ratings by user type to see quality control activity
            for character in ["Peter", "Brian", "Stewie"]:
                char_stats = {
                    "quality_control_accepted": prompt_fine_tuner.ratings_collection.count_documents({
                        "character_name": character,
                        "user_id": "quality_control_llm_assessment",
                        "feedback": {"$regex": "Quality Control Approved"}
                    }),
                    "quality_control_rejected": prompt_fine_tuner.ratings_collection.count_documents({
                        "character_name": character,
                        "user_id": "quality_control_llm_assessment", 
                        "feedback": {"$regex": "Quality Control Rejected"}
                    })
                }
                
                # Calculate acceptance rate
                total_qc = char_stats["quality_control_accepted"] + char_stats["quality_control_rejected"]
                if total_qc > 0:
                    char_stats["acceptance_rate"] = round(char_stats["quality_control_accepted"] / total_qc * 100, 1)
                else:
                    char_stats["acceptance_rate"] = None
                
                quality_control_stats[character] = char_stats
        else:
            quality_control_stats = "Fine-tuning system not available"
        
        return jsonify({
            "configuration": {
                "enabled": QUALITY_CONTROL_ENABLED,
                "min_rating_threshold": QUALITY_CONTROL_MIN_RATING,
                "max_retries": QUALITY_CONTROL_MAX_RETRIES
            },
            "statistics": quality_control_stats,
            "generated_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"Error in quality_control_status endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/organic_conversation_status', methods=['GET'])
def get_organic_conversation_status():
    """
    Get the current status and configuration of the Enhanced Organic Conversation Coordinator.
    """
    try:
        # Get recent follow-up and organic conversation activity
        now = datetime.now()
        recent_cutoff = now - timedelta(hours=24)
        
        # Count recent follow-up conversations (marked by quick succession)
        recent_conversations = list(conversations_collection.find({
            "timestamp": {"$gte": recent_cutoff}
        }).sort("timestamp", 1))
        
        follow_up_count = 0
        organic_count = 0
        
        # Analyze conversation patterns to identify follow-ups vs organic
        for i in range(1, len(recent_conversations)):
            prev_msg = recent_conversations[i-1]
            curr_msg = recent_conversations[i]
            
            # If both are bot messages within follow-up timeframe, likely a follow-up
            if (prev_msg.get("role") == "assistant" and 
                curr_msg.get("role") == "assistant" and
                prev_msg.get("name") != curr_msg.get("name")):
                
                time_diff = (curr_msg["timestamp"] - prev_msg["timestamp"]).total_seconds()
                if time_diff <= MIN_TIME_BETWEEN_FOLLOW_UPS:
                    follow_up_count += 1
                else:
                    organic_count += 1
        
        return jsonify({
            "status": "active",
            "configuration": {
                "follow_up_conversations_enabled": ENABLE_FOLLOW_UP_CONVERSATIONS,
                "follow_up_delay_seconds": FOLLOW_UP_DELAY_SECONDS,
                "min_time_between_follow_ups": MIN_TIME_BETWEEN_FOLLOW_UPS,
                "conversation_silence_threshold_minutes": CONVERSATION_SILENCE_THRESHOLD_MINUTES,
                "min_time_between_organic_conversations": MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS
            },
            "recent_activity_24h": {
                "follow_up_conversations": follow_up_count,
                "organic_conversations": organic_count,
                "total_bot_messages": len([msg for msg in recent_conversations if msg.get("role") == "assistant"])
            },
            "coordinator_state": {
                "last_follow_up_attempt": organic_coordinator.last_follow_up_attempt.isoformat() if organic_coordinator.last_follow_up_attempt else None,
                "last_organic_attempt": organic_coordinator.last_organic_attempt.isoformat() if organic_coordinator.last_organic_attempt else None
            },
            "features": {
                "character_specific_triggers": True,
                "intelligent_character_selection": True,
                "rag_enhanced_starters": True,
                "quality_control_integration": True,
                "self_orchestration": True,
                "timing_management": True
            },
            "timestamp": now.isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error getting organic conversation status: {e}")
        return jsonify({
            "error": f"Failed to get organic conversation status: {str(e)}",
            "status": "error"
        }), 500

# --- Enhanced Conversation Coordinator using Full Character Prompts ---
def create_enhanced_coordinator_prompt():
    """Create conversation coordinator prompt using the detailed character descriptions."""
    
    # Extract the full character descriptions from existing prompts
    character_descriptions = ""
    for char_name in ["Peter", "Brian", "Stewie"]:
        if char_name in CHARACTER_PROMPTS:
            # Get the system message content which contains the detailed character description
            full_description = get_character_description(char_name)
            character_descriptions += f"\n=== {char_name.upper()} GRIFFIN ===\n{full_description}\n"
    
    return ChatPromptTemplate.from_messages([
        ("system",
         f"You are the Conversation Coordinator for Family Guy characters in a Discord chat. Your job is to analyze the conversation and determine which character should respond next to create the most natural, engaging conversation flow.\n\n"
         f"You have access to detailed character profiles below. Use these to make intelligent decisions about who would naturally respond to different topics and situations.\n"
         f"{character_descriptions}\n"
         f"COORDINATOR DECISION FACTORS:\n"
         f"1. **Topic Relevance**: Based on the detailed character descriptions above, who would naturally be most interested in or triggered by this topic?\n"
         f"2. **Character Dynamics**: Consider the relationships and conflicts described in the character profiles\n"
         f"3. **Speech Patterns**: Who would naturally have something to say based on their communication style?\n"
         f"4. **Personality Triggers**: What would make each character want to jump into the conversation?\n"
         f"5. **Conversation Balance**: Avoid same character speaking twice unless it's very natural\n"
         f"6. **Character State**: Consider if someone made a mistake (Brian corrects), someone's being pretentious (Stewie mocks), etc.\n\n"
         f"PRIORITY RULES:\n"
         f"- If someone is directly mentioned (@character), they MUST respond (override your decision)\n"
         f"- Use the detailed personality and speech pattern information to predict natural reactions\n"
         f"- Consider who hasn't spoken recently for balance\n"
         f"- Think about realistic conversation dynamics between these specific characters\n\n"
         f"RESPONSE FORMAT: Respond with ONLY the character name: 'Peter', 'Brian', or 'Stewie'"
        ),
        ("user", "Conversation context:\n{conversation_analysis}\n\nWho should respond next? Answer with ONLY the character name (Peter, Brian, or Stewie):")
    ])

conversation_coordinator_prompt = create_enhanced_coordinator_prompt()
conversation_coordinator_chain = conversation_coordinator_prompt | shared_llm

def select_next_speaker_intelligently(conversation_history_for_llm, current_message, mentioned_bots, last_speaker_name, current_turn, retrieved_context=""):
    """
    Uses an enhanced LLM coordinator with full character descriptions and RAG context to intelligently select who should respond next.
    Returns the selected character name or None if LLM selection fails.
    """
    try:
        # Format conversation history for the coordinator
        history_text = ""
        recent_messages = conversation_history_for_llm[-8:] if len(conversation_history_for_llm) > 8 else conversation_history_for_llm
        
        # Track speaker frequency for balance
        speaker_count = {"Peter": 0, "Brian": 0, "Stewie": 0}
        
        for i, msg in enumerate(recent_messages):
            if isinstance(msg, HumanMessage):
                history_text += f"Human: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                speaker = msg.name.title() if hasattr(msg, 'name') and msg.name else "Bot"
                if speaker in speaker_count:
                    speaker_count[speaker] += 1
                history_text += f"{speaker}: {msg.content}\n"
        
        # Calculate who's been least active (for balance)
        least_active = min(speaker_count, key=speaker_count.get)
        most_active = max(speaker_count, key=speaker_count.get)
        
        # 🔍 RAG-ENHANCED TOPIC ANALYSIS
        # Get additional context about the conversation topic from Family Guy wiki
        rag_context = ""
        if not retrieved_context:
            # If no context was passed, retrieve it specifically for coordinator decision-making
            print("🔍 RAG Coordinator: Retrieving Family Guy universe context for topic analysis...")
            rag_context = retrieve_context(current_message, num_results=2)
        else:
            rag_context = retrieved_context
        
        # Analyze RAG context for character relevance
        rag_analysis = ""
        if rag_context:
            context_lower = rag_context.lower()
            
            # Look for character-specific information in the retrieved context
            if any(term in context_lower for term in ['peter griffin', 'peter', 'fat man', 'pawtucket patriot', 'chicken fight']):
                rag_analysis += "RAG context contains Peter-related information. "
            if any(term in context_lower for term in ['brian griffin', 'brian', 'dog', 'writer', 'liberal', 'martini']):
                rag_analysis += "RAG context contains Brian-related information. "
            if any(term in context_lower for term in ['stewie griffin', 'stewie', 'baby', 'evil', 'time machine', 'british']):
                rag_analysis += "RAG context contains Stewie-related information. "
                
            # Look for topic-specific expertise in retrieved context
            if any(term in context_lower for term in ['science', 'invention', 'technology', 'experiment', 'physics']):
                rag_analysis += "Scientific/technical topics in context - Stewie's expertise area. "
            if any(term in context_lower for term in ['book', 'literature', 'politics', 'culture', 'philosophy']):
                rag_analysis += "Intellectual/cultural topics in context - Brian's expertise area. "
            if any(term in context_lower for term in ['tv', 'television', 'beer', 'food', 'chicken', 'random']):
                rag_analysis += "Simple/entertainment topics in context - Peter's interest area. "
        
        # Enhanced topic analysis using character-specific keywords
        topic_analysis = ""
        message_lower = current_message.lower()
        
        # Peter's interests: simple, crude, entertainment, food, beer, random
        peter_keywords = ['tv', 'television', 'food', 'beer', 'eat', 'hungry', 'pawtucket', 'chicken', 'funny', 'hehe', 'random', 'weird', 'freakin', 'holy crap', 'bird', 'surfin bird']
        peter_score = sum(1 for word in peter_keywords if word in message_lower)
        
        # Brian's interests: intellectual, pretentious, literary, political
        brian_keywords = ['book', 'literature', 'philosophy', 'politics', 'society', 'culture', 'art', 'intellectual', 'profound', 'meaning', 'existence', 'writer', 'novel', 'actually', 'pretentious', 'wine', 'sophisticated']
        brian_score = sum(1 for word in brian_keywords if word in message_lower)
        
        # Stewie's interests: science, technology, evil plans, sophisticated language
        stewie_keywords = ['science', 'invention', 'technology', 'experiment', 'plan', 'device', 'machine', 'robot', 'laser', 'genius', 'physics', 'chemistry', 'engineering', 'evil', 'world domination', 'blast', 'deuce', 'confound']
        stewie_score = sum(1 for word in stewie_keywords if word in message_lower)
        
        if peter_score > 0:
            topic_analysis += f"Peter-relevant topics detected (score: {peter_score}): Simple/entertainment content. "
        if brian_score > 0:
            topic_analysis += f"Brian-relevant topics detected (score: {brian_score}): Intellectual/cultural content. "
        if stewie_score > 0:
            topic_analysis += f"Stewie-relevant topics detected (score: {stewie_score}): Scientific/technological content. "
        
        # Format mentioned characters
        mentioned_text = ", ".join(mentioned_bots) if mentioned_bots else "None"
        
        # Create comprehensive conversation analysis with RAG enhancement
        conversation_analysis = f"""
RECENT CONVERSATION HISTORY:
{history_text}

CURRENT MESSAGE ANALYSIS:
- Message: "{current_message}"
- Last speaker: {last_speaker_name or "None"}
- Turn number: {current_turn}
- Directly mentioned: {mentioned_text}

SPEAKER ACTIVITY ANALYSIS:
- Recent activity count: Peter ({speaker_count['Peter']}), Brian ({speaker_count['Brian']}), Stewie ({speaker_count['Stewie']})
- Least active character: {least_active}
- Most active character: {most_active}

KEYWORD-BASED TOPIC ANALYSIS:
{topic_analysis if topic_analysis else "General conversation - no specific character triggers detected"}

RAG-ENHANCED CONTEXT ANALYSIS:
{rag_analysis if rag_analysis else "No specific Family Guy universe context retrieved"}

FAMILY GUY UNIVERSE KNOWLEDGE:
{rag_context[:500] + "..." if len(rag_context) > 500 else rag_context if rag_context else "No relevant Family Guy wiki context available"}

CHARACTER REACTION PREDICTIONS:
- Would Peter relate to this based on his personality and the context?
- Would Brian want to correct/analyze this based on his intellectual nature?
- Would Stewie be triggered to respond based on his interests and ego?
- Does the Family Guy universe context suggest any character has special knowledge/connection to this topic?
- Who would naturally have the strongest reaction considering both personality and background knowledge?
        """
        
        # Call the enhanced coordinator LLM
        print("🧠 RAG-Enhanced Conversation Coordinator: Analyzing with full character profiles + Family Guy universe knowledge...")
        coordinator_response = conversation_coordinator_chain.invoke({
            "conversation_analysis": conversation_analysis
        })
        
        # Clean and validate the response
        selected_character = clean_llm_response(coordinator_response).strip()
        
        # Improve parsing - extract character name from potentially detailed response
        # Look for character names in the response
        response_lower = selected_character.lower()
        if 'peter' in response_lower:
            selected_character = 'Peter'
        elif 'brian' in response_lower:
            selected_character = 'Brian'
        elif 'stewie' in response_lower:
            selected_character = 'Stewie'
        
        # Ensure the response is a valid character name
        if selected_character in BOT_CONFIGS:
            print(f"🎭 RAG-Enhanced Coordinator: Selected {selected_character} based on detailed analysis")
            print(f"   📊 Topic relevance: {topic_analysis if topic_analysis else 'General conversation'}")
            print(f"   🔍 RAG insights: {rag_analysis if rag_analysis else 'No specific universe context'}")
            print(f"   ⚖️ Speaker balance: Peter({speaker_count['Peter']}), Brian({speaker_count['Brian']}), Stewie({speaker_count['Stewie']})")
            return selected_character
        else:
            print(f"🤖 RAG-Enhanced Coordinator: Invalid selection '{selected_character}', falling back to rule-based selection")
            return None
            
    except Exception as e:
        print(f"🤖 RAG-Enhanced Coordinator: Error during intelligent selection: {e}")
        print(traceback.format_exc())
        return None

# Function to generate conversation starters using the enhanced character-specific prompt
def generate_conversation_starter(initiator_bot_name, recent_history):
    """Generate a conversation starter using the full character description and RAG context."""
    try:
        # 🔍 RAG-ENHANCED STARTER GENERATION
        # Retrieve some general Family Guy context to inspire conversation starters
        rag_context = ""
        if recent_history:
            # Create a query from recent conversation to get relevant context
            recent_topics = []
            for msg in recent_history[-3:]:  # Last 3 messages
                if isinstance(msg, (HumanMessage, AIMessage)):
                    recent_topics.append(msg.content)
            
            if recent_topics:
                query_for_rag = " ".join(recent_topics)
                print(f"🔍 RAG Starter: Retrieving context for conversation inspiration based on recent topics...")
                rag_context = retrieve_context(query_for_rag, num_results=2)
            else:
                # If no recent topics, get general Family Guy context
                print(f"🔍 RAG Starter: Retrieving general Family Guy context for inspiration...")
                rag_context = retrieve_context(f"{initiator_bot_name} Griffin Family Guy", num_results=2)
        else:
            # No recent history, get character-specific context
            print(f"🔍 RAG Starter: Retrieving {initiator_bot_name}-specific context for starter inspiration...")
            rag_context = retrieve_context(f"{initiator_bot_name} Griffin Family Guy", num_results=2)
        
        starter_prompt = create_starter_generation_prompt(initiator_bot_name)
        starter_chain = starter_prompt | shared_llm
        
        # Enhance recent history with RAG context
        enhanced_history = recent_history.copy() if recent_history else []
        if rag_context:
            # Add RAG context as a system-like message for inspiration
            rag_inspiration = HumanMessage(content=f"[FAMILY GUY UNIVERSE CONTEXT FOR INSPIRATION: {rag_context[:300]}...]")
            enhanced_history.append(rag_inspiration)
        
        generated_starter = starter_chain.invoke({
            "recent_history": enhanced_history
        }).strip()
        
        if generated_starter and rag_context:
            print(f"🔍 RAG Starter: Generated starter with Family Guy universe inspiration: '{generated_starter[:50]}...'")
        elif generated_starter:
            print(f"📝 Generated starter without RAG context: '{generated_starter[:50]}...'")
        
        return clean_llm_response(generated_starter) if generated_starter else None
    except Exception as e:
        print(f"Error generating conversation starter for {initiator_bot_name}: {e}")
        print(traceback.format_exc())
        return None

# --- Organic Conversation Coordinator ---
class OrganicConversationCoordinator:
    """
    Manages organic conversation initiation based on context and natural flow rather than rigid schedules.
    Enhanced to handle follow-up conversations where other bots naturally join in.
    """
    
    def __init__(self):
        self.last_organic_attempt = None
        self.last_follow_up_attempt = None
        self.weekly_crawl_check_interval = 24 * 60 * 60  # Check for weekly crawl every 24 hours
        self.last_crawl_check = None
    
    def should_start_follow_up_conversation(self, channel_id):
        """
        Determines if a follow-up conversation should be started after a recent bot response.
        This is more aggressive than organic conversations and looks for immediate opportunities.
        """
        try:
            if not ENABLE_FOLLOW_UP_CONVERSATIONS:
                return False
                
            now = datetime.now()
            
            # Check minimum time between follow-up attempts
            if self.last_follow_up_attempt:
                time_since_last = (now - self.last_follow_up_attempt).total_seconds()
                if time_since_last < MIN_TIME_BETWEEN_FOLLOW_UPS:
                    print(f"🔄 Follow-up Coordinator: Too soon since last follow-up ({time_since_last:.1f}s < {MIN_TIME_BETWEEN_FOLLOW_UPS}s)")
                    return False
            
            # Get the last few messages to analyze for follow-up opportunities
            recent_messages = list(conversations_collection.find({
                "channel_id": channel_id
            }).sort("timestamp", -1).limit(5))
            
            if not recent_messages:
                return False
            
            # Check if the last message was from a bot (not a user)
            last_message = recent_messages[0]
            if last_message.get("role") != "assistant":
                print(f"🔄 Follow-up Coordinator: Last message was from user, not suitable for follow-up")
                return False
            
            # Check if the last message was very recent (within last 30 seconds)
            time_since_last_message = (now - last_message["timestamp"]).total_seconds()
            if time_since_last_message > 30:
                print(f"🔄 Follow-up Coordinator: Last bot message too old ({time_since_last_message:.1f}s)")
                return False
            
            # Analyze if the conversation content suggests other characters would want to respond
            if self._analyze_for_follow_up_triggers(recent_messages):
                print(f"🔄 Follow-up Coordinator: Content analysis suggests follow-up conversation would be natural")
                return True
            
            return False
            
        except Exception as e:
            print(f"🔄 Follow-up Coordinator: Error in should_start_follow_up_conversation: {e}")
            return False

    def should_start_organic_conversation(self, channel_id):
        """
        Determines if an organic conversation should be started based on intelligent criteria.
        """
        try:
            now = datetime.now()
            
            # Get recent conversation activity
            recent_cutoff = now - timedelta(minutes=CONVERSATION_SILENCE_THRESHOLD_MINUTES)
            recent_messages = list(conversations_collection.find({
                "channel_id": channel_id,
                "timestamp": {"$gte": recent_cutoff}
            }).sort("timestamp", -1))
            
            # Don't start if there's been recent activity
            if recent_messages:
                print(f"🤖 Organic Coordinator: Recent activity detected, no need for organic conversation")
                return False
            
            # Check minimum time between organic attempts
            if self.last_organic_attempt:
                time_since_last = (now - self.last_organic_attempt).total_seconds() / 60
                if time_since_last < MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS:
                    print(f"🤖 Organic Coordinator: Too soon since last attempt ({time_since_last:.1f} min < {MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS} min)")
                    return False
            
            # Get longer conversation history for context analysis
            history_cutoff = now - timedelta(hours=2)  # Last 2 hours for context
            conversation_history = list(conversations_collection.find({
                "channel_id": channel_id,
                "timestamp": {"$gte": history_cutoff}
            }).sort("timestamp", -1).limit(10))
            
            # Analyze conversation patterns for organic triggers
            if self._analyze_conversation_for_organic_triggers(conversation_history):
                print(f"🤖 Organic Coordinator: Conversation analysis suggests organic conversation would be beneficial")
                return True
            
            # If it's been silent for a while, consider starting something
            if not recent_messages:
                last_message = conversations_collection.find_one(
                    {"channel_id": channel_id},
                    sort=[("timestamp", -1)]
                )
                
                if last_message:
                    silence_duration = (now - last_message["timestamp"]).total_seconds() / 60
                    if silence_duration > CONVERSATION_SILENCE_THRESHOLD_MINUTES:
                        print(f"🤖 Organic Coordinator: {silence_duration:.1f} minutes of silence, considering organic conversation")
                        return True
                
            return False
            
        except Exception as e:
            print(f"🤖 Organic Coordinator: Error in should_start_organic_conversation: {e}")
            return False
    
    def _analyze_for_follow_up_triggers(self, recent_messages):
        """
        Analyzes recent messages to determine if other characters would naturally want to respond.
        This is more aggressive than organic triggers and looks for immediate reaction opportunities.
        """
        if not recent_messages:
            return False
        
        last_message = recent_messages[0]
        last_speaker = last_message.get("name", "").lower()
        last_content = last_message.get("content", "").lower()
        
        # Character-specific follow-up triggers
        follow_up_triggers = {
            "peter": {
                # Other characters likely to respond to Peter
                "brian_triggers": [
                    "stupid", "dumb", "idiot", "wrong", "beer", "tv", "chicken", "surfin bird",
                    "pawtucket", "lois", "meg", "intellectual", "smart", "book"
                ],
                "stewie_triggers": [
                    "baby", "diaper", "stupid", "fat man", "lois", "mother", "family guy",
                    "invention", "plan", "evil", "world"
                ]
            },
            "brian": {
                # Other characters likely to respond to Brian
                "peter_triggers": [
                    "intellectual", "smart", "book", "culture", "politics", "sophisticated",
                    "pretentious", "dog", "writer", "novel", "philosophy", "wine"
                ],
                "stewie_triggers": [
                    "intellectual", "culture", "book", "philosophy", "science", "invention",
                    "sophisticated", "british", "genius", "plan"
                ]
            },
            "stewie": {
                # Other characters likely to respond to Stewie
                "peter_triggers": [
                    "baby", "evil", "plan", "invention", "british", "smart", "genius",
                    "mother", "lois", "family", "stupid", "fat man"
                ],
                "brian_triggers": [
                    "intellectual", "genius", "science", "invention", "philosophy", "culture",
                    "sophisticated", "british", "plan", "evil"
                ]
            }
        }
        
        # Check if the last message contains triggers that would make other characters want to respond
        if last_speaker in follow_up_triggers:
            triggers = follow_up_triggers[last_speaker]
            
            for responding_character, trigger_words in triggers.items():
                if any(trigger in last_content for trigger in trigger_words):
                    print(f"🔄 Follow-up Analysis: {last_speaker}'s message contains triggers for {responding_character}: {[t for t in trigger_words if t in last_content]}")
                    return True
        
        # Look for direct questions or statements that invite responses
        response_inviting_patterns = [
            "what do you think", "don't you think", "right?", "you know?", "isn't that",
            "what about", "remember when", "speaking of", "by the way", "actually",
            "question", "wonder", "curious", "thoughts?", "opinions?", "agree?",
            "hehehe", "hehe", "funny", "ridiculous", "stupid", "smart", "brilliant"
        ]
        
        if any(pattern in last_content for pattern in response_inviting_patterns):
            print(f"🔄 Follow-up Analysis: Last message contains response-inviting patterns: {[p for p in response_inviting_patterns if p in last_content]}")
            return True
        
        # Look for controversial or debate-worthy statements
        controversial_topics = [
            "politics", "religion", "stupid", "smart", "wrong", "right", "best", "worst",
            "hate", "love", "better", "worse", "always", "never", "everyone", "nobody"
        ]
        
        if any(topic in last_content for topic in controversial_topics):
            print(f"🔄 Follow-up Analysis: Last message contains controversial topics that might spark responses")
            return True
        
        # Check message length - very short messages might not inspire follow-ups
        if len(last_content.strip()) < 20:
            print(f"🔄 Follow-up Analysis: Last message too short to inspire follow-ups")
            return False
        
        # Default: if we've gotten this far and the message is substantial, there's a chance for follow-up
        if len(last_content.strip()) > 50:
            print(f"🔄 Follow-up Analysis: Substantial message detected, moderate chance for follow-up")
            return True
        
        return False

    def _analyze_conversation_for_organic_triggers(self, conversation_history):
        """
        Analyzes recent conversation for patterns that suggest an organic conversation would be natural.
        """
        if not conversation_history:
            return False
        
        # Look for conversation endpoints or natural breaks
        recent_messages = conversation_history[:3]  # Last 3 messages
        
        for msg in recent_messages:
            content = msg.get("content", "").lower()
            
            # Look for conversation-ending phrases
            ending_phrases = [
                "see you later", "goodbye", "gotta go", "talk later", 
                "that's all", "anyway", "well", "ok then", "alright"
            ]
            
            if any(phrase in content for phrase in ending_phrases):
                print(f"🤖 Organic Coordinator: Detected conversation ending phrase in recent messages")
                return True
        
        # Look for incomplete thoughts or unresolved topics
        all_content = " ".join([msg.get("content", "") for msg in conversation_history])
        content_lower = all_content.lower()
        
        # Topics that might inspire follow-up conversations
        follow_up_triggers = [
            "question", "wonder", "think about", "reminds me", "speaking of",
            "by the way", "actually", "wait", "oh", "you know what"
        ]
        
        if any(trigger in content_lower for trigger in follow_up_triggers):
            print(f"🤖 Organic Coordinator: Detected potential follow-up conversation triggers")
            return True
        
        return False
    
    def initiate_follow_up_conversation(self, channel_id):
        """
        Initiates a follow-up conversation where another character responds to the recent bot message.
        """
        try:
            self.last_follow_up_attempt = datetime.now()
            print(f"🔄 Follow-up Coordinator: Initiating follow-up conversation at {datetime.now().strftime('%H:%M:%S')}")
            
            # Get recent conversation history
            recent_history = []
            recent_messages = []
            try:
                all_channel_messages = list(conversations_collection.find({"channel_id": channel_id}).sort("timestamp", -1).limit(10))
                recent_messages = all_channel_messages
                recent_history_raw = list(reversed(all_channel_messages))
                for msg_doc in recent_history_raw:
                    if msg_doc["role"] == "user":
                        recent_history.append(HumanMessage(content=msg_doc["content"]))
                    elif msg_doc["role"] == "assistant":
                        recent_history.append(AIMessage(content=msg_doc["content"], name=msg_doc.get("name")))
            except PyMongoError as e:
                print(f"MongoDB error fetching recent history for follow-up conversation: {e}")
                return False

            if not recent_messages:
                print(f"🔄 Follow-up Coordinator: No recent messages found")
                return False
            
            # Determine which character should respond based on the last message
            last_message = recent_messages[0]
            last_speaker = last_message.get("name", "").lower()
            
            # Select a different character to respond (exclude the last speaker)
            available_characters = [name for name in BOT_CONFIGS.keys() if name.lower() != last_speaker]
            if not available_characters:
                print(f"🔄 Follow-up Coordinator: No other characters available to respond")
                return False
            
            # Use intelligent selection to pick the best responder
            print("🔄 Follow-up Coordinator: Using intelligent selection for follow-up responder...")
            follow_up_speaker = select_conversation_initiator_intelligently(recent_history)
            
            # If intelligent selection picks the same character, override it
            if follow_up_speaker and follow_up_speaker.lower() == last_speaker:
                follow_up_speaker = random.choice(available_characters)
                print(f"🔄 Follow-up Coordinator: Intelligent selection picked same character, overriding to: {follow_up_speaker}")
            elif not follow_up_speaker:
                follow_up_speaker = random.choice(available_characters)
                print(f"🔄 Follow-up Coordinator: Intelligent selection failed, using random: {follow_up_speaker}")
            else:
                print(f"🔄 Follow-up Coordinator: Intelligent selection chose: {follow_up_speaker}")
            
            follow_up_bot_config = BOT_CONFIGS[follow_up_speaker]
            
            # Create a follow-up prompt based on the last message
            last_content = last_message.get("content", "")
            follow_up_prompt = f"Respond to what {last_speaker} just said: \"{last_content}\""
            
            try:
                # Use the same session ID to continue the conversation
                current_session_id = last_message.get("conversation_session_id", str(uuid.uuid4()))
                initiate_payload = {
                    "user_query": follow_up_prompt,
                    "channel_id": channel_id,
                    "initiator_bot_name": follow_up_speaker,
                    "initiator_mention": follow_up_bot_config["mention"],
                    "human_user_display_name": None,
                    "is_new_conversation": False,
                    "conversation_session_id": current_session_id
                }
                
                response = requests.post(ORCHESTRATOR_API_URL, json=initiate_payload, timeout=120)
                response.raise_for_status()
                print(f"🔄 Follow-up Coordinator: Successfully initiated follow-up conversation with {follow_up_speaker}")
                return True
            except Exception as e:
                print(f"ERROR: Follow-up Coordinator: Failed to initiate follow-up conversation: {e}")
                return False
                
        except Exception as e:
            print(f"ERROR: Follow-up Coordinator: Critical error in initiate_follow_up_conversation: {e}")
            print(traceback.format_exc())
            return False

    def initiate_organic_conversation(self, channel_id):
        """
        Initiates an organic conversation using intelligent selection and RAG-enhanced starters.
        """
        try: # Outer try for the whole method
            self.last_organic_attempt = datetime.now()
            print(f"🌱 Organic Coordinator: Initiating organic conversation at {datetime.now().strftime('%H:%M:%S')}")
            
            recent_history = []
            try: # Inner try for MongoDB access
                all_channel_messages = list(conversations_collection.find({"channel_id": channel_id}).sort("timestamp", -1).limit(10))
                recent_history_raw = list(reversed(all_channel_messages))
                for msg_doc in recent_history_raw:
                    if msg_doc["role"] == "user":
                        recent_history.append(HumanMessage(content=msg_doc["content"]))
                    elif msg_doc["role"] == "assistant":
                        recent_history.append(AIMessage(content=msg_doc["content"], name=msg_doc.get("name")))
            except PyMongoError as e:
                print(f"MongoDB error fetching recent history for organic conversation: {e}")
                print(traceback.format_exc())
            # This inner try for MongoDB access intentionally does not return;
            # if it fails, recent_history will be empty, and the coordinator will proceed.

            print("🌱 Organic Coordinator: Using intelligent selection for conversation initiator...")
            initiator_bot_name = select_conversation_initiator_intelligently(recent_history)
            
            if not initiator_bot_name:
                initiator_bot_name = random.choice(list(BOT_CONFIGS.keys()))
                print(f"🌱 Organic Coordinator: Intelligent selection failed, using random fallback: {initiator_bot_name}")
            else:
                print(f"🌱 Organic Coordinator: Intelligent selection chose: {initiator_bot_name}")
            
            initiator_bot_config = BOT_CONFIGS[initiator_bot_name]
            
            conversation_starter_prompt = None
            try: # Inner try for starter generation
                print(f"🌱 Organic Coordinator: Generating organic conversation starter...")
                generated_starter = generate_conversation_starter(initiator_bot_name, recent_history)

                if generated_starter:
                    conversation_starter_prompt = generated_starter
                    print(f"🌱 Organic Coordinator: Generated organic starter: '{conversation_starter_prompt[:50]}...'")
                else:
                    conversation_starter_prompt = random.choice(INITIAL_CONVERSATION_PROMPTS)
                    print(f"🌱 Organic Coordinator: No dynamic starter generated. Falling back to static prompt: '{conversation_starter_prompt[:50]}...'")
            except Exception as e:
                print(f"ERROR: Organic Coordinator: Unexpected error generating starter: {e}. Falling back to static prompt.")
                print(traceback.format_exc())
                conversation_starter_prompt = random.choice(INITIAL_CONVERSATION_PROMPTS)

            try: # Inner try for orchestrator API call
                new_session_id = str(uuid.uuid4())
                initiate_payload = {
                    "user_query": conversation_starter_prompt,
                    "channel_id": channel_id,
                    "initiator_bot_name": initiator_bot_name,
                    "initiator_mention": initiator_bot_config["mention"],
                    "human_user_display_name": None,
                    "is_new_conversation": True,
                    "conversation_session_id": new_session_id
                }
                
                response = requests.post(ORCHESTRATOR_API_URL, json=initiate_payload, timeout=120)
                response.raise_for_status()
                print(f"🌱 Organic Coordinator: Successfully initiated organic conversation with session {new_session_id}")
                return True
            except requests.exceptions.Timeout:
                print(f"ERROR: Organic Coordinator Timeout: Failed to initiate conversation with orchestrator.")
                return False
            except requests.exceptions.ConnectionError:
                print(f"ERROR: Organic Coordinator Connection Error: Orchestrator API might be down.")
                return False
            except Exception as e: # Catch other exceptions for this specific block
                print(f"ERROR: Organic Coordinator: Unexpected error initiating conversation: {e}")
                print(traceback.format_exc())
                return False
                
        except Exception as e: # General except for the outer try block
            print(f"ERROR: Organic Coordinator: Critical error in initiate_organic_conversation: {e}")
            print(traceback.format_exc())
            return False
    
    # Removed check_weekly_crawl(self) method from OrganicConversationCoordinator

# Global organic coordinator instance
organic_coordinator = OrganicConversationCoordinator()

def organic_conversation_monitor():
    """
    Monitors for organic and follow-up conversation opportunities and manages background tasks.
    Much lighter than the old scheduler - focuses on natural conversation flow.
    """
    global DEFAULT_DISCORD_CHANNEL_ID, organic_coordinator
    
    print(f"🌱 Organic Conversation Monitor: Starting natural conversation monitoring...")
    print(f"   🔄 Follow-up conversations: {'Enabled' if ENABLE_FOLLOW_UP_CONVERSATIONS else 'Disabled'}")
    print(f"   ⏱️ Follow-up delay: {FOLLOW_UP_DELAY_SECONDS}s")
    print(f"   🕐 Min time between follow-ups: {MIN_TIME_BETWEEN_FOLLOW_UPS}s")
    
    check_interval = 30  # Check every 30 seconds for more responsive follow-ups
    
    while True:
        try: # Try for the main loop operations
            if DEFAULT_DISCORD_CHANNEL_ID:
                # First check for follow-up opportunities (more frequent and aggressive)
                if ENABLE_FOLLOW_UP_CONVERSATIONS and organic_coordinator.should_start_follow_up_conversation(DEFAULT_DISCORD_CHANNEL_ID):
                    print(f"🔄 Monitor: Follow-up conversation opportunity detected!")
                    success = organic_coordinator.initiate_follow_up_conversation(DEFAULT_DISCORD_CHANNEL_ID)
                    if success:
                        print(f"🔄 Monitor: Successfully started follow-up conversation")
                    else:
                        print(f"🔄 Monitor: Failed to start follow-up conversation")
                
                # Then check for organic opportunities (less frequent, for new conversations)
                elif organic_coordinator.should_start_organic_conversation(DEFAULT_DISCORD_CHANNEL_ID):
                    print(f"🌱 Monitor: Organic conversation opportunity detected!")
                    success = organic_coordinator.initiate_organic_conversation(DEFAULT_DISCORD_CHANNEL_ID)
                    if success:
                        print(f"🌱 Monitor: Successfully started organic conversation")
                    else:
                        print(f"🌱 Monitor: Failed to start organic conversation")
                else:
                    # Only log this occasionally to avoid spam
                    import time
                    if int(time.time()) % 300 == 0:  # Every 5 minutes
                        print(f"🌱 Monitor: No conversation opportunities at this time")
            else:
                print(f"ERROR: DEFAULT_DISCORD_CHANNEL_ID not configured, cannot monitor for conversations")
            
        except Exception as e: # Catch exceptions from the main loop operations
            print(f"ERROR: Conversation Monitor: Unexpected error in monitoring loop: {e}")
            print(traceback.format_exc())
        
        # Wait before next check - ensure this is outside the try-except for the main operations
        # so that the loop continues even if an error occurs in the try block.
        time.sleep(check_interval)

def validate_character_response(character_name, response_text):
    """
    Validates that a character response is appropriate and in-character.
    Returns (is_valid, corrected_response) tuple.
    """
    try:
        # Check for empty or too short responses
        if not response_text or len(response_text.strip()) < 3:
            return False, None
        
        # Check for character identity confusion (speaking as other characters)
        response_lower = response_text.lower()
        
        # Detect if character is speaking AS another character
        identity_violations = []
        if character_name == "Peter":
            if "as for me, brian" in response_lower or "speaking of me, brian" in response_lower:
                identity_violations.append("Peter speaking as Brian")
            if "as for me, stewie" in response_lower or "speaking of me, stewie" in response_lower:
                identity_violations.append("Peter speaking as Stewie")
        elif character_name == "Brian":
            if "as for me, peter" in response_lower or "speaking of me, peter" in response_lower:
                identity_violations.append("Brian speaking as Peter")
            if "as for me, stewie" in response_lower or "speaking of me, stewie" in response_lower:
                identity_violations.append("Brian speaking as Stewie")
        elif character_name == "Stewie":
            if "as for me, peter" in response_lower or "speaking of me, peter" in response_lower:
                identity_violations.append("Stewie speaking as Peter")
            if "as for me, brian" in response_lower or "speaking of me, brian" in response_lower:
                identity_violations.append("Stewie speaking as Brian")
        
        if identity_violations:
            print(f"⚠️ Identity violation detected for {character_name}: {identity_violations}")
            return False, None
        
        # Check for inappropriate length by character
        if character_name == "Peter" and len(response_text) > 500: # Reduced for Peter's style
            print(f"⚠️ Peter response too long: {len(response_text)} characters")
            return False, None
        elif character_name == "Brian" and len(response_text) > 1800:
            print(f"⚠️ Brian response too long: {len(response_text)} characters")
            return False, None
        elif character_name == "Stewie" and len(response_text) > 1800:
            print(f"⚠️ Stewie response too long: {len(response_text)} characters")
            return False, None
        
        # Check for vocabulary mismatch
        if character_name == "Peter":
            # Peter shouldn't use sophisticated words
            sophisticated_words = [
                "sophisticated", "intellectual", "erudite", "profoundly", 
                "philosophical", "contemplating", "astounding", "fascinating"
            ]
            for word in sophisticated_words:
                if word in response_lower:
                    print(f"⚠️ Peter using sophisticated word: {word}")
                    return False, None
        
        elif character_name == "Brian":
            # Brian should use intellectual language
            if len(response_text) > 50 and not any(word in response_lower for word in [
                "actually", "indeed", "quite", "rather", "certainly", "perhaps", "literature", "culture"
            ]):
                # This might be okay, but let's check if it's too simple for Brian
                simple_indicators = ["hehehe", "freakin", "awesome", "stupid"]
                if any(indicator in response_lower for indicator in simple_indicators):
                    print(f"⚠️ Brian response too simple")
                    return False, None
        
        elif character_name == "Stewie":
            # Stewie should have British mannerisms
            if len(response_text) > 30 and not any(phrase in response_lower for phrase in [
                "blast", "deuce", "what the", "indeed", "quite", "rather", "brilliant", "fool", "imbecile"
            ]):
                print(f"⚠️ Stewie response lacks British mannerisms")
                return False, None
        
        # Check for Cleveland confusion
        if "cleveland" in response_lower and "dog" in response_lower:
            print(f"⚠️ Cleveland/dog confusion detected")
            return False, None
        
        # Enhanced validation: Check for direct addressing of other characters
        # Characters should speak as themselves, not TO other characters directly
        import re
        direct_addressing_patterns = [
            r'\b(peter|brian|stewie|lois|meg|chris|quagmire|cleveland)\s*[,:]',  # "Peter," or "Brian:"
            r'@(peter|brian|stewie)',  # "@Peter" mentions
            r'\b(hey|hi|hello)\s+(peter|brian|stewie|lois|meg|chris)',  # "Hey Peter"
            r'\b(peter|brian|stewie|lois|meg|chris)\s+(you\b|your\b)',  # "Peter you" or "Brian your"
        ]
        
        for pattern in direct_addressing_patterns:
            if re.search(pattern, response_lower):
                # Allow self-reference (e.g., Brian talking about Brian is okay)
                match = re.search(pattern, response_lower)
                if match:
                    addressed_name = None
                    for group in match.groups():
                        if group and group.lower() in ['peter', 'brian', 'stewie', 'lois', 'meg', 'chris', 'quagmire', 'cleveland']:
                            addressed_name = group.lower()
                            break
                    
                    if addressed_name and addressed_name != character_name.lower():
                        print(f"⚠️ {character_name} directly addressing {addressed_name}: {match.group()}")
                        return False, None
        
        # Check for dialogue formatting that suggests multiple speakers
        dialogue_violations = [
            '"' in response_text and response_text.count('"') >= 2,  # Multiple quoted sections
            response_text.count(':') >= 2,  # Multiple colons suggesting dialogue
            '[' in response_text and ']' in response_text,  # Stage directions like [Brian looks at Peter]
            # Removed character_name prefix check since we clean those now
        ]
        
        if any(dialogue_violations):
            print(f"⚠️ {character_name} response contains dialogue formatting")
            return False, None
        
        # Check for mixed character conversation patterns
        # Look for patterns that suggest multiple characters speaking in one response
        mixed_conversation_patterns = [
            # Multiple character names followed by colons (dialogue format)
            r'(peter|brian|stewie|lois|meg|chris):\s*[^:]+\s*(peter|brian|stewie|lois|meg|chris):',
            # Character name followed by "said" or "says" (narrative format)
            r'(peter|brian|stewie|lois|meg|chris)\s+(said|says|replied|responded)',
            # Multiple instances of character names in conversational context
            r'(peter|brian|stewie)\s+.{10,50}\s+(peter|brian|stewie)\s+.{10,50}\s+(peter|brian|stewie)',
            # Conversation back-and-forth indicators
            r'(peter|brian|stewie).{5,30}(replied|responded|answered|said).{5,30}(peter|brian|stewie)',
            # Multiple quoted speech sections with character attribution
            r'"[^"]+"\s*(peter|brian|stewie).{0,20}"[^"]+"\s*(peter|brian|stewie)',
        ]
        
        for pattern in mixed_conversation_patterns:
            matches = re.findall(pattern, response_lower, re.IGNORECASE)
            if matches:
                # Check if it involves other characters (not just self-reference)
                for match in matches:
                    if isinstance(match, tuple):
                        involved_chars = [name.lower() for name in match if name]
                    else:
                        involved_chars = [match.lower()]
                    
                    # If multiple different characters are mentioned in conversation context
                    unique_chars = set(involved_chars)
                    if len(unique_chars) > 1 or (len(unique_chars) == 1 and list(unique_chars)[0] != character_name.lower()):
                        print(f"⚠️ {character_name} response contains mixed character conversation: {matches}")
                        return False, None
        
        # Check for narrative/descriptive text about multiple characters
        narrative_patterns = [
            # "Brian looks at Peter" type descriptions
            r'(peter|brian|stewie|lois|meg|chris)\s+(looks|turns|walks|goes|says|tells|asks)\s+(to|at|toward)?\s*(peter|brian|stewie|lois|meg|chris)',
            # "Peter and Brian" type multi-character descriptions
            r'(peter|brian|stewie)\s+and\s+(peter|brian|stewie)\s+(both|together|simultaneously)',
            # Scene descriptions with multiple characters
            r'(peter|brian|stewie).{10,50}(while|as|when)\s+(peter|brian|stewie)',
        ]
        
        for pattern in narrative_patterns:
            matches = re.findall(pattern, response_lower, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        involved_chars = [name.lower() for name in match if name and name.lower() in ['peter', 'brian', 'stewie', 'lois', 'meg', 'chris']]
                        unique_chars = set(involved_chars)
                        if len(unique_chars) > 1:
                            print(f"⚠️ {character_name} response contains multi-character narrative: {match}")
                            return False, None
        
        # Check for third-person self-reference (should speak in first person)
        third_person_patterns = [
            f'{character_name.lower()} thinks',
            f'{character_name.lower()} says',
            f'{character_name.lower()} looks',
            f'{character_name.lower()} feels',
            f'{character_name.lower()} walks',
            f'{character_name.lower()} goes',
            f'{character_name.lower()} responds',
            f'{character_name.lower()} replies',
            f'{character_name.lower()} turns to',
        ]
        
        for pattern in third_person_patterns:
            if pattern in response_lower:
                print(f"⚠️ {character_name} speaking in third person: {pattern}")
                return False, None
        
        # Response passes validation
        return True, response_text
        
    except Exception as e:
        print(f"⚠️ Error validating response: {e}")
        return True, response_text  # Allow response if validation fails

if __name__ == '__main__':
    # Try to connect to MongoDB with retries
    max_retries = 5
    initial_delay = 1
    
    print("Starting orchestrator initialization...")
    
    while True:
        if connect_to_mongodb(max_retries=max_retries, initial_delay=initial_delay):
            break
        print("Initial MongoDB connection attempts failed. Waiting 10 seconds before trying again...")
        time.sleep(10)
    
    try:
        # get_embeddings_model() # Initialize embeddings model on startup - Removed, orchestrator no longer loads this directly
        # initialize_vector_store() # Initialize or load vector store on startup - Removed
        
        # Initialize the fine-tuning system after MongoDB connection is established
        try:
            if mongo_client:
                prompt_fine_tuner = PromptFineTuner(mongo_client)
                print("🎯 Supervised Fine-Tuning System initialized successfully")
                print(f"   📊 Quality Control: {'Enabled' if QUALITY_CONTROL_ENABLED else 'Disabled'}")
                print(f"   🎯 Auto-Optimization: {'Enabled' if FINE_TUNING_ENABLED else 'Disabled'}")
                print(f"   🧪 A/B Testing: {AB_TEST_PERCENTAGE*100}% traffic for optimized prompts")
            else:
                print("⚠️ Warning: MongoDB client not available, fine-tuning system disabled")
                prompt_fine_tuner = None
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize fine-tuning system: {e}")
            prompt_fine_tuner = None
        
        # Start the retry worker thread
        threading.Thread(target=retry_worker, daemon=True).start()
        print("Dead letter queue retry worker thread started.")
        
        threading.Thread(target=run_flask_app, daemon=True).start()
        print("Orchestrator server thread started. Waiting for requests...")

        threading.Thread(target=organic_conversation_monitor, daemon=True).start()
        print("Organic conversation monitor thread started.")
        
        # Log follow-up conversation configuration
        print(f"🔄 Follow-up Conversations: {'Enabled' if ENABLE_FOLLOW_UP_CONVERSATIONS else 'Disabled'}")
        if ENABLE_FOLLOW_UP_CONVERSATIONS:
            print(f"   ⏱️ Follow-up delay: {FOLLOW_UP_DELAY_SECONDS}s")
            print(f"   🕐 Min time between follow-ups: {MIN_TIME_BETWEEN_FOLLOW_UPS}s")

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

