#!/usr/bin/env python3
"""
Environment Setup Script for Discord Family Guy Bot
Helps users configure their .env file with the correct environment variables.
"""

import os
import sys

def create_env_file():
    """Create a .env file with proper configuration."""
    
    print("🤖 Discord Family Guy Bot - Environment Setup")
    print("=" * 50)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return
    
    print("\nPlease provide the following information:")
    
    # Required Discord Bot Tokens
    print("\n📱 DISCORD BOT TOKENS (Required)")
    peter_token = input("Peter Bot Token: ").strip()
    brian_token = input("Brian Bot Token: ").strip()
    stewie_token = input("Stewie Bot Token: ").strip()
    
    if not all([peter_token, brian_token, stewie_token]):
        print("❌ All bot tokens are required!")
        sys.exit(1)
    
    # Required Bot Mention Strings
    print("\n🔗 BOT MENTION STRINGS (Required)")
    print("Get these from Discord after creating the bots (format: <@123456789>)")
    peter_mention = input("Peter Bot Mention: ").strip()
    brian_mention = input("Brian Bot Mention: ").strip()
    stewie_mention = input("Stewie Bot Mention: ").strip()
    
    if not all([peter_mention, brian_mention, stewie_mention]):
        print("❌ All bot mention strings are required!")
        sys.exit(1)
    
    # Required Default Channel
    print("\n💬 DEFAULT CHANNEL (Required)")
    default_channel = input("Default Discord Channel ID for organic conversations: ").strip()
    
    if not default_channel:
        print("❌ Default channel ID is required!")
        sys.exit(1)
    
    # Optional configurations
    print("\n⚙️  OPTIONAL CONFIGURATIONS")
    silence_threshold = input("Conversation silence threshold in minutes (default: 30): ").strip() or "30"
    min_time_between = input("Minimum time between organic conversations in minutes (default: 10): ").strip() or "10"
    
    # Create .env file content
    env_content = f"""# Discord Bot Tokens
DISCORD_BOT_TOKEN_PETER={peter_token}
DISCORD_BOT_TOKEN_BRIAN={brian_token}
DISCORD_BOT_TOKEN_STEWIE={stewie_token}

# Bot Mention Strings
PETER_BOT_MENTION_STRING={peter_mention}
BRIAN_BOT_MENTION_STRING={brian_mention}
STEWIE_BOT_MENTION_STRING={stewie_mention}

# Default Discord Channel for Organic Conversations
DEFAULT_DISCORD_CHANNEL_ID={default_channel}

# MongoDB Configuration (Docker defaults)
MONGO_URI=mongodb://admin:adminpassword@mongodb:27017/?authSource=admin
MONGO_DB_NAME=discord_bot_conversations
MONGO_COLLECTION_NAME=conversations

# Ollama Configuration (Docker defaults)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Organic Conversation Configuration
CONVERSATION_SILENCE_THRESHOLD_MINUTES={silence_threshold}
MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS={min_time_between}

# RAG Configuration for Family Guy Wiki
FANDOM_WIKI_START_URL=https://familyguy.fandom.com/wiki/Main_Page
FANDOM_WIKI_MAX_PAGES=100
FANDOM_WIKI_CRAWL_DELAY=1

# Orchestrator API URL (for bot communication)
ORCHESTRATOR_API_URL=http://localhost:5003/orchestrate
"""
    
    # Write .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("\n✅ .env file created successfully!")
        print("\n🚀 Next steps:")
        print("1. Make sure Ollama is running with the 'discord-bot' model")
        print("2. Run: docker-compose -f docker/docker-compose.yml up --build")
        print("3. The organic conversation coordinator will start automatically!")
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        sys.exit(1)

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print(__doc__)
        return
    
    create_env_file()

if __name__ == '__main__':
    main() 