#!/usr/bin/env python3
"""
Test script for NO_FALLBACK_MODE functionality.

This script tests the new no-fallback retry system that removes all fallback responses
and instead uses infinite retry with exponential backoff until a valid response is generated.

Usage:
    python test_no_fallback_mode.py

Environment Variables:
    NO_FALLBACK_MODE=True/False - Enable/disable no-fallback mode
    MAX_RETRY_ATTEMPTS=10 - Maximum retry attempts before giving up
    RETRY_BACKOFF_ENABLED=True/False - Enable exponential backoff
    RETRY_BACKOFF_MULTIPLIER=1.5 - Backoff multiplier
"""

import os
import sys
import requests
import json
import time
from datetime import datetime

# Test configuration
ORCHESTRATOR_URL = "http://localhost:5001"
TEST_CHANNEL_ID = "test_no_fallback_123456"

def test_no_fallback_mode():
    """Test the no-fallback mode functionality"""
    print("🚫 Testing NO_FALLBACK_MODE Functionality")
    print("=" * 60)
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Normal Conversation",
            "query": "Hey everyone, what's your favorite food?",
            "expected_behavior": "Should generate valid response without fallbacks"
        },
        {
            "name": "Simple Question",
            "query": "How are you doing today?",
            "expected_behavior": "Should handle simple queries efficiently"
        },
        {
            "name": "Complex Topic",
            "query": "What do you think about the philosophical implications of artificial intelligence and consciousness?",
            "expected_behavior": "Should handle complex topics with retries if needed"
        },
        {
            "name": "Character-Specific Mention",
            "query": "@Peter Griffin what's your take on this?",
            "expected_behavior": "Should respond as Peter without fallbacks"
        },
        {
            "name": "Ambiguous Input",
            "query": "That thing we talked about earlier...",
            "expected_behavior": "Should retry until valid response or max attempts"
        }
    ]
    
    print(f"🔧 Configuration Check:")
    print(f"   NO_FALLBACK_MODE: {os.getenv('NO_FALLBACK_MODE', 'False')}")
    print(f"   MAX_RETRY_ATTEMPTS: {os.getenv('MAX_RETRY_ATTEMPTS', '10')}")
    print(f"   RETRY_BACKOFF_ENABLED: {os.getenv('RETRY_BACKOFF_ENABLED', 'True')}")
    print(f"   RETRY_BACKOFF_MULTIPLIER: {os.getenv('RETRY_BACKOFF_MULTIPLIER', '1.5')}")
    print()
    
    # Test orchestrator health first
    print("🏥 Testing Orchestrator Health...")
    try:
        health_response = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=10)
        if health_response.status_code == 200:
            print("✅ Orchestrator is healthy")
        else:
            print(f"⚠️ Orchestrator health check returned {health_response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to orchestrator: {e}")
        return False
    
    print()
    
    # Run test scenarios
    passed_tests = 0
    total_tests = len(test_scenarios)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"🧪 Test {i}/{total_tests}: {scenario['name']}")
        print(f"   Query: '{scenario['query']}'")
        print(f"   Expected: {scenario['expected_behavior']}")
        
        start_time = time.time()
        
        try:
            # Send request to orchestrator
            payload = {
                "user_query": scenario["query"],
                "channel_id": TEST_CHANNEL_ID,
                "initiator_bot_name": "Peter",
                "initiator_mention": "@Peter Griffin",
                "human_user_display_name": "TestUser",
                "original_message": scenario["query"]
            }
            
            response = requests.post(
                f"{ORCHESTRATOR_URL}/orchestrate",
                json=payload,
                timeout=120  # Longer timeout for no-fallback mode
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ SUCCESS ({duration:.1f}s)")
                print(f"   Speaker: {result.get('speaker', 'Unknown')}")
                print(f"   Status: {result.get('status', 'Unknown')}")
                print(f"   Session ID: {result.get('conversation_session_id', 'Unknown')}")
                passed_tests += 1
            elif response.status_code == 500 and "NO_FALLBACK_MODE" in response.text:
                print(f"   ⚠️ NO_FALLBACK_MODE FAILURE ({duration:.1f}s)")
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
                print(f"   Details: {error_data.get('details', 'No details')}")
                print(f"   Suggestion: {error_data.get('suggestion', 'No suggestion')}")
                print(f"   This indicates the system exhausted all retry attempts")
            else:
                print(f"   ❌ FAILED ({duration:.1f}s)")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ TIMEOUT (>120s)")
            print(f"   This may indicate the system is still retrying")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        print()
        
        # Small delay between tests
        time.sleep(2)
    
    # Summary
    print("📊 Test Results Summary")
    print("-" * 30)
    print(f"Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! NO_FALLBACK_MODE is working correctly.")
    elif passed_tests > 0:
        print("⚠️ Some tests passed. System is partially functional.")
    else:
        print("❌ All tests failed. Check system configuration.")
    
    return passed_tests == total_tests

def test_quality_control_status():
    """Test the quality control status endpoint"""
    print("\n🛡️ Testing Quality Control Status")
    print("-" * 40)
    
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/quality_control_status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Quality Control Status:")
            print(f"   Enabled: {data.get('quality_control_enabled', 'Unknown')}")
            print(f"   Min Rating: {data.get('min_rating', 'Unknown')}")
            print(f"   Max Retries: {data.get('max_retries', 'Unknown')}")
            print(f"   Adaptive Control: {data.get('adaptive_quality_control_enabled', 'Unknown')}")
            print(f"   No Fallback Mode: {data.get('no_fallback_mode', 'Unknown')}")
            print(f"   Max Retry Attempts: {data.get('max_retry_attempts', 'Unknown')}")
            return True
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return False

def test_configuration_scenarios():
    """Test different configuration scenarios"""
    print("\n⚙️ Testing Configuration Scenarios")
    print("-" * 40)
    
    scenarios = [
        {
            "name": "NO_FALLBACK_MODE=False (Traditional)",
            "env_vars": {"NO_FALLBACK_MODE": "False"},
            "expected": "Should use fallback responses when quality fails"
        },
        {
            "name": "NO_FALLBACK_MODE=True (No Fallbacks)",
            "env_vars": {"NO_FALLBACK_MODE": "True"},
            "expected": "Should retry until success or max attempts"
        },
        {
            "name": "High Retry Limit",
            "env_vars": {"NO_FALLBACK_MODE": "True", "MAX_RETRY_ATTEMPTS": "15"},
            "expected": "Should allow more retry attempts"
        },
        {
            "name": "Disabled Backoff",
            "env_vars": {"NO_FALLBACK_MODE": "True", "RETRY_BACKOFF_ENABLED": "False"},
            "expected": "Should retry immediately without delays"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n🔧 Scenario: {scenario['name']}")
        print(f"   Environment: {scenario['env_vars']}")
        print(f"   Expected: {scenario['expected']}")
        print(f"   Note: Restart orchestrator with these env vars to test")

def main():
    """Main test function"""
    print("🚫 NO_FALLBACK_MODE Test Suite")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Orchestrator URL: {ORCHESTRATOR_URL}")
    print(f"Test Channel ID: {TEST_CHANNEL_ID}")
    print()
    
    # Check if NO_FALLBACK_MODE is enabled
    no_fallback_enabled = os.getenv("NO_FALLBACK_MODE", "False").lower() == "true"
    if no_fallback_enabled:
        print("🚫 NO_FALLBACK_MODE is ENABLED")
        print("   System will retry until success or max attempts reached")
    else:
        print("🔄 NO_FALLBACK_MODE is DISABLED")
        print("   System will use traditional fallback responses")
    print()
    
    # Run tests
    success = True
    
    # Test quality control status
    if not test_quality_control_status():
        success = False
    
    # Test main functionality
    if not test_no_fallback_mode():
        success = False
    
    # Show configuration scenarios
    test_configuration_scenarios()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests completed successfully!")
    else:
        print("⚠️ Some tests failed. Check the logs above.")
    
    print("\n💡 Tips for NO_FALLBACK_MODE:")
    print("   1. Monitor logs for retry patterns")
    print("   2. Adjust MAX_RETRY_ATTEMPTS based on your needs")
    print("   3. Use RETRY_BACKOFF_ENABLED=True to prevent overwhelming the LLM")
    print("   4. Consider lowering quality thresholds if too many retries occur")
    print("   5. Disable NO_FALLBACK_MODE temporarily if system becomes unstable")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 