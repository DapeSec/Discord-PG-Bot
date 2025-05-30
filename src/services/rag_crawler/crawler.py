import os
import time
import traceback
from collections import deque
from urllib.parse import urljoin, urlparse
from typing import Dict, Any
import warnings

# Suppress HuggingFace deprecation warnings
import os
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import MongoClient, errors as pymongo_errors
import redis
import json
from datetime import datetime, timedelta

# Langchain imports (updated to use new langchain-chroma package)
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
SERVICE_NAME = "RAG Crawler"
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
FANDOM_WIKI_START_URL = os.getenv("FANDOM_WIKI_START_URL", "https://familyguy.fandom.com/wiki/Main_Page")
FANDOM_WIKI_MAX_PAGES = int(os.getenv("FANDOM_WIKI_MAX_PAGES", "100").split('#')[0].strip())
FANDOM_WIKI_CRAWL_DELAY = int(os.getenv("FANDOM_WIKI_CRAWL_DELAY", "1").split('#')[0].strip())

REDIS_URL = os.getenv("REDIS_URL", "redis://keydb:6379")
EMBEDDINGS_MODEL_NAME = os.getenv("EMBEDDINGS_MODEL_NAME", "all-MiniLM-L6-v2")

# Global variables for services
redis_client = None
chroma_client = None
collection = None
embeddings_model = None
vectorstore = None

def get_redis_connection():
    """Establishes and returns a Redis connection for status tracking."""
    global redis_client
    if redis_client is None:
        try:
            print(f"{SERVICE_NAME} - Attempting to connect to Redis...")
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            redis_client.ping()
            print(f"{SERVICE_NAME} - Successfully connected to Redis")
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: Could not connect to Redis: {e}")
            redis_client = None
    return redis_client

def update_crawl_status(status: str, details: Dict[str, Any] = None):
    """Updates the crawl status in Redis."""
    if get_redis_connection():
        try:
            status_data = {
                "service_name": SERVICE_NAME,
                "status": status,
                "last_updated": datetime.now().isoformat(),
                "details": json.dumps(details) if details else "{}"
            }
            
            # Store status in Redis with expiry
            status_key = f"crawl_status:{SERVICE_NAME}"
            redis_client.hset(status_key, mapping=status_data)
            redis_client.expire(status_key, 86400)  # 24 hours
            
            print(f"{SERVICE_NAME} - Status updated: {status}")
            
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: Failed to update crawl status in Redis: {e}")
    else:
        print(f"{SERVICE_NAME} - WARNING: Cannot update status - Redis not available")

def get_embeddings_model():
    """Initializes and returns the SentenceTransformer embeddings model."""
    global embeddings_model
    if embeddings_model is None:
        try:
            print(f"{SERVICE_NAME} - Loading embeddings model: {EMBEDDINGS_MODEL_NAME}...")
            # Suppress specific warnings during model loading
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=FutureWarning)
                warnings.filterwarnings("ignore", message=".*resume_download.*deprecated.*")
                embeddings_model = SentenceTransformerEmbeddings(model_name=EMBEDDINGS_MODEL_NAME)
            print(f"{SERVICE_NAME} - SentenceTransformerEmbeddings model loaded successfully.")
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: Error loading SentenceTransformerEmbeddings model: {e}")
            raise # Critical error, crawler cannot proceed
    return embeddings_model

def initialize_vector_store_for_crawl():
    """Initializes or loads an existing Chroma vector store for crawling."""
    global vectorstore
    try:
        print(f"{SERVICE_NAME} - Initializing Chroma DB at {CHROMA_DB_PATH}...")
        # Load existing store or create new one (preserving existing data)
        # Use the same collection name as the retriever service
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_PATH, 
            embedding_function=get_embeddings_model(),
            collection_name="family_guy_docs"
        )
        
        # Check existing documents
        try:
            existing_count = vectorstore._collection.count()
            print(f"{SERVICE_NAME} - Found {existing_count} existing documents in Chroma DB")
            
            if existing_count > 0:
                print(f"{SERVICE_NAME} - Preserving existing {existing_count} documents")
                print(f"{SERVICE_NAME} - New crawl will add to existing knowledge base")
            else:
                print(f"{SERVICE_NAME} - Chroma DB is empty, starting fresh crawl")
                
        except Exception as e:
            print(f"{SERVICE_NAME} - Warning: Could not check existing document count: {e}")
            print(f"{SERVICE_NAME} - Proceeding with crawl anyway")
        
        print(f"{SERVICE_NAME} - Chroma DB ready for ingestion.")

    except Exception as e:
        print(f"{SERVICE_NAME} - ERROR: Error initializing Chroma DB: {e}")
        print(traceback.format_exc())
        raise # Critical error
    return vectorstore

