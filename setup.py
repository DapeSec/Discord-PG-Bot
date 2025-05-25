#!/usr/bin/env python3
"""
Discord Family Guy Bot - Unified Setup Script
Comprehensive setup tool that handles environment configuration, service deployment, and testing.
"""

import os
import sys
import subprocess
import time
import requests
import json
import socket
from pathlib import Path
from datetime import datetime

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color

def print_header():
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.WHITE}🎭 Discord Family Guy Bot - Unified Setup{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print()

def log(message, color=Colors.GREEN):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{timestamp}]{Colors.NC} {message}")

def log_error(message):
    log(f"❌ {message}", Colors.RED)

def log_warning(message):
    log(f"⚠️  {message}", Colors.YELLOW)

def log_success(message):
    log(f"✅ {message}", Colors.GREEN)

def log_info(message):
    log(f"ℹ️  {message}", Colors.BLUE)

def check_prerequisites():
    """Check if all required software is installed."""
    log("Checking prerequisites...", Colors.PURPLE)
    
    missing = []
    
    # Check Docker
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            log_success("Docker is installed")
        else:
            missing.append("Docker (not working properly)")
    except FileNotFoundError:
        missing.append("Docker")
    
    # Check Docker Compose
    try:
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            log_success("Docker Compose is installed")
        else:
            missing.append("Docker Compose (not working properly)")
    except FileNotFoundError:
        missing.append("Docker Compose")
    
    # Check Ollama
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            log_success("Ollama is running")
            
            # Check for mistral-nemo model
            models = response.json().get('models', [])
            mistral_available = any('mistral-nemo' in model.get('name', '') for model in models)
            
            if mistral_available:
                log_success("mistral-nemo model is available")
            else:
                log_warning("mistral-nemo model not found")
                print(f"   {Colors.YELLOW}Run: ollama pull mistral-nemo{Colors.NC}")
                missing.append("mistral-nemo model")
        else:
            missing.append("Ollama (not responding properly)")
    except requests.exceptions.RequestException:
        missing.append("Ollama (not running)")
        print(f"   {Colors.YELLOW}Start with: ollama serve{Colors.NC}")
        print(f"   {Colors.YELLOW}Then install model: ollama pull mistral-nemo{Colors.NC}")
    
    if missing:
        log_error("Missing prerequisites:")
        for item in missing:
            print(f"   • {item}")
        return False
    
    log_success("All prerequisites satisfied")
    return True

