#!/usr/bin/env python3
"""
RAG Crawler Service

A dedicated microservice for web scraping and vector database population.
Provides REST API endpoints for crawling operations and status monitoring.
Includes automatic crawling based on configurable intervals.
"""

import os
import time
import threading
import traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import redis
import json

# Import the existing crawler functionality
from .crawler import (
    SERVICE_NAME,
    get_redis_connection,
    update_crawl_status,
    get_embeddings_model,
    initialize_vector_store_for_crawl,
    crawl_and_process_documents,
    FANDOM_WIKI_START_URL,
    FANDOM_WIKI_MAX_PAGES,
    FANDOM_WIKI_CRAWL_DELAY,
    clear_visited_urls_from_redis,
    get_visited_urls_from_redis
)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://keydb:6379")

# Global variables
redis_client = None
crawl_thread = None
crawl_in_progress = False

def initialize_redis():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print(f"{SERVICE_NAME} - Connected to Redis")
        return redis_client
    except Exception as e:
        print(f"{SERVICE_NAME} - Warning: Could not connect to Redis: {e}")
        redis_client = None
        return None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the RAG Crawler service."""
    try:
        # Check Redis connection
        redis_status = "connected" if redis_client else "disconnected"
        
        # Check embeddings model
        try:
            get_embeddings_model()
            embeddings_status = "loaded"
        except Exception:
            embeddings_status = "not_loaded"
        
        # Check crawl status
        global crawl_in_progress
        service_status = "crawling" if crawl_in_progress else "idle"
        
        return jsonify({
            "service_name": SERVICE_NAME,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "crawl_status": service_status,
            "dependencies": {
                "redis": redis_status,
                "embeddings_model": embeddings_status
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "service_name": SERVICE_NAME,
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/crawl/start', methods=['POST'])
def start_crawl():
    """Start a new crawl operation."""
    global crawl_thread, crawl_in_progress
    
    if crawl_in_progress:
        return jsonify({
            "error": "Crawl already in progress",
            "status": "rejected"
        }), 409
    
    # Get crawl parameters from request
    data = request.json or {}
    start_url = data.get('start_url', FANDOM_WIKI_START_URL)
    max_pages = int(data.get('max_pages', FANDOM_WIKI_MAX_PAGES))
    delay = int(data.get('delay', FANDOM_WIKI_CRAWL_DELAY))
    
    try:
        # Validate parameters
        if max_pages <= 0 or max_pages > 10000:
            return jsonify({
                "error": "max_pages must be between 1 and 10000",
                "status": "rejected"
            }), 400
        
        if delay < 0 or delay > 60:
            return jsonify({
                "error": "delay must be between 0 and 60 seconds",
                "status": "rejected"
            }), 400
        
        # Start crawl in background thread
        crawl_thread = threading.Thread(
            target=_run_crawl_background,
            args=(start_url, max_pages, delay),
            daemon=True
        )
        crawl_thread.start()
        crawl_in_progress = True
        
        return jsonify({
            "message": "Crawl started successfully",
            "status": "started",
            "parameters": {
                "start_url": start_url,
                "max_pages": max_pages,
                "delay": delay
            },
            "timestamp": datetime.now().isoformat()
        }), 202
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to start crawl: {str(e)}",
            "status": "failed"
        }), 500

@app.route('/crawl/status', methods=['GET'])
def get_crawl_status():
    """Get the current crawl status."""
    global crawl_in_progress
    
    try:
        # Get visited URLs count for resume info
        visited_urls = get_visited_urls_from_redis()
        visited_count = len(visited_urls)
        
        # Get document count from vector store
        try:
            vectorstore = initialize_vector_store_for_crawl()
            doc_count = vectorstore._collection.count() if vectorstore else 0
        except:
            doc_count = "unknown"
        
        # Get status from Redis
        redis_conn = redis_client
        if redis_conn:
            status_key = f"crawl_status:{SERVICE_NAME}"
            status_data = redis_conn.hgetall(status_key)
            if status_data:
                details = json.loads(status_data.get("details", "{}"))
                return jsonify({
                    "service_name": SERVICE_NAME,
                    "crawl_in_progress": crawl_in_progress,
                    "resume_capability": {
                        "visited_urls_count": visited_count,
                        "documents_in_store": doc_count,
                        "can_resume": visited_count > 0 or doc_count > 0
                    },
                    "last_crawl": {
                        "timestamp": status_data.get("last_updated"),
                        "status": status_data.get("status"),
                        "pages_crawled": details.get("pages_crawled", 0),
                        "total_documents": details.get("total_documents", 0),
                        "error_message": details.get("error_message")
                    }
                }), 200
        
        # Fallback if no status found
        return jsonify({
            "service_name": SERVICE_NAME,
            "crawl_in_progress": crawl_in_progress,
            "resume_capability": {
                "visited_urls_count": visited_count,
                "documents_in_store": doc_count,
                "can_resume": visited_count > 0 or doc_count > 0
            },
            "last_crawl": None,
            "message": "No crawl status found"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get crawl status: {str(e)}",
            "service_name": SERVICE_NAME,
            "crawl_in_progress": crawl_in_progress
        }), 500

@app.route('/crawl/stop', methods=['POST'])
def stop_crawl():
    """Stop the current crawl operation."""
    global crawl_in_progress
    
    if not crawl_in_progress:
        return jsonify({
            "message": "No crawl in progress",
            "status": "not_running"
        }), 200
    
    # Note: This is a simple implementation. In a production system,
    # you'd want more sophisticated thread management and graceful shutdown.
    crawl_in_progress = False
    update_crawl_status("STOPPED_BY_USER")
    
    return jsonify({
        "message": "Crawl stop requested",
        "status": "stopping",
        "note": "Crawl will stop after current page completes"
    }), 200

@app.route('/vector_store/info', methods=['GET'])
def get_vector_store_info():
    """Get information about the vector store."""
    try:
        # Initialize vector store to get info
        vectorstore = initialize_vector_store_for_crawl()
        if vectorstore is not None:
            doc_count = vectorstore._collection.count()
            return jsonify({
                "vector_store": "ChromaDB",
                "document_count": doc_count,
                "status": "available",
                "path": os.getenv("CHROMA_DB_PATH", "/app/chroma_db")
            }), 200
        else:
            return jsonify({
                "vector_store": "ChromaDB",
                "status": "unavailable",
                "error": "Failed to initialize vector store"
            }), 503
            
    except Exception as e:
        return jsonify({
            "vector_store": "ChromaDB",
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/auto-crawl-status', methods=['GET'])
def get_auto_crawl_status():
    """Get auto-crawl configuration and status."""
    try:
        # Get last crawl info
        redis_conn = redis_client
        last_crawl_info = None
        next_auto_crawl = None
        
        if redis_conn:
            status_key = f"crawl_status:{SERVICE_NAME}"
            status_data = redis_conn.hgetall(status_key)
            if status_data:
                last_crawl_info = {
                    "timestamp": status_data.get("last_updated"),
                    "status": status_data.get("status"),
                    "details": json.loads(status_data.get("details", "{}"))
                }
                
                # Calculate next auto-crawl time
                if status_data.get("last_updated"):
                    try:
                        last_update = datetime.fromisoformat(status_data["last_updated"])
                        next_crawl_date = last_update + timedelta(days=int(os.getenv("AUTO_CRAWL_INTERVAL_DAYS", "30")))
                        next_auto_crawl = next_crawl_date.isoformat()
                    except Exception:
                        next_auto_crawl = None
        
        return jsonify({
            "auto_crawl_enabled": os.getenv("AUTO_CRAWL_ENABLED", "true").lower() == "true",
            "auto_crawl_interval_days": int(os.getenv("AUTO_CRAWL_INTERVAL_DAYS", "30")),
            "auto_crawl_check_interval_hours": int(os.getenv("AUTO_CRAWL_CHECK_INTERVAL_HOURS", "24")),
            "crawl_in_progress": crawl_in_progress,
            "last_crawl": last_crawl_info,
            "next_auto_crawl": next_auto_crawl,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get auto-crawl status: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/crawl/clear', methods=['POST'])
def clear_crawl_data():
    """Clear all crawl data (documents and visited URLs) for a fresh start."""
    global crawl_in_progress
    
    if crawl_in_progress:
        return jsonify({
            "error": "Cannot clear data while crawl is in progress",
            "status": "rejected"
        }), 409
    
    try:
        # Clear visited URLs from Redis
        clear_visited_urls_from_redis()
        
        # Clear vector store documents
        vectorstore = initialize_vector_store_for_crawl()
        if vectorstore is not None:
            all_ids = vectorstore.get(ids=[])['ids']
            if all_ids:
                vectorstore.delete(ids=all_ids)
                vectorstore.persist()
                doc_count = len(all_ids)
            else:
                doc_count = 0
        else:
            doc_count = "unknown"
        
        return jsonify({
            "message": "Crawl data cleared successfully",
            "status": "cleared",
            "documents_removed": doc_count,
            "visited_urls_cleared": True,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to clear crawl data: {str(e)}",
            "status": "failed"
        }), 500

def _run_crawl_background(start_url, max_pages, delay):
    """Run crawl in background thread."""
    global crawl_in_progress
    try:
        update_crawl_status("STARTING")
        success = crawl_and_process_documents(start_url, max_pages, delay)
        if success:
            update_crawl_status("COMPLETED")
        else:
            update_crawl_status("FAILED")
    except Exception as e:
        print(f"{SERVICE_NAME} - Error in background crawl: {e}")
        update_crawl_status("FAILED", {"error_message": str(e)})
    finally:
        crawl_in_progress = False

def _check_and_start_auto_crawl():
    """Check if auto-crawl should start on service startup."""
    global crawl_thread, crawl_in_progress
    
    # Check if auto-crawl is enabled
    if not os.getenv("AUTO_CRAWL_ENABLED", "true").lower() == "true":
        print(f"{SERVICE_NAME} - Auto-crawl disabled, skipping startup crawl")
        return
    
    if crawl_in_progress:
        print(f"{SERVICE_NAME} - Crawl already in progress, skipping startup crawl")
        return
    
    try:
        # Check if vector store has any documents
        vectorstore = initialize_vector_store_for_crawl()
        if vectorstore is not None:
            doc_count = vectorstore._collection.count()
            print(f"{SERVICE_NAME} - Vector store has {doc_count} documents")
            
            if doc_count == 0:
                print(f"{SERVICE_NAME} - No documents found, starting auto-crawl...")
                # Start initial crawl with default parameters
                crawl_thread = threading.Thread(
                    target=_run_crawl_background,
                    args=(FANDOM_WIKI_START_URL, FANDOM_WIKI_MAX_PAGES, FANDOM_WIKI_CRAWL_DELAY),
                    daemon=True
                )
                crawl_thread.start()
                crawl_in_progress = True
                print(f"{SERVICE_NAME} - Auto-crawl started successfully")
            else:
                print(f"{SERVICE_NAME} - Vector store already populated, skipping startup crawl")
        else:
            print(f"{SERVICE_NAME} - Could not initialize vector store for auto-crawl check")
            
    except Exception as e:
        print(f"{SERVICE_NAME} - Error during auto-crawl check: {e}")

if __name__ == '__main__':
    print(f"--- Starting {SERVICE_NAME} Service ---")
    
    # Initialize Redis connection
    initialize_redis()
    
    # Initialize other components
    try:
        get_redis_connection()
        print(f"{SERVICE_NAME} - Initialization complete.")
        
        # Check and start auto-crawl if needed
        _check_and_start_auto_crawl()
        
    except Exception as e:
        print(f"{SERVICE_NAME} - Warning: Non-critical error during startup: {e}")
    
    PORT = int(os.getenv("RAG_CRAWLER_PORT", 5009))
    print(f"{SERVICE_NAME} - Flask app starting on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False) 