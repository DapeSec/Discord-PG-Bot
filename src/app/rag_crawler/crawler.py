import os
import time
import traceback
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import MongoClient, errors as pymongo_errors

# Langchain imports
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
SERVICE_NAME = "RAGCrawler"
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "/app/chroma_db") # Path inside the container
FANDOM_WIKI_START_URL = os.getenv("FANDOM_WIKI_START_URL", "https://familyguy.fandom.com/wiki/Main_Page")
FANDOM_WIKI_MAX_PAGES = int(os.getenv("FANDOM_WIKI_MAX_PAGES", "100").split('#')[0].strip())
FANDOM_WIKI_CRAWL_DELAY = int(os.getenv("FANDOM_WIKI_CRAWL_DELAY", "1").split('#')[0].strip())

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:adminpassword@mongodb:27017/?authSource=admin")
DB_NAME = os.getenv("MONGO_DB_NAME", "discord_bot_conversations")
CRAWL_STATUS_COLLECTION_NAME = "crawl_status"

# Global variables for services
embeddings_model = None
vectorstore = None
mongo_client = None
db = None
crawl_status_collection = None

def get_mongo_connection():
    """Establishes and returns a MongoDB connection."""
    global mongo_client, db, crawl_status_collection
    if mongo_client is None:
        try:
            print(f"{SERVICE_NAME} - Attempting to connect to MongoDB...")
            mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000) # 10s timeout
            mongo_client.admin.command('ping') # Verify connection
            db = mongo_client[DB_NAME]
            crawl_status_collection = db[CRAWL_STATUS_COLLECTION_NAME]
            print(f"{SERVICE_NAME} - Successfully connected to MongoDB: {DB_NAME}")
        except pymongo_errors.ConnectionFailure as e:
            print(f"{SERVICE_NAME} - ERROR: Could not connect to MongoDB: {e}")
            mongo_client = None # Reset on failure
            db = None
            crawl_status_collection = None
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: An unexpected error occurred with MongoDB connection: {e}")
            mongo_client = None
            db = None
            crawl_status_collection = None
    return crawl_status_collection

def update_crawl_status(status, pages_crawled=0, documents_added=0, error_message=None):
    """Updates the crawl status in MongoDB."""
    if get_mongo_connection():
        try:
            crawl_status_collection.update_one(
                {"service_name": SERVICE_NAME},
                {
                    "$set": {
                        "last_crawl_timestamp": time.time(),
                        "status": status,
                        "pages_crawled": pages_crawled,
                        "documents_added": documents_added,
                        "error_message": error_message
                    }
                },
                upsert=True
            )
            print(f"{SERVICE_NAME} - Crawl status updated: {status}")
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: Failed to update crawl status in MongoDB: {e}")

def get_embeddings_model():
    """Initializes and returns the SentenceTransformer embeddings model."""
    global embeddings_model
    if embeddings_model is None:
        try:
            embeddings_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
            print(f"{SERVICE_NAME} - SentenceTransformerEmbeddings model loaded successfully.")
        except Exception as e:
            print(f"{SERVICE_NAME} - ERROR: Error loading SentenceTransformerEmbeddings model: {e}")
            raise # Critical error, crawler cannot proceed
    return embeddings_model

def initialize_vector_store_for_crawl():
    """Initializes a new or loads and clears an existing Chroma vector store for crawling."""
    global vectorstore
    try:
        print(f"{SERVICE_NAME} - Initializing Chroma DB at {CHROMA_DB_PATH} for new crawl...")
        # Always create a new store or clear existing one for a fresh crawl
        vectorstore = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=get_embeddings_model())
        
        # Clear existing documents
        all_ids = vectorstore.get(ids=[])['ids'] # Get all IDs
        if all_ids:
            print(f"{SERVICE_NAME} - Clearing {len(all_ids)} existing documents from Chroma DB...")
            vectorstore.delete(ids=all_ids)
            vectorstore.persist() # Persist changes after deletion
            print(f"{SERVICE_NAME} - Successfully cleared Chroma DB.")
        else:
            print(f"{SERVICE_NAME} - Chroma DB is already empty or new.")
        
        print(f"{SERVICE_NAME} - Chroma DB ready for ingestion.")

    except Exception as e:
        print(f"{SERVICE_NAME} - ERROR: Error initializing Chroma DB for crawl: {e}")
        print(traceback.format_exc())
        raise # Critical error
    return vectorstore