def load_documents_from_url(url):
    """Loads and extracts text and links from a single URL."""
    try:
        # Add headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        response = requests.get(url, timeout=30, headers=headers) # 30 second timeout for fetching page
        response.raise_for_status() # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Basic text extraction (can be improved for specific site structures)
        # Try to find main content area, fall back to body
        main_content = soup.find('div', class_='mw-parser-output') # Common for MediaWiki (Fandom)
        if not main_content:
            main_content = soup.body
        
        if main_content:
            text_content = ' '.join(t for t in main_content.find_all(string=True, recursive=True) if t.parent.name not in ['style', 'script', 'head', 'title', 'meta', '[document]'] and t.strip())
        else:
            print(f"{SERVICE_NAME} - WARNING: No main content found for {url}")
            return None, []
        
        links = []
        for a_tag in soup.find_all('a', href=True):
            link = urljoin(url, a_tag['href'])
            if urlparse(link).netloc == urlparse(url).netloc: # Stay on the same domain
                links.append(link)
        return text_content, list(set(links)) # Return unique links
    except requests.exceptions.RequestException as e:
        print(f"{SERVICE_NAME} - ERROR: Failed to fetch URL {url}: {e}")
        return None, []
    except Exception as e:
        print(f"{SERVICE_NAME} - ERROR: Error processing URL {url}: {e}")
        print(f"{SERVICE_NAME} - ERROR details: {traceback.format_exc()}")
        return None, []

def get_visited_urls_from_redis():
    """Get previously visited URLs from Redis to enable resume functionality."""
    visited_urls = set()
    if get_redis_connection():
        try:
            visited_key = f"crawl_visited_urls:{SERVICE_NAME}"
            stored_urls = redis_client.smembers(visited_key)
            visited_urls = set(stored_urls)
            print(f"{SERVICE_NAME} - Loaded {len(visited_urls)} previously visited URLs from Redis")
        except Exception as e:
            print(f"{SERVICE_NAME} - Warning: Could not load visited URLs from Redis: {e}")
    return visited_urls

def save_visited_url_to_redis(url):
    """Save a visited URL to Redis for resume functionality."""
    if get_redis_connection():
        try:
            visited_key = f"crawl_visited_urls:{SERVICE_NAME}"
            redis_client.sadd(visited_key, url)
            redis_client.expire(visited_key, 604800)  # 7 days expiry
        except Exception as e:
            print(f"{SERVICE_NAME} - Warning: Could not save visited URL to Redis: {e}")

def clear_visited_urls_from_redis():
    """Clear visited URLs from Redis (useful for fresh crawls)."""
    if get_redis_connection():
        try:
            visited_key = f"crawl_visited_urls:{SERVICE_NAME}"
            redis_client.delete(visited_key)
            print(f"{SERVICE_NAME} - Cleared visited URLs from Redis")
        except Exception as e:
            print(f"{SERVICE_NAME} - Warning: Could not clear visited URLs from Redis: {e}")

