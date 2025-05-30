from flask import Flask, request, jsonify
import os
import logging
import json
import redis
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import numpy as np
from datetime import datetime

# Service configuration
SERVICE_NAME = "RAG Retriever"
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Environment variables
PORT = int(os.getenv("RAG_RETRIEVER_PORT", 5007))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
EMBEDDINGS_MODEL_NAME = os.getenv("EMBEDDINGS_MODEL_NAME", "all-MiniLM-L6-v2")
REDIS_URL = os.getenv("REDIS_URL", "redis://keydb:6379")

# Global variables for services
chroma_client = None
collection = None
embeddings_model = None
redis_client = None

def get_embeddings_model():
    """Initializes and returns the SentenceTransformer embeddings model."""
    global embeddings_model
    if embeddings_model is None:
        try:
            print(f"{SERVICE_NAME} - Loading embeddings model: {EMBEDDINGS_MODEL_NAME}...")
            embeddings_model = SentenceTransformer(EMBEDDINGS_MODEL_NAME)
            print(f"{SERVICE_NAME} - Embeddings model loaded successfully.")
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: Fatal error loading embeddings model: {e}")
            print(traceback.format_exc())
            # This is a critical error, the service cannot function without embeddings.
            # In a real-world scenario, you might want to exit or have a more robust error handling.
            raise RuntimeError(f"Failed to load embeddings model: {e}")
    return embeddings_model

def initialize_vector_store():
    """Initializes or loads the Chroma vector store (read-only)."""
    global chroma_client, collection
    if chroma_client is not None:
        return chroma_client

    print(f"{SERVICE_NAME} - Attempting to load Chroma DB from {CHROMA_DB_PATH}...")
    
    try:
        current_embeddings = get_embeddings_model()
        if current_embeddings is None:
            print(f"{SERVICE_NAME} - ERROR: Embeddings model not available, cannot initialize vector store.")
            chroma_client = None
            collection = None
            return None

        # Create the directory if it doesn't exist
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)

        # Initialize ChromaDB client with persistent directory
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = chroma_client.get_or_create_collection("family_guy_docs")
        
        try:
            count = collection.count()
            if count == 0:
                print(f"{SERVICE_NAME} - WARNING: Chroma DB loaded from {CHROMA_DB_PATH} but is empty. Retrieval will yield no results until the RAG Crawler runs.")
            else:
                print(f"{SERVICE_NAME} - Successfully loaded Chroma DB: {count} documents available.")
        except Exception as count_error:
            print(f"{SERVICE_NAME} - Warning: Could not check document count: {count_error}")
    
    except Exception as e:
        print(f"{SERVICE_NAME} - Could not load existing vector store: {e}")
        try:
            print(f"{SERVICE_NAME} - Attempting to create a new empty vector store...")
            os.makedirs(CHROMA_DB_PATH, exist_ok=True)
            chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            collection = chroma_client.get_or_create_collection("family_guy_docs")
            print(f"{SERVICE_NAME} - Created new empty vector store. Service will work once content is crawled.")
        except Exception as create_error:
            print(f"{SERVICE_NAME} - FATAL: Could not create new vector store: {create_error}")
            chroma_client = None
            collection = None
            # Don't raise error - let service start but mark as unhealthy
            return None

    return chroma_client

def initialize_redis():
    """Initialize Redis client for caching"""
    global redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print(f"{SERVICE_NAME} - Connected to Redis for caching")
        return redis_client
    except Exception as e:
        print(f"{SERVICE_NAME} - Warning: Could not connect to Redis: {e}. Caching disabled.")
        redis_client = None
        return None

