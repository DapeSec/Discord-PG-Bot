import os
import traceback
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from pymongo import MongoClient # For potential status checks, not core retrieval
from datetime import datetime
import hashlib

# Load environment variables
load_dotenv()

SERVICE_NAME = "RAGRetrieverService"

# KeyDB Cache Integration for query caching
try:
    from src.app.utils.cache import get_cache
    CACHE_AVAILABLE = True
    print(f"{SERVICE_NAME} - ✅ KeyDB cache utilities imported successfully")
except ImportError as e:
    print(f"{SERVICE_NAME} - ⚠️ Cache utilities not available: {e}. No query caching.")
    CACHE_AVAILABLE = False

app = Flask(__name__)

# --- Configuration ---
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/app/chroma_db") # Path inside the container
EMBEDDINGS_MODEL_NAME = os.getenv("EMBEDDINGS_MODEL_NAME", "all-MiniLM-L6-v2")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:adminpassword@mongodb:27017/?authSource=admin")
DB_NAME = os.getenv("MONGO_DB_NAME", "discord_bot_conversations")
CRAWL_STATUS_COLLECTION_NAME = "crawl_status"

# --- Global Variables for RAG Components ---
vectorstore = None
embeddings = None
mongo_client = None
db = None
crawl_status_collection = None

def get_mongo_connection():
    """Establishes and returns a MongoDB connection for status checking."""
    global mongo_client, db, crawl_status_collection
    if mongo_client is None:
        try:
            print(f"{SERVICE_NAME} - Attempting to connect to MongoDB for status checks...")
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            mongo_client.admin.command('ping') # Verify connection
            db = mongo_client[DB_NAME]
            crawl_status_collection = db[CRAWL_STATUS_COLLECTION_NAME]
            print(f"{SERVICE_NAME} - Successfully connected to MongoDB: {DB_NAME} for status checks.")
        except Exception as e:
            print(f"{SERVICE_NAME} - WARNING: Could not connect to MongoDB for status checks: {e}. Crawl status will be unavailable.")
            mongo_client = None
            db = None
            crawl_status_collection = None
    return crawl_status_collection

def get_embeddings_model():
    """Initializes and returns the SentenceTransformer embeddings model."""
    global embeddings
    if embeddings is None:
        try:
            print(f"{SERVICE_NAME} - Loading embeddings model: {EMBEDDINGS_MODEL_NAME}...")
            embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDINGS_MODEL_NAME)
            print(f"{SERVICE_NAME} - Embeddings model loaded successfully.")
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: Fatal error loading embeddings model: {e}")
            print(traceback.format_exc())
            # This is a critical error, the service cannot function without embeddings.
            # In a real-world scenario, you might want to exit or have a more robust error handling.
            raise RuntimeError(f"Failed to load embeddings model: {e}")
    return embeddings

def initialize_vector_store():
    """Initializes or loads the Chroma vector store (read-only)."""
    global vectorstore
    if vectorstore is not None:
        return vectorstore

    print(f"{SERVICE_NAME} - Attempting to load Chroma DB from {CHROMA_DB_PATH}...")
    try:
        current_embeddings = get_embeddings_model() # Ensure embeddings are loaded first
        if not current_embeddings:
            # This case should ideally be handled by get_embeddings_model raising an error
            print(f"{SERVICE_NAME} - ERROR: Embeddings model not available, cannot initialize vector store.")
            vectorstore = None
            return None

        # Create the directory if it doesn't exist
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)

        vectorstore = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=current_embeddings)
        
        try:
            count = vectorstore._collection.count()
            if count == 0:
                print(f"{SERVICE_NAME} - WARNING: Chroma DB loaded from {CHROMA_DB_PATH} but is empty. Retrieval will yield no results until the RAG Crawler runs.")
                print(f"{SERVICE_NAME} - This is normal for a fresh installation. The service will work once content is crawled.")
            else:
                print(f"{SERVICE_NAME} - Chroma DB loaded successfully from {CHROMA_DB_PATH} with {count} documents.")
        except Exception as count_error:
            print(f"{SERVICE_NAME} - WARNING: Could not count documents in vector store: {count_error}")
            print(f"{SERVICE_NAME} - Vector store initialized but document count unavailable.")
            
    except Exception as e:
        print(f"{SERVICE_NAME} - ERROR: Critical error loading Chroma DB from {CHROMA_DB_PATH}: {e}")
        print(traceback.format_exc())
        print(f"{SERVICE_NAME} - RAG retrieval will be unavailable. Ensure the DB path is correct and the RAG Crawler has populated the database.")
        
        # Instead of raising an error, let's try to create a new empty vector store
        try:
            print(f"{SERVICE_NAME} - Attempting to create a new empty vector store...")
            os.makedirs(CHROMA_DB_PATH, exist_ok=True)
            vectorstore = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=current_embeddings)
            print(f"{SERVICE_NAME} - Created new empty vector store. Service will work once content is crawled.")
        except Exception as create_error:
            print(f"{SERVICE_NAME} - FATAL: Could not create new vector store: {create_error}")
            vectorstore = None
            # Don't raise error - let service start but mark as unhealthy
            return None

    return vectorstore

