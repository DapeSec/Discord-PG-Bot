#!/usr/bin/env python3
"""
RAG Retriever Service Server

Entry point for the RAG Retriever microservice.
Exposes the Flask app for gunicorn deployment.
"""

import os
import sys

# Add the src directory to the Python path for imports
sys.path.insert(0, '/app/src')

from src.services.rag_retriever.retriever_service import app, initialize_vector_store, initialize_redis

# Initialize services on startup
print("🚀 RAG Retriever Server: Starting initialization...")

# Initialize Redis connection
redis_client = initialize_redis()

# Initialize vector store
vector_store = initialize_vector_store()

print("✅ RAG Retriever Server: Initialization complete")

if __name__ == '__main__':
    # This is only used for local development
    port = int(os.getenv('RAG_RETRIEVER_PORT', 6007))
    app.run(host='0.0.0.0', port=port, debug=False) 