def crawl_and_process_documents(start_url, max_pages, delay):
    """Crawls a website, extracts text, splits it, and stores it in the vector store."""
    if vectorstore is None:
        print(f"{SERVICE_NAME} - ERROR: Vector store not initialized. Cannot crawl.")
        update_crawl_status("FAILED", {"error_message": "Vector store not initialized"})
        return False

    print(f"{SERVICE_NAME} - Starting crawl from {start_url} (max {max_pages} pages, {delay}s delay)...")
    update_crawl_status("IN_PROGRESS", {"message": "Starting crawl", "start_url": start_url, "max_pages": max_pages})

    queue = deque([start_url])
    visited_urls = get_visited_urls_from_redis()  # Load previously visited URLs
    pages_crawled = 0
    documents_added_total = 0
    base_netloc = urlparse(start_url).netloc

    # If we have visited URLs, we're resuming
    if visited_urls:
        print(f"{SERVICE_NAME} - Resuming crawl with {len(visited_urls)} previously visited URLs")
    else:
        print(f"{SERVICE_NAME} - Starting fresh crawl")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        add_start_index=True,
    )

    start_time = time.time()

    try:
        while queue and pages_crawled < max_pages:
            current_url = queue.popleft()

            if current_url in visited_urls:
                continue

            print(f"{SERVICE_NAME} - Crawling: {current_url} ({pages_crawled + 1}/{max_pages})")
            visited_urls.add(current_url)
            save_visited_url_to_redis(current_url)  # Persist visited URL
            
            text_content, links = load_documents_from_url(current_url)
            
            if text_content:
                # Using create_documents to get Langchain Document objects
                docs = text_splitter.create_documents([text_content], metadatas=[{"source": current_url}])
                if docs:
                    try:
                        vectorstore.add_documents(docs)
                        # Documents are automatically persisted with the new langchain-chroma package
                        documents_added_total += len(docs)
                        print(f"  -> Added {len(docs)} chunks to Chroma DB (total: {documents_added_total}).")
                        pages_crawled += 1
                    except Exception as e:
                        print(f"  -> ERROR adding chunks for {current_url} to Chroma DB: {e}")
                        print(traceback.format_exc())
                else:
                    print(f"  -> No chunks generated for {current_url}.")
            else:
                print(f"  -> No content scraped from {current_url}.")

            # Add discovered links to queue
            new_links_added = 0
            for link in links:
                parsed_link = urlparse(link)
                # Ensure it's a valid HTTP/HTTPS link and stays on the same domain
                if parsed_link.scheme in ['http', 'https'] and parsed_link.netloc == base_netloc and link not in visited_urls:
                    queue.append(link)
                    new_links_added += 1
            
            if new_links_added > 0:
                print(f"  -> Discovered {new_links_added} new links (queue size: {len(queue)})")
            
            # Log progress periodically
            if pages_crawled % 10 == 0 and pages_crawled > 0:
                try:
                    current_doc_count = vectorstore._collection.count()
                    print(f"{SERVICE_NAME} - Progress: {pages_crawled}/{max_pages} pages crawled. Total documents in DB: {current_doc_count}")
                    update_crawl_status("IN_PROGRESS", {"pages_crawled": pages_crawled, "total_documents": current_doc_count, "queue_size": len(queue)})
                except Exception as e:
                    print(f"{SERVICE_NAME} - Warning: Could not update progress status: {e}")

            time.sleep(delay) # Respectful delay

        # Final processing after loop finishes
        print(f"{SERVICE_NAME} - All changes automatically persisted to Chroma DB...")
        print(f"{SERVICE_NAME} - Crawl processing complete.")

    except Exception as e:
        print(f"{SERVICE_NAME} - CRITICAL ERROR during crawl: {e}")
        print(traceback.format_exc())
        update_crawl_status("FAILED", {"pages_crawled": pages_crawled, "total_documents": vectorstore._collection.count() if vectorstore else documents_added_total, "error_message": str(e)})
        return False
    finally:
        end_time = time.time()
        duration = end_time - start_time
        print(f"{SERVICE_NAME} - Crawl finished in {duration:.2f} seconds.")
        print(f"{SERVICE_NAME} - Total pages crawled: {pages_crawled}. Total documents in Chroma DB: {vectorstore._collection.count() if vectorstore else documents_added_total}.")
        if vectorstore is not None and vectorstore._collection.count() > 0:
            update_crawl_status("SUCCESS", {"pages_crawled": pages_crawled, "total_documents": vectorstore._collection.count()})
        elif pages_crawled > 0 : # If we crawled but DB is empty (shouldn't happen if no errors)
            update_crawl_status("WARNING_EMPTY_DB", {"pages_crawled": pages_crawled, "total_documents": 0})
        else: # No pages crawled, potentially an issue with start URL or initial connection
            update_crawl_status("COMPLETED_NO_PAGES", {"pages_crawled": pages_crawled, "total_documents": 0})

    return True

if __name__ == "__main__":
    print(f"--- Starting {SERVICE_NAME} --- ")
    print(f"Chroma DB Path: {CHROMA_DB_PATH}")
    print(f"Fandom Wiki Start URL: {FANDOM_WIKI_START_URL}")
    print(f"Max Pages to Crawl: {FANDOM_WIKI_MAX_PAGES}")
    print(f"Crawl Delay: {FANDOM_WIKI_CRAWL_DELAY}s")

    get_redis_connection() # Initialize Redis connection for status logging

    try:
        initialize_vector_store_for_crawl()
        crawl_and_process_documents(
            start_url=FANDOM_WIKI_START_URL,
            max_pages=FANDOM_WIKI_MAX_PAGES,
            delay=FANDOM_WIKI_CRAWL_DELAY
        )
    except Exception as e:
        print(f"{SERVICE_NAME} - FATAL: A critical error occurred: {e}")
        print(traceback.format_exc())
        update_crawl_status("FATAL_ERROR", error_message=str(e))
        exit(1)
    
    print(f"--- {SERVICE_NAME} Finished --- ")
    exit(0) 