def create_env_file():
    """Create comprehensive .env file with user input."""
    log("Setting up environment configuration...", Colors.PURPLE)
    
    env_path = Path('.env')
    if env_path.exists():
        response = input(f"{Colors.YELLOW}⚠️  .env file already exists. Overwrite? (y/N): {Colors.NC}")
        if response.lower() != 'y':
            log_info("Using existing .env file")
            return True
    
    print(f"\n{Colors.WHITE}🤖 Discord Bot Configuration{Colors.NC}")
    print("You need Discord bot tokens for Peter, Brian, and Stewie.")
    print("Create bots at: https://discord.com/developers/applications")
    print()
    
    # Get Discord tokens
    peter_token = input("Enter Peter's Discord bot token: ").strip()
    if not peter_token:
        log_error("Peter's token is required")
        return False
    
    brian_token = input("Enter Brian's Discord bot token: ").strip()
    if not brian_token:
        log_error("Brian's token is required")
        return False
    
    stewie_token = input("Enter Stewie's Discord bot token: ").strip()
    if not stewie_token:
        log_error("Stewie's token is required")
        return False
    
    # Get mention strings
    print(f"\n{Colors.WHITE}🔗 Bot Mention Strings{Colors.NC}")
    print("Get these from Discord after inviting bots (format: <@123456789>)")
    print("You can update these later in the .env file")
    
    peter_mention = input("Peter's mention string (optional for now): ").strip() or "<@PETER_BOT_ID>"
    brian_mention = input("Brian's mention string (optional for now): ").strip() or "<@BRIAN_BOT_ID>"
    stewie_mention = input("Stewie's mention string (optional for now): ").strip() or "<@STEWIE_BOT_ID>"
    
    # Get channel ID
    channel_id = input("\nEnter Discord channel ID where bots should operate: ").strip()
    if not channel_id:
        log_error("Channel ID is required")
        return False
    
    # Optional configurations
    print(f"\n{Colors.WHITE}⚙️  Optional Configurations{Colors.NC}")
    silence_threshold = input("Conversation silence threshold in minutes (default: 30): ").strip() or "30"
    min_time_between = input("Minimum time between organic conversations in minutes (default: 10): ").strip() or "10"
    max_pages = input("Maximum wiki pages to crawl (default: 100): ").strip() or "100"
    
    # Create comprehensive .env file
    env_content = f"""# === DISCORD BOT TOKENS ===
DISCORD_BOT_TOKEN_PETER={peter_token}
DISCORD_BOT_TOKEN_BRIAN={brian_token}
DISCORD_BOT_TOKEN_STEWIE={stewie_token}

# === BOT MENTION STRINGS ===
# Update these after inviting bots to your server
PETER_BOT_MENTION_STRING={peter_mention}
BRIAN_BOT_MENTION_STRING={brian_mention}
STEWIE_BOT_MENTION_STRING={stewie_mention}

# === DISCORD CHANNEL CONFIGURATION ===
DEFAULT_DISCORD_CHANNEL_ID={channel_id}

# === OLLAMA/MISTRAL CONFIGURATION ===
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=mistral-nemo

# === MONGODB CONFIGURATION ===
MONGO_URI=mongodb://admin:adminpassword@mongodb:27017/?authSource=admin
MONGO_DB_NAME=discord_bot_conversations
MONGO_COLLECTION_NAME=conversations

# === RAG SYSTEM CONFIGURATION ===
EMBEDDINGS_MODEL_NAME=all-MiniLM-L6-v2
CHROMA_DB_PATH=/app/chroma_db
FANDOM_WIKI_START_URL=https://familyguy.fandom.com/wiki/Main_Page
FANDOM_WIKI_MAX_PAGES={max_pages}
FANDOM_WIKI_CRAWL_DELAY=1
AUTO_CRAWL_ENABLED=true
AUTO_CRAWL_INTERVAL_DAYS=30
AUTO_CRAWL_CHECK_INTERVAL_HOURS=24

# === FINE-TUNING SYSTEM ===
FINE_TUNING_ENABLED=true
QUALITY_CONTROL_ENABLED=true
OPTIMIZATION_THRESHOLD=0.7
MIN_RATINGS_FOR_OPTIMIZATION=10
AB_TEST_PERCENTAGE=0.2
QUALITY_CONTROL_MIN_RATING=3.0
QUALITY_CONTROL_MAX_RETRIES=3

# === ORGANIC CONVERSATIONS ===
CONVERSATION_SILENCE_THRESHOLD_MINUTES={silence_threshold}
MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS={min_time_between}

# === SERVICE PORTS ===
ORCHESTRATOR_PORT=5003
RAG_RETRIEVER_PORT=5005
RAG_CRAWLER_PORT=5009
PETER_BOT_PORT=5006
BRIAN_BOT_PORT=5007
STEWIE_BOT_PORT=5008

# === API URLS ===
RAG_RETRIEVER_API_URL=http://rag-retriever:5005/retrieve
RAG_CRAWLER_API_URL=http://rag-crawler:5009

# === DEAD LETTER QUEUE ===
DLQ_MAX_RETRY_ATTEMPTS=3
DLQ_RETRY_DELAY_BASE=2.0
DLQ_MAX_RETRY_DELAY=300
DLQ_RETRY_WORKER_INTERVAL=60
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        log_success(".env file created successfully")
        return True
    except Exception as e:
        log_error(f"Failed to create .env file: {e}")
        return False

def build_and_start_services():
    """Build Docker images and start services in proper order."""
    log("Building and starting services...", Colors.PURPLE)
    
    # Change to docker directory
    docker_dir = Path('docker')
    if not docker_dir.exists():
        log_error("docker directory not found")
        return False
    
    os.chdir('docker')
    
    try:
        # Build images
        log("Building Docker images...")
        result = subprocess.run(['docker-compose', 'build', '--no-cache'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            log_error("Failed to build Docker images")
            print(result.stderr)
            return False
        log_success("Docker images built")
        
        # Start MongoDB first
        log("Starting MongoDB...")
        subprocess.run(['docker-compose', 'up', '-d', 'mongodb'], check=True)
        time.sleep(10)
        
        # Start RAG services
        log("Starting RAG services...")
        subprocess.run(['docker-compose', 'up', '-d', 'rag-retriever', 'rag-crawler'], check=True)
        time.sleep(10)
        
        # Start orchestrator
        log("Starting orchestrator...")
        subprocess.run(['docker-compose', 'up', '-d', 'orchestrator'], check=True)
        time.sleep(15)
        
        # Start bot services
        log("Starting bot services...")
        subprocess.run(['docker-compose', 'up', '-d', 'peter', 'brian', 'stewie'], check=True)
        time.sleep(10)
        
        log_success("All services started")
        return True
        
    except subprocess.CalledProcessError as e:
        log_error(f"Failed to start services: {e}")
        return False
    finally:
        os.chdir('..')

def check_service_health():
    """Check health of all services."""
    log("Checking service health...", Colors.PURPLE)
    
    services = {
        'MongoDB': ('localhost', 27017),
        'Orchestrator': 'http://localhost:5003/health',
        'RAG Retriever': 'http://localhost:5005/health',
        'Peter Bot': 'http://localhost:5006/health',
        'Brian Bot': 'http://localhost:5007/health',
        'Stewie Bot': 'http://localhost:5008/health',
    }
    
    healthy_count = 0
    total_count = len(services)
    
    for service_name, endpoint in services.items():
        try:
            if service_name == 'MongoDB':
                # Check MongoDB port
                host, port = endpoint
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    log_success(f"{service_name} is running")
                    healthy_count += 1
                else:
                    log_error(f"{service_name} is not accessible")
            else:
                # HTTP health check
                response = requests.get(endpoint, timeout=10)
                if response.status_code == 200:
                    log_success(f"{service_name} is healthy")
                    healthy_count += 1
                else:
                    log_warning(f"{service_name} returned status {response.status_code}")
        except Exception as e:
            log_error(f"{service_name} is not responding: {e}")
        
        time.sleep(0.5)
    
    print(f"\n{Colors.WHITE}Health Summary: {healthy_count}/{total_count} services healthy{Colors.NC}")
    return healthy_count == total_count

def test_ollama_integration():
    """Test Ollama integration with character responses."""
    log("Testing Ollama integration...", Colors.PURPLE)
    
    test_cases = {
        "Peter": {
            "prompt": "You are Peter Griffin from Family Guy. User: Hello Peter! Peter:",
            "expected": ["hehehe", "holy crap", "freakin"]
        },
        "Brian": {
            "prompt": "You are Brian Griffin from Family Guy. User: What do you think? Brian:",
            "expected": ["actually", "intellectual", "quite"]
        },
        "Stewie": {
            "prompt": "You are Stewie Griffin from Family Guy. User: Hello Stewie! Stewie:",
            "expected": ["blast", "deuce", "victory"]
        }
    }
    
    all_passed = True
    
    for character, config in test_cases.items():
        try:
            payload = {
                "model": "mistral-nemo",
                "prompt": config["prompt"],
                "stream": False,
                "options": {
                    "temperature": 0.9,
                    "num_predict": 50,
                    "stop": ["User:", "Human:"]
                }
            }
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip()
                
                if generated_text:
                    log_success(f"{character} response: {generated_text[:60]}...")
                else:
                    log_warning(f"{character} returned empty response")
                    all_passed = False
            else:
                log_error(f"{character} test failed: HTTP {response.status_code}")
                all_passed = False
                
        except Exception as e:
            log_error(f"{character} test failed: {e}")
            all_passed = False
    
    return all_passed

def trigger_initial_crawl():
    """Trigger initial RAG crawl to populate the knowledge base."""
    log("Triggering initial RAG crawl...", Colors.PURPLE)
    
    try:
        response = requests.post('http://localhost:5003/crawl/trigger', timeout=30)
        if response.status_code in [200, 202]:
            log_success("RAG crawl initiated successfully")
            log_info("This will populate the Family Guy knowledge base")
            return True
        else:
            log_warning(f"Crawl trigger returned status {response.status_code}")
            return False
    except Exception as e:
        log_error(f"Failed to trigger crawl: {e}")
        return False

def show_logs():
    """Show recent service logs."""
    log("Showing recent logs...", Colors.PURPLE)
    
    os.chdir('docker')
    try:
        result = subprocess.run(['docker-compose', 'logs', '--tail=20'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"\n{Colors.CYAN}Recent Logs:{Colors.NC}")
            print(result.stdout)
        else:
            log_error("Failed to get logs")
    finally:
        os.chdir('..')

def show_next_steps():
    """Show what to do next."""
    print(f"\n{Colors.GREEN}🎉 Setup Complete!{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.NC}")
    print()
    print(f"{Colors.WHITE}📱 Your Discord bots should now be online in your server.{Colors.NC}")
    print(f"{Colors.WHITE}💬 Try mentioning them in your Discord channel:{Colors.NC}")
    print("   @Peter what's up?")
    print("   @Brian tell me something intellectual")
    print("   @Stewie what are you plotting?")
    print()
    print(f"{Colors.WHITE}🔧 Useful commands:{Colors.NC}")
    print("   docker-compose logs -f          # View live logs")
    print("   docker-compose ps               # Check service status")
    print("   docker-compose down             # Stop all services")
    print("   docker-compose up -d            # Start services")
    print()
    print(f"{Colors.WHITE}📊 Monitor the system:{Colors.NC}")
    print("   http://localhost:5003/health              # Orchestrator health")
    print("   http://localhost:5003/fine_tuning_stats   # Performance stats")
    print("   http://localhost:5005/health              # RAG Retriever health")
    print()
    print(f"{Colors.WHITE}🐛 If you encounter issues:{Colors.NC}")
    print("   1. Check the logs: docker-compose logs")
    print("   2. Ensure Ollama is running: ollama serve")
    print("   3. Verify bot tokens are correct in .env")
    print("   4. Check Discord bot permissions")
    print("   5. See TROUBLESHOOTING.md for detailed help")

def main():
    """Main setup function."""
    print_header()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'health':
            check_service_health()
            return
        elif command == 'logs':
            show_logs()
            return
        elif command == 'test':
            test_ollama_integration()
            return
        elif command == 'crawl':
            trigger_initial_crawl()
            return
        elif command == 'help':
            print(__doc__)
            print(f"\n{Colors.WHITE}Available commands:{Colors.NC}")
            print("  python setup.py          # Full setup")
            print("  python setup.py health   # Check service health")
            print("  python setup.py logs     # Show recent logs")
            print("  python setup.py test     # Test Ollama integration")
            print("  python setup.py crawl    # Trigger RAG crawl")
            return
    
    # Full setup process
    log("Starting Discord Family Guy Bot setup...", Colors.WHITE)
    
    # Step 1: Check prerequisites
    if not check_prerequisites():
        log_error("Prerequisites not met. Please fix the issues above and try again.")
        sys.exit(1)
    
    # Step 2: Create .env file
    if not create_env_file():
        log_error("Failed to create .env file.")
        sys.exit(1)
    
    # Step 3: Build and start services
    if not build_and_start_services():
        log_error("Failed to start services.")
        sys.exit(1)
    
    # Step 4: Wait for services to initialize
    log("Waiting for services to initialize...", Colors.YELLOW)
    time.sleep(30)
    
    # Step 5: Check health
    if check_service_health():
        log_success("All services are healthy!")
    else:
        log_warning("Some services may need more time to start.")
        log_info("Check logs with: python setup.py logs")
    
    # Step 6: Test Ollama integration
    if test_ollama_integration():
        log_success("Ollama integration test passed!")
    else:
        log_warning("Ollama integration test had issues")
    
    # Step 7: Trigger initial crawl
    trigger_initial_crawl()
    
    # Step 8: Show logs and next steps
    show_logs()
    show_next_steps()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup interrupted by user.{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        sys.exit(1) 