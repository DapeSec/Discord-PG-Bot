#!/usr/bin/env python3
"""
Diagnostic script for organic conversation coordinator issues.
Identifies why the coordinator is not initiating conversations after silence.
"""

import sys
import os
import requests
import json
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def check_orchestrator_health():
    """Check if orchestrator is running and healthy."""
    print("🔍 CHECKING ORCHESTRATOR HEALTH")
    print("=" * 50)
    
    try:
        response = requests.get("http://localhost:5003/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Orchestrator Status: {data.get('status')}")
            print(f"📊 Components: {', '.join(data.get('components', {}).keys())}")
            return True
        else:
            print(f"❌ Orchestrator unhealthy: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to orchestrator. Is it running on port 5003?")
        return False
    except Exception as e:
        print(f"❌ Error checking orchestrator: {e}")
        return False

def check_organic_conversation_status():
    """Check the organic conversation coordinator status."""
    print("\n🌱 CHECKING ORGANIC CONVERSATION STATUS")
    print("=" * 50)
    
    try:
        response = requests.get("http://localhost:5003/organic_conversation_status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            print(f"📊 Status: {data.get('status')}")
            
            config = data.get('configuration', {})
            print(f"\n⚙️ Configuration:")
            print(f"   🔄 Follow-up conversations: {config.get('follow_up_conversations_enabled')}")
            print(f"   ⏱️ Follow-up delay: {config.get('follow_up_delay_seconds')}s")
            print(f"   🕐 Min time between follow-ups: {config.get('min_time_between_follow_ups')}s")
            print(f"   🤫 Silence threshold: {config.get('conversation_silence_threshold_minutes')} minutes")
            print(f"   ⏰ Min time between organic: {config.get('min_time_between_organic_conversations')} minutes")
            
            activity = data.get('recent_activity_24h', {})
            print(f"\n📈 Recent Activity (24h):")
            print(f"   🔄 Follow-up conversations: {activity.get('follow_up_conversations')}")
            print(f"   🌱 Organic conversations: {activity.get('organic_conversations')}")
            print(f"   🤖 Total bot messages: {activity.get('total_bot_messages')}")
            
            state = data.get('coordinator_state', {})
            print(f"\n🎯 Coordinator State:")
            print(f"   🔄 Last follow-up attempt: {state.get('last_follow_up_attempt') or 'Never'}")
            print(f"   🌱 Last organic attempt: {state.get('last_organic_attempt') or 'Never'}")
            
            return data
        else:
            print(f"❌ Failed to get status: HTTP {response.status_code}")
            if response.text:
                print(f"   Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error checking organic conversation status: {e}")
        return None

def check_environment_variables():
    """Check critical environment variables."""
    print("\n🔧 CHECKING ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    # Try to import the configuration from the orchestrator
    try:
        from app.orchestrator.server import (
            DEFAULT_DISCORD_CHANNEL_ID,
            CONVERSATION_SILENCE_THRESHOLD_MINUTES,
            MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS,
            ENABLE_FOLLOW_UP_CONVERSATIONS,
            FOLLOW_UP_DELAY_SECONDS,
            MIN_TIME_BETWEEN_FOLLOW_UPS
        )
        
        print(f"📺 DEFAULT_DISCORD_CHANNEL_ID: {DEFAULT_DISCORD_CHANNEL_ID}")
        print(f"🤫 CONVERSATION_SILENCE_THRESHOLD_MINUTES: {CONVERSATION_SILENCE_THRESHOLD_MINUTES}")
        print(f"⏰ MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS: {MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS}")
        print(f"🔄 ENABLE_FOLLOW_UP_CONVERSATIONS: {ENABLE_FOLLOW_UP_CONVERSATIONS}")
        print(f"⏱️ FOLLOW_UP_DELAY_SECONDS: {FOLLOW_UP_DELAY_SECONDS}")
        print(f"🕐 MIN_TIME_BETWEEN_FOLLOW_UPS: {MIN_TIME_BETWEEN_FOLLOW_UPS}")
        
        # Check for critical missing values
        issues = []
        if not DEFAULT_DISCORD_CHANNEL_ID:
            issues.append("❌ DEFAULT_DISCORD_CHANNEL_ID is not set!")
        
        if CONVERSATION_SILENCE_THRESHOLD_MINUTES <= 0:
            issues.append(f"❌ Invalid silence threshold: {CONVERSATION_SILENCE_THRESHOLD_MINUTES}")
        
        if MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS <= 0:
            issues.append(f"❌ Invalid min time between organic: {MIN_TIME_BETWEEN_ORGANIC_CONVERSATIONS}")
        
        if issues:
            print(f"\n⚠️ CONFIGURATION ISSUES:")
            for issue in issues:
                print(f"   {issue}")
            return False
        else:
            print(f"\n✅ All environment variables look good!")
            return True
            
    except ImportError as e:
        print(f"❌ Cannot import orchestrator configuration: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking environment variables: {e}")
        return False

def simulate_silence_check():
    """Simulate what the organic conversation coordinator would check."""
    print("\n🧪 SIMULATING SILENCE CHECK")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import (
            DEFAULT_DISCORD_CHANNEL_ID,
            CONVERSATION_SILENCE_THRESHOLD_MINUTES,
            conversations_collection
        )
        from datetime import datetime, timedelta
        
        if not DEFAULT_DISCORD_CHANNEL_ID:
            print("❌ Cannot simulate - DEFAULT_DISCORD_CHANNEL_ID not set")
            return False
        
        print(f"🔍 Checking channel: {DEFAULT_DISCORD_CHANNEL_ID}")
        print(f"🕐 Silence threshold: {CONVERSATION_SILENCE_THRESHOLD_MINUTES} minutes")
        
        now = datetime.now()
        recent_cutoff = now - timedelta(minutes=CONVERSATION_SILENCE_THRESHOLD_MINUTES)
        
        print(f"📅 Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Looking for messages after: {recent_cutoff.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check for recent messages
        recent_messages = list(conversations_collection.find({
            "channel_id": DEFAULT_DISCORD_CHANNEL_ID,
            "timestamp": {"$gte": recent_cutoff}
        }).sort("timestamp", -1))
        
        print(f"📊 Recent messages found: {len(recent_messages)}")
        
        if recent_messages:
            print("❌ Recent activity detected - organic conversation would NOT start")
            print("   Recent messages:")
            for i, msg in enumerate(recent_messages[:3]):
                timestamp = msg['timestamp'].strftime('%H:%M:%S')
                role = msg.get('role', 'unknown')
                name = msg.get('name', 'Unknown')
                content = msg.get('content', '')[:50] + '...' if len(msg.get('content', '')) > 50 else msg.get('content', '')
                print(f"   {i+1}. [{timestamp}] {role} ({name}): {content}")
            return False
        else:
            print("✅ No recent activity - organic conversation SHOULD start")
            
            # Check for last message
            last_message = conversations_collection.find_one(
                {"channel_id": DEFAULT_DISCORD_CHANNEL_ID},
                sort=[("timestamp", -1)]
            )
            
            if last_message:
                silence_duration = (now - last_message["timestamp"]).total_seconds() / 60
                print(f"🤫 Silence duration: {silence_duration:.1f} minutes")
                
                if silence_duration > CONVERSATION_SILENCE_THRESHOLD_MINUTES:
                    print(f"✅ Silence duration ({silence_duration:.1f} min) > threshold ({CONVERSATION_SILENCE_THRESHOLD_MINUTES} min)")
                    print("🌱 Organic conversation SHOULD be initiated!")
                    return True
                else:
                    print(f"❌ Silence duration ({silence_duration:.1f} min) < threshold ({CONVERSATION_SILENCE_THRESHOLD_MINUTES} min)")
                    return False
            else:
                print("❌ No messages found in channel at all")
                return False
                
    except Exception as e:
        print(f"❌ Error simulating silence check: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_mongodb_connection():
    """Check MongoDB connection and data."""
    print("\n🗄️ CHECKING MONGODB CONNECTION")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import mongo_client, conversations_collection
        
        if not mongo_client:
            print("❌ MongoDB client is None")
            return False
        
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Check conversations collection
        total_messages = conversations_collection.count_documents({})
        print(f"📊 Total messages in database: {total_messages}")
        
        # Check recent messages
        recent_messages = list(conversations_collection.find().sort("timestamp", -1).limit(5))
        print(f"📊 Recent messages: {len(recent_messages)}")
        
        if recent_messages:
            print("   Last few messages:")
            for i, msg in enumerate(recent_messages):
                timestamp = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                role = msg.get('role', 'unknown')
                name = msg.get('name', 'Unknown')
                channel = msg.get('channel_id', 'Unknown')
                print(f"   {i+1}. [{timestamp}] {role} ({name}) in {channel}")
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        return False

def check_monitor_thread_status():
    """Check if the organic conversation monitor thread is running."""
    print("\n🧵 CHECKING MONITOR THREAD STATUS")
    print("=" * 50)
    
    import threading
    
    # List all active threads
    active_threads = threading.enumerate()
    print(f"📊 Total active threads: {len(active_threads)}")
    
    monitor_thread_found = False
    for thread in active_threads:
        print(f"   🧵 {thread.name}: {'daemon' if thread.daemon else 'main'}, alive: {thread.is_alive()}")
        
        # Look for organic conversation monitor thread
        if 'organic' in thread.name.lower() or thread.name == 'Thread-3':  # Common name for daemon threads
            monitor_thread_found = True
            print(f"   🌱 Potential organic monitor thread found: {thread.name}")
    
    if not monitor_thread_found:
        print("❌ No obvious organic conversation monitor thread found")
        print("   This could indicate the thread crashed or was never started")
    
    return monitor_thread_found

def main():
    """Run all diagnostic checks."""
    print("🔍 ORGANIC CONVERSATION COORDINATOR DIAGNOSTICS")
    print("=" * 60)
    
    checks = [
        ("Orchestrator Health", check_orchestrator_health),
        ("Environment Variables", check_environment_variables),
        ("MongoDB Connection", check_mongodb_connection),
        ("Monitor Thread Status", check_monitor_thread_status),
        ("Organic Conversation Status", check_organic_conversation_status),
        ("Silence Check Simulation", simulate_silence_check),
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        print(f"\n" + "="*60)
        try:
            result = check_func()
            results[check_name] = result
            print(f"✅ {check_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {check_name}: ERROR - {e}")
            results[check_name] = False
    
    print(f"\n" + "="*60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
    
    print(f"\n📈 Overall: {passed}/{total} checks passed")
    
    if passed < total:
        print(f"\n🔧 RECOMMENDED ACTIONS:")
        
        if not results.get("Orchestrator Health"):
            print("   1. Start the orchestrator service: docker-compose up orchestrator")
        
        if not results.get("Environment Variables"):
            print("   2. Check your .env file for DEFAULT_DISCORD_CHANNEL_ID")
        
        if not results.get("MongoDB Connection"):
            print("   3. Start MongoDB: docker-compose up mongodb")
        
        if not results.get("Monitor Thread Status"):
            print("   4. Restart orchestrator to reinitialize monitor thread")
        
        if not results.get("Silence Check Simulation"):
            print("   5. Wait for the silence threshold period or manually trigger")
    else:
        print(f"\n🎉 All checks passed! The organic conversation coordinator should be working.")
        print(f"   If it's still not working, check the orchestrator logs for errors.")

if __name__ == "__main__":
    main() 