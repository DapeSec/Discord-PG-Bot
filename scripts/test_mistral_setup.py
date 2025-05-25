#!/usr/bin/env python3
"""
Test script for local Mistral setup
Verifies that Ollama and Mistral 4070 are properly configured
"""

import os
import requests
import json
import sys
from datetime import datetime

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-nemo")

def test_ollama_connection():
    """Test if Ollama is running and accessible."""
    print("🔍 Testing Ollama connection...")
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            print("✅ Ollama is running and accessible")
            return True
        else:
            print(f"❌ Ollama responded with status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        print(f"   Make sure Ollama is running: ollama serve")
        return False

def test_mistral_model_available():
    """Test if Mistral 4070 model is available."""
    print(f"🔍 Testing if {OLLAMA_MODEL} model is available...")
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json()
            available_models = [model['name'] for model in models.get('models', [])]
            
            if OLLAMA_MODEL in available_models:
                print(f"✅ {OLLAMA_MODEL} model is available")
                return True
            else:
                print(f"❌ {OLLAMA_MODEL} model not found")
                print(f"   Available models: {available_models}")
                print(f"   Download with: ollama pull {OLLAMA_MODEL}")
                return False
        else:
            print(f"❌ Failed to get model list: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to check models: {e}")
        return False

def test_mistral_response():
    """Test Mistral model response generation."""
    print(f"🔍 Testing {OLLAMA_MODEL} response generation...")
    
    test_prompt = """You are Peter Griffin from Family Guy. You must stay in character.

User: Hello Peter! How are you today?
Peter:"""
    
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": test_prompt,
            "stream": False,
            "options": {
                "temperature": 0.9,
                "num_predict": 100,
                "stop": ["User:", "Human:"]
            }
        }
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('response', '').strip()
            
            if generated_text:
                print(f"✅ {OLLAMA_MODEL} generated response successfully")
                print(f"📝 Sample response: {generated_text[:100]}...")
                return True
            else:
                print(f"❌ {OLLAMA_MODEL} returned empty response")
                return False
        else:
            print(f"❌ {OLLAMA_MODEL} API error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to test {OLLAMA_MODEL} response: {e}")
        return False

def test_character_responses():
    """Test character-specific responses."""
    print("🔍 Testing character-specific responses...")
    
    characters = {
        "Peter": {
            "prompt": "You are Peter Griffin. User: What's your favorite thing to do? Peter:",
            "expected_phrases": ["holy crap", "freakin", "chicken fight", "beer"]
        },
        "Brian": {
            "prompt": "You are Brian Griffin. User: What do you think about literature? Brian:",
            "expected_phrases": ["intellectual", "writing", "novel", "sophisticated"]
        },
        "Stewie": {
            "prompt": "You are Stewie Griffin. User: What are your plans? Stewie:",
            "expected_phrases": ["victory", "deuce", "world domination", "blast"]
        }
    }
    
    all_passed = True
    
    for character, config in characters.items():
        print(f"  🎭 Testing {character}...")
        
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": config["prompt"],
                "stream": False,
                "options": {
                    "temperature": 0.9,
                    "num_predict": 80,
                    "stop": ["User:", "Human:"]
                }
            }
            
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '').strip().lower()
                
                # Check if response contains character-appropriate content
                contains_character_content = any(
                    phrase in generated_text 
                    for phrase in config["expected_phrases"]
                )
                
                if generated_text and len(generated_text) > 10:
                    print(f"    ✅ {character} response: {generated_text[:60]}...")
                    if contains_character_content:
                        print(f"    ✅ Response contains character-appropriate content")
                    else:
                        print(f"    ⚠️  Response may not be character-specific")
                else:
                    print(f"    ❌ {character} response too short or empty")
                    all_passed = False
            else:
                print(f"    ❌ {character} API error: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"    ❌ {character} test failed: {e}")
            all_passed = False
    
    return all_passed

def test_docker_services():
    """Test if Docker services are healthy."""
    print("🔍 Testing Docker services...")
    
    services = {
        "Orchestrator": "http://localhost:5003/health",
        "Discord Handler": "http://localhost:5001/health",
        "Peter Config": "http://localhost:5005/health",
        "Brian Config": "http://localhost:5006/health",
        "Stewie Config": "http://localhost:5007/health"
    }
    
    all_healthy = True
    
    for service_name, health_url in services.items():
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                print(f"  ✅ {service_name}: {status}")
            else:
                print(f"  ❌ {service_name}: HTTP {response.status_code}")
                all_healthy = False
        except requests.exceptions.RequestException:
            print(f"  ⚠️  {service_name}: Not accessible (may not be running)")
            all_healthy = False
    
    return all_healthy

def main():
    """Run all tests."""
    print("🚀 Discord Family Guy Bot - Local Mistral Setup Test")
    print("=" * 60)
    print(f"📍 Ollama URL: {OLLAMA_BASE_URL}")
    print(f"🤖 Model: {OLLAMA_MODEL}")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("Mistral Model Availability", test_mistral_model_available),
        ("Mistral Response Generation", test_mistral_response),
        ("Character-Specific Responses", test_character_responses),
        ("Docker Services", test_docker_services)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<8} {test_name}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your local Mistral setup is ready!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 