import requests
import json

# Simple test
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
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        analysis = data.get("analysis", {})
        
        print(f"Continue: {analysis.get('continue')}")
        print(f"Reason: {analysis.get('reason')}")
        print(f"Character: {analysis.get('suggested_character')}")
        
        if analysis.get('continue'):
            print("🎉 SUCCESS: Conversation continuation is working and being PERMISSIVE!")
        else:
            print("⚠️  Conversation ended")
        
except Exception as e:
    print(f"Error: {e}") 