#!/usr/bin/env python3
"""
Startup script for Stewie Discord service that runs both:
1. Gunicorn web server for health checks and API
2. Discord bot client for Discord functionality
"""
import os
import sys
import asyncio
import subprocess
import signal
from threading import Thread
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
STEWIE_DISCORD_PORT = int(os.getenv("STEWIE_DISCORD_PORT", "6013"))
DISCORD_BOT_TOKEN_STEWIE = os.getenv("DISCORD_BOT_TOKEN_STEWIE")

# Global process references
gunicorn_process = None
discord_task = None

def start_gunicorn():
    """Start Gunicorn web server for Flask app."""
    global gunicorn_process
    
    cmd = [
        "gunicorn",
        "--bind", f"0.0.0.0:{STEWIE_DISCORD_PORT}",
        "--workers", "2",
        "--timeout", "120",
        "--worker-class", "sync",
        "src.services.stewie_discord.app:app"
    ]
    
    print(f"🌐 Starting Gunicorn web server on port {STEWIE_DISCORD_PORT}...")
    gunicorn_process = subprocess.Popen(cmd)
    return gunicorn_process

async def start_discord_bot():
    """Start Discord bot client."""
    global discord_task
    
    if not DISCORD_BOT_TOKEN_STEWIE:
        print("❌ Stewie Discord: No bot token provided, Discord bot will not start")
        return
    
    try:
        from src.services.stewie_discord.discord_bot import run_discord_bot
        print("👶 Starting Discord bot client...")
        await run_discord_bot()
    except Exception as e:
        print(f"❌ Failed to start Discord bot: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
    
    # Stop Gunicorn
    if gunicorn_process:
        print("🌐 Stopping Gunicorn...")
        gunicorn_process.terminate()
        gunicorn_process.wait()
    
    # Stop Discord bot
    if discord_task and not discord_task.done():
        print("👶 Stopping Discord bot...")
        discord_task.cancel()
    
    print("✅ Shutdown complete")
    sys.exit(0)

def run_gunicorn_thread():
    """Run Gunicorn in a separate thread."""
    try:
        start_gunicorn()
        gunicorn_process.wait()  # Wait for Gunicorn to finish
    except Exception as e:
        print(f"❌ Gunicorn error: {e}")

async def main():
    """Main function that starts both services."""
    global discord_task
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Starting Stewie Discord Handler...")
    print(f"🔗 Port: {STEWIE_DISCORD_PORT}")
    print(f"🔐 Token configured: {bool(DISCORD_BOT_TOKEN_STEWIE)}")
    
    # Start Gunicorn in a background thread
    gunicorn_thread = Thread(target=run_gunicorn_thread, daemon=True)
    gunicorn_thread.start()
    
    # Give Gunicorn a moment to start
    await asyncio.sleep(2)
    
    # Start Discord bot in main thread
    try:
        discord_task = asyncio.create_task(start_discord_bot())
        await discord_task
    except asyncio.CancelledError:
        print("👶 Discord bot cancelled")
    except Exception as e:
        print(f"❌ Discord bot error: {e}")
    
    # Keep the main thread alive
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == '__main__':
    asyncio.run(main()) 