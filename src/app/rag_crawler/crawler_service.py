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

# Import the existing crawler functionality
from .crawler import (
    SERVICE_NAME,
    get_mongo_connection,
    update_crawl_status,
    get_embeddings_model,
    initialize_vector_store_for_crawl,
    crawl_and_process_documents,
    FANDOM_WIKI_START_URL,
    FANDOM_WIKI_MAX_PAGES,
    FANDOM_WIKI_CRAWL_DELAY
)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Global variables for tracking crawl status
current_crawl_thread = None
crawl_in_progress = False
auto_crawl_thread = None

# Auto-crawl configuration
AUTO_CRAWL_ENABLED = os.getenv("AUTO_CRAWL_ENABLED", "true").lower() == "true"
AUTO_CRAWL_INTERVAL_DAYS = int(os.getenv("AUTO_CRAWL_INTERVAL_DAYS", "30"))
AUTO_CRAWL_CHECK_INTERVAL_HOURS = int(os.getenv("AUTO_CRAWL_CHECK_INTERVAL_HOURS", "24"))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the RAG Crawler service."""
    try:
        # Check MongoDB connection
        mongo_status = "connected" if get_mongo_connection() else "disconnected"
        
        # Check embeddings model
        try:
            get_embeddings_model()
            embeddings_status = "loaded"
        except Exception:
            embeddings_status = "not_loaded"
        
        # Check crawl status
        global crawl_in_progress
        service_status = "crawling" if crawl_in_progress else "idle"
        
        # Auto-crawl status
        auto_crawl_status = {
            "enabled": AUTO_CRAWL_ENABLED,
            "interval_days": AUTO_CRAWL_INTERVAL_DAYS,
            "should_crawl": _should_auto_crawl() if AUTO_CRAWL_ENABLED else False
        }
        
        return jsonify({
            "service_name": SERVICE_NAME,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "crawl_status": service_status,
            "auto_crawl": auto_crawl_status,
            "dependencies": {
                "mongodb": mongo_status,
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
    global current_crawl_thread, crawl_in_progress
    
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
        current_crawl_thread = threading.Thread(
            target=_run_crawl_background,
            args=(start_url, max_pages, delay),
            daemon=True
        )
        current_crawl_thread.start()
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
        # Get status from MongoDB
        mongo_conn = get_mongo_connection()
        if mongo_conn:
            status_doc = mongo_conn.find_one({"service_name": SERVICE_NAME})
            if status_doc:
                return jsonify({
                    "service_name": SERVICE_NAME,
                    "crawl_in_progress": crawl_in_progress,
                    "last_crawl": {
                        "timestamp": status_doc.get("last_crawl_timestamp"),
                        "status": status_doc.get("status"),
                        "pages_crawled": status_doc.get("pages_crawled", 0),
                        "documents_added": status_doc.get("documents_added", 0),
                        "error_message": status_doc.get("error_message")
                    }
                }), 200
        
        return jsonify({
            "service_name": SERVICE_NAME,
            "crawl_in_progress": crawl_in_progress,
            "last_crawl": None,
            "message": "No crawl history found"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get crawl status: {str(e)}"
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

@app.route('/auto_crawl/status', methods=['GET'])
def get_auto_crawl_status():
    """Get auto-crawl configuration and status."""
    global crawl_in_progress
    
    try:
        # Get last crawl info
        mongo_conn = get_mongo_connection()
        last_crawl_info = None
        next_auto_crawl = None
        
        if mongo_conn:
            status_doc = mongo_conn.find_one({"service_name": SERVICE_NAME})
            if status_doc and status_doc.get("last_crawl_timestamp"):
                last_crawl_str = status_doc.get("last_crawl_timestamp")
                try:
                    if isinstance(last_crawl_str, str):
                        last_crawl = datetime.fromisoformat(last_crawl_str.replace('Z', '+00:00'))
                    else:
                        last_crawl = last_crawl_str
                    
                    last_crawl_info = {
                        "timestamp": last_crawl.isoformat(),
                        "status": status_doc.get("status"),
                        "pages_crawled": status_doc.get("pages_crawled", 0),
                        "documents_added": status_doc.get("documents_added", 0)
                    }
                    
                    # Calculate next auto-crawl time
                    next_crawl_date = last_crawl.replace(tzinfo=None) + timedelta(days=AUTO_CRAWL_INTERVAL_DAYS)
                    next_auto_crawl = next_crawl_date.isoformat()
                    
                except Exception as e:
                    print(f"Error parsing last crawl timestamp: {e}")
        
        return jsonify({
            "auto_crawl_enabled": AUTO_CRAWL_ENABLED,
            "auto_crawl_interval_days": AUTO_CRAWL_INTERVAL_DAYS,
            "auto_crawl_check_interval_hours": AUTO_CRAWL_CHECK_INTERVAL_HOURS,
            "crawl_in_progress": crawl_in_progress,
            "last_crawl": last_crawl_info,
            "next_auto_crawl": next_auto_crawl,
            "should_crawl_now": _should_auto_crawl() if AUTO_CRAWL_ENABLED else False
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get auto-crawl status: {str(e)}"
        }), 500

def _run_crawl_background(start_url, max_pages, delay):
    """Run crawl operation in background thread."""
    global crawl_in_progress
    
    try:
        print(f"{SERVICE_NAME} - Starting background crawl...")
        
        # Initialize vector store
        initialize_vector_store_for_crawl()
        
        # Run the crawl
        success = crawl_and_process_documents(start_url, max_pages, delay)
        
        if success:
            print(f"{SERVICE_NAME} - Background crawl completed successfully")
        else:
            print(f"{SERVICE_NAME} - Background crawl completed with errors")
            
    except Exception as e:
        print(f"{SERVICE_NAME} - Background crawl failed: {e}")
        print(traceback.format_exc())
        update_crawl_status("FAILED", error_message=str(e))
    finally:
        crawl_in_progress = False

def _should_auto_crawl():
    """Check if an automatic crawl should be triggered based on last crawl time."""
    if not AUTO_CRAWL_ENABLED:
        return False
    
    try:
        mongo_conn = get_mongo_connection()
        if not mongo_conn:
            print(f"{SERVICE_NAME} - Cannot check auto-crawl: MongoDB not available")
            return False
        
        # Get last crawl status
        status_doc = mongo_conn.find_one({"service_name": SERVICE_NAME})
        
        if not status_doc or not status_doc.get("last_crawl_timestamp"):
            print(f"{SERVICE_NAME} - No previous crawl found, triggering initial crawl")
            return True
        
        # Parse last crawl timestamp
        last_crawl_str = status_doc.get("last_crawl_timestamp")
        if isinstance(last_crawl_str, str):
            try:
                last_crawl = datetime.fromisoformat(last_crawl_str.replace('Z', '+00:00'))
            except ValueError:
                # Try parsing without timezone info
                last_crawl = datetime.fromisoformat(last_crawl_str.replace('Z', ''))
        else:
            last_crawl = last_crawl_str
        
        # Check if enough time has passed
        time_since_crawl = datetime.now() - last_crawl.replace(tzinfo=None)
        days_since_crawl = time_since_crawl.days
        
        if days_since_crawl >= AUTO_CRAWL_INTERVAL_DAYS:
            print(f"{SERVICE_NAME} - {days_since_crawl} days since last crawl, triggering auto-crawl")
            return True
        else:
            print(f"{SERVICE_NAME} - {days_since_crawl} days since last crawl, next auto-crawl in {AUTO_CRAWL_INTERVAL_DAYS - days_since_crawl} days")
            return False
            
    except Exception as e:
        print(f"{SERVICE_NAME} - Error checking auto-crawl status: {e}")
        return False

def _auto_crawl_monitor():
    """Background thread that monitors and triggers automatic crawls."""
    global crawl_in_progress, current_crawl_thread
    
    print(f"{SERVICE_NAME} - Auto-crawl monitor started (interval: {AUTO_CRAWL_INTERVAL_DAYS} days, check every: {AUTO_CRAWL_CHECK_INTERVAL_HOURS} hours)")
    
    while True:
        try:
            # Check if we should trigger an auto-crawl
            if not crawl_in_progress and _should_auto_crawl():
                print(f"{SERVICE_NAME} - Triggering automatic crawl...")
                
                # Start auto-crawl with default parameters
                current_crawl_thread = threading.Thread(
                    target=_run_crawl_background,
                    args=(FANDOM_WIKI_START_URL, FANDOM_WIKI_MAX_PAGES, FANDOM_WIKI_CRAWL_DELAY),
                    daemon=True
                )
                current_crawl_thread.start()
                crawl_in_progress = True
            
            # Sleep for the check interval
            time.sleep(AUTO_CRAWL_CHECK_INTERVAL_HOURS * 3600)  # Convert hours to seconds
            
        except Exception as e:
            print(f"{SERVICE_NAME} - Auto-crawl monitor error: {e}")
            time.sleep(3600)  # Sleep for 1 hour on error

if __name__ == '__main__':
    print(f"--- Starting {SERVICE_NAME} Service ---")
    PORT = int(os.getenv("RAG_CRAWLER_PORT", 5009))
    
    # Initialize connections at startup
    try:
        get_mongo_connection()
        get_embeddings_model()
        print(f"{SERVICE_NAME} - Service initialization complete")
    except Exception as e:
        print(f"{SERVICE_NAME} - Warning: Initialization issues: {e}")
    
    # Start auto-crawl monitor if enabled
    if AUTO_CRAWL_ENABLED:
        auto_crawl_thread = threading.Thread(target=_auto_crawl_monitor, daemon=True)
        auto_crawl_thread.start()
        print(f"{SERVICE_NAME} - Auto-crawl monitor started")
    else:
        print(f"{SERVICE_NAME} - Auto-crawl disabled")
    
    print(f"{SERVICE_NAME} - Flask app starting on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True) 