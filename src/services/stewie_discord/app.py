import os
import asyncio
from datetime import datetime
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
STEWIE_DISCORD_PORT = int(os.getenv("STEWIE_DISCORD_PORT", "6013"))
DISCORD_BOT_TOKEN_STEWIE = os.getenv("DISCORD_BOT_TOKEN_STEWIE")
MESSAGE_ROUTER_URL = os.getenv("MESSAGE_ROUTER_URL", "http://message-router:6005/orchestrate")

# Flask app for health checks and API
app = Flask(__name__)

# Import the bot instance from the main server module
try:
    from src.services.stewie_discord.discord_bot import stewie_bot
    BOT_AVAILABLE = True
except ImportError:
    BOT_AVAILABLE = False
    stewie_bot = None

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        if BOT_AVAILABLE and stewie_bot:
            status = stewie_bot.get_status()
            health_status = "healthy" if status.get("bot_ready", False) and status.get("token_configured", False) else "degraded"
            
            return jsonify({
                "status": health_status,
                "service": "Stewie_Discord_Handler",
                **status
            }), 200
        else:
            return jsonify({
                "status": "degraded",
                "service": "Stewie_Discord_Handler",
                "bot_ready": False,
                "token_configured": bool(DISCORD_BOT_TOKEN_STEWIE),
                "error": "Discord bot module not available",
                "timestamp": datetime.now().isoformat()
            }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/status', methods=['GET'])
def get_status():
    """Get detailed bot status."""
    try:
        if BOT_AVAILABLE and stewie_bot:
            return jsonify(stewie_bot.get_status()), 200
        else:
            return jsonify({
                "character": "Stewie Griffin",
                "bot_ready": False,
                "token_configured": bool(DISCORD_BOT_TOKEN_STEWIE),
                "message_router_url": MESSAGE_ROUTER_URL,
                "error": "Discord bot module not available",
                "timestamp": datetime.now().isoformat()
            }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    """API endpoint to send messages (for testing)."""
    return jsonify({
        "message": "Stewie Discord handler is running via Discord bot",
        "note": "Use Discord mentions or DMs to interact with Stewie",
        "timestamp": datetime.now().isoformat()
    }), 200

if __name__ == '__main__':
    # This should only be used for development
    app.run(host='0.0.0.0', port=STEWIE_DISCORD_PORT, debug=False) 