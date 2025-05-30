import os
import asyncio
import requests
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Load environment variables
load_dotenv()

# Configuration
DISCORD_BOT_TOKEN_STEWIE = os.getenv("DISCORD_BOT_TOKEN_STEWIE")
MESSAGE_ROUTER_URL = os.getenv("MESSAGE_ROUTER_URL", "http://message-router:6005/orchestrate")

class StewieDiscordBot:
    """Stewie Griffin Discord bot handler."""
    
    def __init__(self):
        """Initialize the Stewie Discord bot."""
        self.bot = None
        self.is_running = False
        self.message_count = 0
        self.error_count = 0
        
        if not DISCORD_BOT_TOKEN_STEWIE:
            print("❌ Stewie Discord: DISCORD_BOT_TOKEN_STEWIE not set!")
            return
            
        # Configure bot with intents
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(
            command_prefix='!stewie ',
            intents=intents,
            description="Stewie Griffin - evil genius baby from Family Guy"
        )
        
        self.setup_bot_events()
    
    def setup_bot_events(self):
        """Setup Discord bot event handlers."""
        
        @self.bot.event
        async def on_ready():
            print(f"👶 Stewie Discord Bot: Logged in as {self.bot.user}")
            self.is_running = True
        
        @self.bot.event
        async def on_message(message):
            """Handle incoming Discord messages."""
            # Ignore messages from bots
            if message.author.bot:
                return
            
            # Only respond to mentions or DMs
            if not (self.bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel)):
                return
            
            try:
                self.message_count += 1
                
                # Clean the message content (remove mentions)
                content = message.content
                if self.bot.user.mentioned_in(message):
                    content = content.replace(f'<@{self.bot.user.id}>', '').strip()
                
                # Send typing indicator
                async with message.channel.typing():
                    # Get conversation history (simplified for now)
                    conversation_history = []
                    
                    # Send to message router
                    response = await self.send_to_message_router(
                        input_text=content,
                        channel_id=str(message.channel.id),
                        user_id=str(message.author.id),
                        conversation_history=conversation_history
                    )
                    
                    if response and response.get("success"):
                        stewie_response = response["data"]["response"]
                        await message.channel.send(stewie_response)
                    else:
                        error_msg = response.get("error", "Unknown error") if response else "No response"
                        await message.channel.send("What the deuce?! My sophisticated systems appear to be malfunctioning! Blast! 🎭⚙️")
                        print(f"❌ Stewie Discord: Error - {error_msg}")
                        self.error_count += 1
            
            except Exception as e:
                self.error_count += 1
                print(f"❌ Stewie Discord: Exception handling message: {e}")
                print(traceback.format_exc())
                await message.channel.send("Confound it! My brilliant intellect has encountered an unexpected error! How utterly pedestrian! 🧠💥")
    
    async def send_to_message_router(self, input_text: str, channel_id: str, user_id: str, conversation_history: list) -> Optional[Dict[str, Any]]:
        """Send message to the message router service."""
        try:
            data = {
                "character_name": "Stewie",
                "input_text": input_text,
                "channel_id": channel_id,
                "user_id": user_id,
                "conversation_history": conversation_history
            }
            
            # Use asyncio to make non-blocking HTTP request
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(MESSAGE_ROUTER_URL, json=data, timeout=30)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Stewie Discord: Message router returned {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.Timeout:
            print("❌ Stewie Discord: Message router timeout")
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError:
            print("❌ Stewie Discord: Cannot connect to message router")
            return {"success": False, "error": "Connection failed"}
        except Exception as e:
            print(f"❌ Stewie Discord: Exception sending to message router: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_bot(self):
        """Start the Discord bot."""
        if not self.bot or not DISCORD_BOT_TOKEN_STEWIE:
            print("❌ Stewie Discord: Cannot start - missing bot token")
            return
        
        try:
            print("🚀 Stewie Discord: Starting bot...")
            await self.bot.start(DISCORD_BOT_TOKEN_STEWIE)
        except Exception as e:
            print(f"❌ Stewie Discord: Failed to start bot: {e}")
            self.error_count += 1
    
    def get_status(self) -> Dict[str, Any]:
        """Get bot status."""
        return {
            "character": "Stewie Griffin",
            "bot_ready": self.is_running,
            "bot_user": str(self.bot.user) if self.bot and self.bot.user else None,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "token_configured": bool(DISCORD_BOT_TOKEN_STEWIE),
            "message_router_url": MESSAGE_ROUTER_URL,
            "timestamp": datetime.now().isoformat()
        }

# Global bot instance
stewie_bot = StewieDiscordBot()

async def run_discord_bot():
    """Run Discord bot in asyncio loop."""
    await stewie_bot.start_bot()

if __name__ == '__main__':
    print(f"👶 Stewie Discord Bot starting...")
    print(f"🔗 Message Router URL: {MESSAGE_ROUTER_URL}")
    print(f"🔐 Token configured: {bool(DISCORD_BOT_TOKEN_STEWIE)}")
    
    if DISCORD_BOT_TOKEN_STEWIE:
        asyncio.run(run_discord_bot())
    else:
        print("❌ Stewie Discord: No token provided") 