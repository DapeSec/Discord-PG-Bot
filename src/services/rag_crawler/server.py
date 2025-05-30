#!/usr/bin/env python3
"""
RAG Crawler Service Server

Entry point for the RAG Crawler microservice.
Exposes the Flask app for gunicorn deployment.
"""

import os
import sys
import threading
import time

# Add the src directory to the Python path for imports
sys.path.insert(0, '/app/src')

from src.services.rag_crawler.crawler_service import app, initialize_redis, _check_and_start_auto_crawl

# Initialize services on startup
print("🚀 RAG Crawler Server: Starting initialization...")

# Initialize Redis connection
redis_client = initialize_redis()

print("✅ RAG Crawler Server: Initialization complete")

# Start auto-crawl check in background thread (for Gunicorn)
def start_auto_crawl_background():
    """Start auto-crawl check after a brief delay to ensure full startup"""
    time.sleep(5)  # Wait for full service startup
    try:
        _check_and_start_auto_crawl()
    except Exception as e:
        print(f"🔍 RAG Crawler Server: Auto-crawl startup error: {e}")

# Start background thread for auto-crawl
auto_crawl_thread = threading.Thread(target=start_auto_crawl_background, daemon=True)
auto_crawl_thread.start()
print("🔄 RAG Crawler Server: Auto-crawl check scheduled")

if __name__ == '__main__':
    # This is only used for local development
    port = int(os.getenv('RAG_CRAWLER_PORT', 6009))
    app.run(host='0.0.0.0', port=port, debug=False) 