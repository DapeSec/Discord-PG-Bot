#!/usr/bin/env python3
"""
Test script to verify the exact response format from conversation continuation endpoint.
"""

import requests
import json

def test_response_format():
    """Test the response format of conversation continuation."""
    print("🧪 Testing Response Format")
    print("=" * 40)
    
    payload = {
        "conversation_history": [{"character": "peter", "content": "Pizza is the best!"}],
        "responding_character": "peter", 
        "response_text": "Pizza is amazing!",
        "channel_id": "test"
    }
    
    try:
        response = requests.post(
            "http://localhost:6002/analyze-conversation-continuation",
            json=payload,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Raw Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nParsed JSON:")
            print(json.dumps(data, indent=2))
            
            # Check the structure
            if "success" in data and data["success"]:
                analysis = data.get("analysis", {})
                print(f"\n✅ Success: {data['success']}")
                print(f"Continue: {analysis.get('continue')}")
                print(f"Reason: {analysis.get('reason')}")
                print(f"Character: {analysis.get('suggested_character')}")
                print(f"Analysis Type: {analysis.get('analysis_type')}")
                
                if analysis.get('continue'):
                    print("🎉 Conversation continuation is working!")
                else:
                    print("⚠️ Conversation ended")
            else:
                print(f"❌ Request failed: {data}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_response_format() 