@app.route('/retrieve', methods=['POST'])
def retrieve_context_api():
    """Retrieve relevant context from the vector store."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query field'}), 400
        
        query = data['query']
        num_results = data.get('num_results', 5)
        
        print(f"{SERVICE_NAME} - Processing retrieval query: '{query[:50]}...' (max {num_results} results)")
        
        # Ensure vector store is initialized
        current_vectorstore = initialize_vector_store()
        if current_vectorstore is None:
            return jsonify({
                'error': 'Vector store not available',
                'context': '',
                'documents_found': 0
            }), 503
        
        # Check cache first if available
        cache_key = None
        if redis_client:
            try:
                import hashlib
                query_hash = hashlib.md5(f"{query}:{num_results}".encode()).hexdigest()
                cache_key = f"rag_query:{query_hash}"
                
                cached_result = redis_client.get(cache_key)
                
                if cached_result:
                    cached_data = json.loads(cached_result)
                    cached_data["cached"] = True
                    print(f"{SERVICE_NAME} - 🗲 Cache hit for query: '{query[:50]}...'")
                    return jsonify(cached_data), 200
                    
            except Exception as e:
                print(f"{SERVICE_NAME} - Cache lookup failed: {e}")

        try:
            if collection.count() == 0:
                print(f"{SERVICE_NAME} - Warning: Chroma DB is empty. Returning no context for query: '{query[:50]}...'")
                result = {"query": query, "context": "", "documents_found": 0, "message": "Vector store is empty."}
            else:
                # Query the collection
                query_embedding = embeddings_model.encode([query])
                results = collection.query(
                    query_embeddings=query_embedding.tolist(),
                    n_results=num_results,
                    include=['documents', 'distances', 'metadatas']
                )
                
                context_parts = []
                retrieved_documents_info = []
                
                documents = results.get('documents', [[]])[0]
                distances = results.get('distances', [[]])[0] 
                metadatas = results.get('metadatas', [[]])[0]
                
                for i, (doc, distance) in enumerate(zip(documents, distances)):
                    context_parts.append(doc)
                    doc_info = {
                        "content": doc[:200] + "..." if len(doc) > 200 else doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "score": float(distance) if distance is not None else 0.0
                    }
                    retrieved_documents_info.append(doc_info)
                
                context = "\n\n".join(context_parts)
                
                result = {
                    "query": query,
                    "context": context,
                    "retrieved_documents": retrieved_documents_info,
                    "documents_found": len(documents),
                    "cached": False
                }
                
                if context:
                    print(f"{SERVICE_NAME} - Retrieved {len(documents)} documents for query '{query[:50]}...'")
                else:
                    print(f"{SERVICE_NAME} - No relevant context found for query: '{query[:50]}...'")

            # Cache the result if caching is available
            if redis_client and cache_key:
                try:
                    result["cached"] = False  # Mark as fresh result
                    redis_client.set(cache_key, json.dumps(result), ex=3600)  # Cache for 1 hour
                    print(f"{SERVICE_NAME} - 💾 Cached result for query: '{query[:50]}...'")
                except Exception as e:
                    print(f"{SERVICE_NAME} - Cache storage failed: {e}")
            
            return jsonify(result), 200
            
        except Exception as e:
            print(f"{SERVICE_NAME} - Error during retrieval: {e}")
            return jsonify({
                'error': f'Retrieval failed: {str(e)}',
                'context': '',
                'documents_found': 0
            }), 500
            
    except Exception as e:
        print(f"{SERVICE_NAME} - Error processing request: {e}")
        return jsonify({'error': f'Request processing failed: {str(e)}'}), 500

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
                document_count = collection.count()
            except Exception as e:
                print(f"{SERVICE_NAME} - Error getting document count: {e}")
        
        # Check cache status
        cache_status = "not_available"
        if redis_client:
            try:
                test_data = json.dumps({"timestamp": datetime.now().isoformat()})
                test_result = redis_client.set("health_test", test_data, ex=60)
                cache_status = "connected" if test_result else "connection_failed"
            except Exception as e:
                cache_status = f"error: {str(e)}"
        
        # Determine overall status
        # Service is healthy if vector store is initialized, regardless of document count
        # An empty vector store is still functional - it just means no content has been crawled yet
        status = "healthy" if current_vectorstore else "degraded"
        
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
                "available": bool(redis_client)
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
    PORT = int(os.getenv("RAG_RETRIEVER_PORT", 5007)) # Default port 5007 for this service
    
    # Initialize components at startup
    # These will raise errors and stop startup if critical components fail to load
    try:
        initialize_redis() # Initialize Redis for caching (non-critical)
        get_embeddings_model() # Must load for the service to work
        initialize_vector_store() # Try to load, but don't fail if empty
        print(f"{SERVICE_NAME} - Initialization complete.")
    except RuntimeError as e:
        print(f"{SERVICE_NAME} - FATAL: A critical error occurred during startup: {e}")
        print(f"{SERVICE_NAME} - Exiting due to failed initialization.")
        exit(1) # Exit if critical components cannot be initialized
    except Exception as e:
        print(f"{SERVICE_NAME} - WARNING: Non-critical error during startup: {e}")
        print(f"{SERVICE_NAME} - Service will start but may have limited functionality.")

    print(f"{SERVICE_NAME} - Flask app starting on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False) 