@app.route('/retrieve', methods=['POST'])
def retrieve_context_api():
    """API endpoint to retrieve context from the vector store with caching."""
    # Ensure vector store is initialized before each request
    current_vectorstore = initialize_vector_store()
    
    if current_vectorstore is None:
        print(f"{SERVICE_NAME} - Error: Vector store not initialized. Cannot retrieve context.")
        return jsonify({"error": "Vector store not initialized. RAG retriever may be starting or encountered an issue."}), 503

    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request JSON"}), 400

    query = data.get('query')
    num_results = data.get('num_results', 3)
    
    try:
        num_results = int(num_results)
        if num_results <= 0:
            num_results = 3 # Default to 3 if invalid
    except ValueError:
        num_results = 3

    print(f"{SERVICE_NAME} - Received retrieval request for query: '{query[:50]}...' (num_results: {num_results})")

    # Check cache first if available
    cache_key = None
    if CACHE_AVAILABLE:
        try:
            # Create cache key from query and parameters
            query_hash = hashlib.md5(f"{query}:{num_results}".encode()).hexdigest()
            cache_key = f"query:{query_hash}"
            
            cache = get_cache("rag")
            cached_result = cache.get(cache_key)
            
            if cached_result:
                print(f"{SERVICE_NAME} - 🎯 Cache hit for query: '{query[:50]}...'")
                return jsonify(cached_result), 200
                
        except Exception as e:
            print(f"{SERVICE_NAME} - ⚠️ Cache check failed: {e}")

    try:
        if current_vectorstore._collection.count() == 0:
            print(f"{SERVICE_NAME} - Warning: Chroma DB is empty. Returning no context for query: '{query[:50]}...'")
            result = {"query": query, "context": "", "documents_found": 0, "message": "Vector store is empty."}
        else:
            docs_with_scores = current_vectorstore.similarity_search_with_score(query, k=num_results)
            
            context_parts = []
            retrieved_documents_info = []

            for doc, score in docs_with_scores:
                context_parts.append(doc.page_content)
                doc_info = {
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score) # Ensure score is JSON serializable
                }
                retrieved_documents_info.append(doc_info)
                
            context = "\n\n".join(context_parts)
            
            result = {
                "query": query,
                "context": context,
                "retrieved_documents": retrieved_documents_info,
                "documents_found": len(docs_with_scores),
                "cached": False
            }
            
            if context:
                print(f"{SERVICE_NAME} - Retrieved {len(docs_with_scores)} documents for query '{query[:50]}...'")
            else:
                print(f"{SERVICE_NAME} - No relevant context found for query: '{query[:50]}...'")

        # Cache the result if caching is available
        if CACHE_AVAILABLE and cache_key:
            try:
                cache = get_cache("rag")
                result["cached"] = False  # Mark as fresh result
                cache.set(cache_key, result, ttl=3600)  # Cache for 1 hour
                print(f"{SERVICE_NAME} - 💾 Cached result for query: '{query[:50]}...'")
            except Exception as e:
                print(f"{SERVICE_NAME} - ⚠️ Failed to cache result: {e}")
        
        return jsonify(result), 200

    except Exception as e:
        print(f"{SERVICE_NAME} - ERROR: Error during context retrieval for query '{query[:50]}...': {e}")
        print(traceback.format_exc())
        return jsonify({"error": f"Failed to retrieve context: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker and load balancers."""
    try:
        # Check vector store status
        current_vectorstore = initialize_vector_store()
        vectorstore_status = "initialized" if current_vectorstore else "not_initialized"
        
        # Check document count
        document_count = 0
        if current_vectorstore:
            try:
                document_count = current_vectorstore._collection.count()
            except Exception as e:
                print(f"{SERVICE_NAME} - Error getting document count: {e}")
        
        # Check cache status
        cache_status = "not_available"
        if CACHE_AVAILABLE:
            try:
                cache = get_cache("rag")
                test_result = cache.set("health_test", {"timestamp": datetime.now().isoformat()}, ttl=60)
                cache_status = "connected" if test_result else "connection_failed"
            except Exception as e:
                cache_status = f"error: {str(e)}"
        
        # Determine overall status
        status = "healthy" if current_vectorstore and document_count > 0 else "degraded"
        
        return jsonify({
            "status": status,
            "service": SERVICE_NAME,
            "timestamp": datetime.now().isoformat(),
            "vectorstore": {
                "status": vectorstore_status,
                "document_count": document_count,
                "embeddings_model": EMBEDDINGS_MODEL_NAME
            },
            "cache": {
                "status": cache_status,
                "available": CACHE_AVAILABLE
            }
        }), 200 if status == "healthy" else 503
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "service": SERVICE_NAME,
            "reason": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503


if __name__ == '__main__':
    print(f"--- Starting {SERVICE_NAME} ---")
    PORT = int(os.getenv("RAG_RETRIEVER_PORT", 5005)) # Default port 5005 for this service
    
    # Initialize components at startup
    # These will raise errors and stop startup if critical components fail to load
    try:
        get_mongo_connection() # For crawl status checks (non-critical)
        get_embeddings_model() # Must load for the service to work
        initialize_vector_store() # Try to load, but don't fail if empty
        print(f"{SERVICE_NAME} - Initialization complete.")
    except RuntimeError as e:
        print(f"{SERVICE_NAME} - FATAL: A critical error occurred during startup: {e}")
        print(f"{SERVICE_NAME} - Exiting due to failed initialization.")
        exit(1) # Exit if critical components cannot be initialized
    except Exception as e:
        print(f"{SERVICE_NAME} - WARNING: Non-critical error during startup: {e}")
        print(traceback.format_exc())
        print(f"{SERVICE_NAME} - Service will start but may have limited functionality.")

    print(f"{SERVICE_NAME} - Flask app starting on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False) 