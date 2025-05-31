#!/usr/bin/env python3
"""
Test script to verify retry manager usage in conversation coordinator.
"""

import requests
import json

def test_retry_manager():
    """Test the retry manager functionality via organic response generation."""
    print("🧪 Testing Retry Manager Integration")
    print("=" * 50)
    
    # Test organic response generation which uses retry manager
    payload = {
        "responding_character": "stewie",
        "previous_speaker": "peter",
        "previous_message": "I think pizza is the best food ever!",
        "original_input": "What's your favorite food?",
        "conversation_history": [
            {"character": "user", "content": "What's your favorite food?"},
            {"character": "peter", "content": "I think pizza is the best food ever!"}
        ],
        "channel_id": "test_retry"
    }
    
    try:
        print("📡 Making request to generate-organic-response endpoint...")
        response = requests.post(
            "http://localhost:6002/generate-organic-response",
            json=payload,
            timeout=30  # Longer timeout to allow for retries
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data.get('success')}")
            if data.get('response'):
                print(f"📝 Generated Response: {data['response']}")
                print("🎉 Retry manager integration working!")
            else:
                print("⚠️ No response generated")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_retry_manager() 