def load_documents_from_url(url):
    """Loads and extracts text and links from a single URL."""
    try:
        response = requests.get(url, timeout=30) # 30 second timeout for fetching page
        response.raise_for_status() # Raise an exception for bad status codes
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Basic text extraction (can be improved for specific site structures)
        # Try to find main content area, fall back to body
        main_content = soup.find('div', class_='mw-parser-output') # Common for MediaWiki (Fandom)
        if not main_content:
            main_content = soup.body
        
        text_content = ' '.join(t for t in main_content.find_all(string=True, recursive=True) if t.parent.name not in ['style', 'script', 'head', 'title', 'meta', '[document]'] and t.strip())
        
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
        return None, []

def crawl_and_process_documents(start_url, max_pages, delay):
    """Crawls a website, extracts text, splits it, and stores it in the vector store."""
    if vectorstore is None:
        print(f"{SERVICE_NAME} - ERROR: Vector store not initialized. Cannot crawl.")
        update_crawl_status("FAILED", error_message="Vector store not initialized")
        return False

    print(f"{SERVICE_NAME} - Starting crawl from {start_url} (max {max_pages} pages, {delay}s delay)...")
    update_crawl_status("IN_PROGRESS")

    queue = deque([start_url])
    visited_urls = set()
    pages_crawled = 0
    documents_added_total = 0
    base_netloc = urlparse(start_url).netloc

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
            
            text_content, links = load_documents_from_url(current_url)
            
            if text_content:
                # Using create_documents to get Langchain Document objects
                docs = text_splitter.create_documents([text_content], metadatas=[{"source": current_url}])
                if docs:
                    try:
                        vectorstore.add_documents(docs)
                        # No need to call persist() after every add_documents with Chroma usually,
                        # but for a long crawl, periodic persistence might be safer.
                        # For now, we persist at the very end.
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

            for link in links:
                parsed_link = urlparse(link)
                # Ensure it's a valid HTTP/HTTPS link and stays on the same domain
                if parsed_link.scheme in ['http', 'https'] and parsed_link.netloc == base_netloc and link not in visited_urls:
                    queue.append(link)
            
            # Log progress periodically
            if pages_crawled % 50 == 0 and pages_crawled > 0:
                print(f"{SERVICE_NAME} - Progress: {pages_crawled}/{max_pages} pages crawled. Total documents in DB: {vectorstore._collection.count()}")
                update_crawl_status("IN_PROGRESS", pages_crawled, vectorstore._collection.count())

            time.sleep(delay) # Respectful delay

        # Final persist after loop finishes
        print(f"{SERVICE_NAME} - Persisting all changes to Chroma DB...")
        vectorstore.persist()
        print(f"{SERVICE_NAME} - Chroma DB persisted.")

    except Exception as e:
        print(f"{SERVICE_NAME} - CRITICAL ERROR during crawl: {e}")
        print(traceback.format_exc())
        update_crawl_status("FAILED", pages_crawled, vectorstore._collection.count() if vectorstore else documents_added_total, str(e))
        return False
    finally:
        end_time = time.time()
        duration = end_time - start_time
        print(f"{SERVICE_NAME} - Crawl finished in {duration:.2f} seconds.")
        print(f"{SERVICE_NAME} - Total pages crawled: {pages_crawled}. Total documents in Chroma DB: {vectorstore._collection.count() if vectorstore else documents_added_total}.")
        if vectorstore is not None and vectorstore._collection.count() > 0:
            update_crawl_status("SUCCESS", pages_crawled, vectorstore._collection.count())
        elif pages_crawled > 0 : # If we crawled but DB is empty (shouldn't happen if no errors)
            update_crawl_status("WARNING_EMPTY_DB", pages_crawled, 0)
        else: # No pages crawled, potentially an issue with start URL or initial connection
            update_crawl_status("COMPLETED_NO_PAGES", pages_crawled, 0)

    return True

if __name__ == "__main__":
    print(f"--- Starting {SERVICE_NAME} --- ")
    print(f"Chroma DB Path: {CHROMA_DB_PATH}")
    print(f"Fandom Wiki Start URL: {FANDOM_WIKI_START_URL}")
    print(f"Max Pages to Crawl: {FANDOM_WIKI_MAX_PAGES}")
    print(f"Crawl Delay: {FANDOM_WIKI_CRAWL_DELAY}s")

    get_mongo_connection() # Initialize MongoDB connection for status logging

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