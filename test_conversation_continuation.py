#!/usr/bin/env python3
"""
Test script to verify conversation continuation logic is less strict.
"""

import requests
import json

def test_conversation_continuation():
    """Test that conversation continuation is now more permissive."""
    print("🧪 Testing Conversation Continuation Logic")
    print("=" * 50)
    
    # Test cases that should now continue (previously might have ended)
    test_cases = [
        {
            "name": "TV Show Discussion",
            "conversation_history": [
                {"character": "user", "content": "What's your favorite TV show?"},
                {"character": "peter", "content": "Oh man, I love watching TV! My favorite show is probably the news because it's so funny when they talk about politics."},
                {"character": "stewie", "content": "Peter, your grandiose plans or try to one-up him with his own outlandish ideas."}
            ],
            "responding_character": "stewie",
            "response_text": "Peter, your taste in television is about as sophisticated as a potato's understanding of quantum physics.",
            "channel_id": "test_channel_123"
        },
        {
            "name": "Food Debate",
            "conversation_history": [
                {"character": "user", "content": "Pizza or burgers?"},
                {"character": "peter", "content": "Are you kidding me? Pizza! You can put anything on pizza!"},
                {"character": "brian", "content": "Well, actually, I think there's something to be said for a well-crafted burger..."}
            ],
            "responding_character": "brian",
            "response_text": "The artistry of a properly constructed burger cannot be understated.",
            "channel_id": "test_channel_123"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🎯 Test Case: {test_case['name']}")
        print("-" * 30)
        
        try:
            # Test conversation continuation analysis
            response = requests.post(
                "http://localhost:6002/analyze-conversation-continuation",
                json={
                    "conversation_history": test_case["conversation_history"],
                    "responding_character": test_case["responding_character"],
                    "response_text": test_case["response_text"],
                    "channel_id": test_case["channel_id"]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                should_continue = data.get("continue", False)
                reason = data.get("reason", "No reason provided")
                suggested_character = data.get("suggested_character", "None")
                
                status = "✅ CONTINUE" if should_continue else "❌ END"
                print(f"   Decision: {status}")
                print(f"   Reason: {reason}")
                print(f"   Suggested Character: {suggested_character}")
                
                if should_continue:
                    print(f"   ✅ Success: Conversation will continue (less strict!)")
                else:
                    print(f"   ⚠️  Notice: Conversation ended - {reason}")
                    
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("   ❌ Error: Cannot connect to conversation coordinator")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🎉 Test completed! The conversation continuation logic should now be more permissive.")
    print("Expected: Most conversations should continue unless explicitly ended.")

if __name__ == "__main__":
    test_conversation_continuation() 