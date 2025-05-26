#!/usr/bin/env python3
"""
Manual trigger script for organic conversations.
Allows testing the organic conversation system by manually initiating conversations.
"""

import sys
import os
import requests
import json
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def trigger_organic_conversation(channel_id=None):
    """Manually trigger an organic conversation."""
    print("🌱 MANUAL ORGANIC CONVERSATION TRIGGER")
    print("=" * 50)
    
    # Get channel ID from environment if not provided
    if not channel_id:
        try:
            from app.orchestrator.server import DEFAULT_DISCORD_CHANNEL_ID
            channel_id = DEFAULT_DISCORD_CHANNEL_ID
        except ImportError:
            print("❌ Cannot import DEFAULT_DISCORD_CHANNEL_ID")
            return False
    
    if not channel_id:
        print("❌ No channel ID provided and DEFAULT_DISCORD_CHANNEL_ID not set")
        return False
    
    print(f"📺 Target channel: {channel_id}")
    
    # Try to directly call the organic coordinator
    try:
        from app.orchestrator.server import organic_coordinator
        
        print("🔍 Checking if organic conversation should start...")
        should_start = organic_coordinator.should_start_organic_conversation(channel_id)
        print(f"📊 Should start organic conversation: {should_start}")
        
        if should_start:
            print("🌱 Initiating organic conversation...")
            success = organic_coordinator.initiate_organic_conversation(channel_id)
            if success:
                print("✅ Organic conversation initiated successfully!")
                return True
            else:
                print("❌ Failed to initiate organic conversation")
                return False
        else:
            print("⚠️ Organic conversation coordinator says it shouldn't start")
            print("   This could be due to:")
            print("   - Recent activity in the channel")
            print("   - Too soon since last organic attempt")
            print("   - Other timing constraints")
            
            # Force trigger anyway
            print("\n🔧 Attempting to force trigger...")
            success = organic_coordinator.initiate_organic_conversation(channel_id)
            if success:
                print("✅ Force trigger successful!")
                return True
            else:
                print("❌ Force trigger failed")
                return False
                
    except ImportError as e:
        print(f"❌ Cannot import organic coordinator: {e}")
        return False
    except Exception as e:
        print(f"❌ Error triggering organic conversation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversation_starter_generation():
    """Test the conversation starter generation system."""
    print("\n🎭 TESTING CONVERSATION STARTER GENERATION")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import (
            generate_conversation_starter,
            select_conversation_initiator_intelligently,
            BOT_CONFIGS
        )
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Create some fake recent history
        recent_history = [
            HumanMessage(content="Hey everyone, what's up?"),
            AIMessage(content="Hehehe, not much! Just watching TV.", name="Peter"),
            HumanMessage(content="Cool, what show?"),
            AIMessage(content="Some documentary about quantum physics. Fascinating stuff.", name="Brian")
        ]
        
        print("📚 Testing with sample conversation history...")
        
        # Test intelligent character selection
        print("\n🎯 Testing intelligent character selection...")
        selected_character = select_conversation_initiator_intelligently(recent_history)
        if selected_character:
            print(f"✅ Selected character: {selected_character}")
        else:
            print("❌ Character selection failed, using fallback")
            selected_character = "Stewie"
        
        # Test conversation starter generation
        print(f"\n💬 Testing conversation starter generation for {selected_character}...")
        starter = generate_conversation_starter(selected_character, recent_history)
        
        if starter:
            print(f"✅ Generated starter: '{starter}'")
            return True
        else:
            print("❌ Failed to generate conversation starter")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import required functions: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing conversation starter generation: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_timing_constraints():
    """Check current timing constraints for organic conversations."""
    print("\n⏰ CHECKING TIMING CONSTRAINTS")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import (
            organic_coordinator,
            MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS,
            CONVERSATION_SILENCE_THRESHOLD_MINUTES
        )
        from datetime import datetime, timedelta
        
        now = datetime.now()
        print(f"📅 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check last organic attempt
        if organic_coordinator.last_organic_attempt:
            time_since_last = (now - organic_coordinator.last_organic_attempt).total_seconds() / 60
            print(f"🌱 Last organic attempt: {organic_coordinator.last_organic_attempt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏰ Time since last attempt: {time_since_last:.1f} minutes")
            print(f"📏 Minimum required: {MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS} minutes")
            
            if time_since_last >= MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS:
                print("✅ Timing constraint satisfied")
            else:
                remaining = MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS - time_since_last
                print(f"❌ Must wait {remaining:.1f} more minutes")
        else:
            print("🌱 No previous organic attempts recorded")
            print("✅ Timing constraint satisfied (first attempt)")
        
        # Check follow-up attempt
        if organic_coordinator.last_follow_up_attempt:
            time_since_followup = (now - organic_coordinator.last_follow_up_attempt).total_seconds() / 60
            print(f"🔄 Last follow-up attempt: {organic_coordinator.last_follow_up_attempt.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏰ Time since last follow-up: {time_since_followup:.1f} minutes")
        else:
            print("🔄 No previous follow-up attempts recorded")
        
        print(f"\n📊 Configuration:")
        print(f"   🤫 Silence threshold: {CONVERSATION_SILENCE_THRESHOLD_MINUTES} minutes")
        print(f"   ⏰ Min time between organic: {MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS} minutes")
        
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import timing configuration: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking timing constraints: {e}")
        return False

def reset_timing_constraints():
    """Reset timing constraints to allow immediate organic conversation."""
    print("\n🔄 RESETTING TIMING CONSTRAINTS")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import organic_coordinator
        
        print("⚠️ Resetting last attempt timestamps...")
        organic_coordinator.last_organic_attempt = None
        organic_coordinator.last_follow_up_attempt = None
        
        print("✅ Timing constraints reset!")
        print("   Organic conversations can now be triggered immediately")
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import organic coordinator: {e}")
        return False
    except Exception as e:
        print(f"❌ Error resetting timing constraints: {e}")
        return False

def main():
    """Main function with interactive menu."""
    print("🌱 ORGANIC CONVERSATION TRIGGER TOOL")
    print("=" * 50)
    
    while True:
        print("\n📋 Available Actions:")
        print("1. 🔍 Check timing constraints")
        print("2. 🧪 Test conversation starter generation")
        print("3. 🌱 Trigger organic conversation")
        print("4. 🔄 Reset timing constraints")
        print("5. 🚪 Exit")
        
        choice = input("\nSelect an action (1-5): ").strip()
        
        if choice == "1":
            check_timing_constraints()
        elif choice == "2":
            test_conversation_starter_generation()
        elif choice == "3":
            trigger_organic_conversation()
        elif choice == "4":
            if reset_timing_constraints():
                print("✅ You can now trigger organic conversations immediately")
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    main() 