#!/usr/bin/env python3
"""
Organic Conversation Coordinator Demo Script
Demonstrates the new intelligent conversation initiation system that replaced the scheduler.
"""

import requests
import time
import json
from datetime import datetime, timedelta

class OrganicConversationDemo:
    def __init__(self, orchestrator_url="http://localhost:5003"):
        self.orchestrator_url = orchestrator_url
        
    def check_orchestrator_health(self):
        """Check if the orchestrator is running and healthy."""
        try:
            response = requests.get(f"{self.orchestrator_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Orchestrator Status: {data.get('status')}")
                components = data.get('components', {})
                print(f"   📊 Components: {', '.join(components.keys())}")
                return True
            else:
                print(f"❌ Orchestrator unhealthy: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to orchestrator. Is it running?")
            return False
        except Exception as e:
            print(f"❌ Error checking orchestrator: {e}")
            return False
    
    def demonstrate_organic_triggers(self):
        """Demonstrate different organic conversation triggers."""
        print("\n🌱 ORGANIC CONVERSATION TRIGGERS DEMO")
        print("=" * 50)
        
        triggers = [
            {
                "name": "Conversation Ending",
                "description": "Detects phrases like 'see you later', 'goodbye'",
                "example": "Well, see you later everyone!"
            },
            {
                "name": "Follow-up Opportunities", 
                "description": "Detects phrases like 'reminds me', 'speaking of'",
                "example": "That reminds me of something interesting..."
            },
            {
                "name": "Silence Detection",
                "description": "Starts conversations after 30+ minutes of silence",
                "example": "No messages for extended period"
            },
            {
                "name": "Post-Response Analysis",
                "description": "Checks for follow-up opportunities after each response",
                "example": "Natural conversation flow analysis"
            }
        ]
        
        for trigger in triggers:
            print(f"\n🎯 {trigger['name']}")
            print(f"   📝 {trigger['description']}")
            print(f"   💬 Example: {trigger['example']}")
    
    def demonstrate_character_selection(self):
        """Demonstrate intelligent character selection."""
        print("\n🎭 INTELLIGENT CHARACTER SELECTION")
        print("=" * 50)
        
        selection_factors = [
            "Topic Relevance: Who would naturally be interested?",
            "Character Dynamics: Relationships and conflicts",
            "Speech Patterns: Natural communication styles", 
            "Personality Triggers: What makes each character respond?",
            "Conversation Balance: Avoid same character twice",
            "RAG Context: Family Guy universe knowledge"
        ]
        
        for i, factor in enumerate(selection_factors, 1):
            print(f"{i}. {factor}")
        
        print(f"\n🧠 The same advanced coordinator that handles responses")
        print(f"   also chooses who should start conversations!")
    
    def demonstrate_rag_enhancement(self):
        """Demonstrate RAG-enhanced conversation starters."""
        print("\n🔍 RAG-ENHANCED CONVERSATION STARTERS")
        print("=" * 50)
        
        print("📚 The system uses Family Guy universe knowledge to:")
        print("   • Generate contextual conversation starters")
        print("   • Inspire topics based on recent conversations")
        print("   • Use character-specific expertise areas")
        print("   • Create authentic Family Guy references")
        
        print(f"\n💡 Example Enhancement Process:")
        print(f"   1. Analyze recent conversation topics")
        print(f"   2. Retrieve relevant Family Guy context")
        print(f"   3. Generate character-appropriate starter")
        print(f"   4. Fallback to curated prompts if needed")
    
    def show_configuration_options(self):
        """Show configuration options for organic conversations."""
        print("\n⚙️ CONFIGURATION OPTIONS")
        print("=" * 50)
        
        configs = [
            {
                "var": "CONVERSATION_SILENCE_THRESHOLD_MINUTES",
                "default": "30",
                "description": "Minutes of silence before considering new conversation"
            },
            {
                "var": "MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS", 
                "default": "10",
                "description": "Minimum minutes between organic attempts"
            },
            {
                "var": "DEFAULT_DISCORD_CHANNEL_ID",
                "default": "your_channel_id",
                "description": "Channel for organic conversations"
            }
        ]
        
        print("Add these to your .env file:")
        for config in configs:
            print(f"\n{config['var']}={config['default']}")
            print(f"# {config['description']}")
    
    def compare_with_scheduler(self):
        """Compare organic system with old scheduler."""
        print("\n📊 ORGANIC vs SCHEDULER COMPARISON")
        print("=" * 50)
        
        comparison = [
            ("Timing", "Context-driven", "Fixed schedule"),
            ("Intelligence", "LLM-powered decisions", "Random selection"),
            ("Triggers", "Natural conversation patterns", "Time intervals"),
            ("Character Selection", "Personality-aware", "Round-robin"),
            ("Resource Usage", "Lightweight monitoring", "Heavy scheduling"),
            ("Conversation Quality", "Contextual & relevant", "Generic starters"),
            ("Interruptions", "Respects active discussions", "Interrupts conversations"),
            ("Adaptability", "Learns from patterns", "Static configuration")
        ]
        
        print(f"{'Aspect':<20} {'Organic System':<25} {'Old Scheduler':<20}")
        print("-" * 65)
        for aspect, organic, scheduler in comparison:
            print(f"{aspect:<20} {organic:<25} {scheduler:<20}")
    
    def run_demo(self):
        """Run the complete demonstration."""
        print("🌱 ORGANIC CONVERSATION COORDINATOR DEMO")
        print("=" * 60)
        print("This demo showcases the intelligent conversation system")
        print("that replaced the time-based scheduler.\n")
        
        # Check if system is running
        if not self.check_orchestrator_health():
            print("\n❌ Cannot proceed with demo - orchestrator not available")
            return
        
        # Run demonstrations
        self.demonstrate_organic_triggers()
        self.demonstrate_character_selection()
        self.demonstrate_rag_enhancement()
        self.show_configuration_options()
        self.compare_with_scheduler()
        
        print("\n🎉 DEMO COMPLETE!")
        print("=" * 60)
        print("The organic conversation coordinator provides:")
        print("✅ Natural, context-driven conversation initiation")
        print("✅ Intelligent character selection using LLM")
        print("✅ RAG-enhanced conversation starters")
        print("✅ Respect for active conversations")
        print("✅ Lightweight, efficient monitoring")
        print("✅ Adaptive pattern recognition")

def main():
    """Main demo execution."""
    demo = OrganicConversationDemo()
    demo.run_demo()

if __name__ == "__main__":
    main() 