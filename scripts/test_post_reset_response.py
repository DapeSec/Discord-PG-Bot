#!/usr/bin/env python3
"""
Test script for post-database-reset response quality.
Simulates the exact scenario where Brian responds after database reset.
"""

import sys
import os
import requests
import json
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_post_reset_response():
    """Test Brian's response quality after database reset."""
    print("🧪 TESTING POST-RESET RESPONSE QUALITY")
    print("=" * 60)
    
    # Simulate the exact request from the screenshot
    test_data = {
        "character": "Brian",
        "user_query": "Do you cook?",
        "channel_id": "1374667208134885416",
        "user_id": "test_user",
        "username": "Dape"
    }
    
    print(f"📝 Test Query: '{test_data['user_query']}'")
    print(f"🎭 Character: {test_data['character']}")
    print(f"📺 Channel: {test_data['channel_id']}")
    
    try:
        print("\n🔄 Sending request to orchestrator...")
        response = requests.post(
            "http://localhost:5003/orchestrate",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Request successful!")
            print(f"📊 Response: {json.dumps(result, indent=2)}")
            
            # Analyze the response
            if 'response' in result:
                response_text = result['response']
                print(f"\n📝 Generated Response: '{response_text}'")
                
                # Check for quality issues
                quality_issues = []
                
                if "drawing a blank" in response_text.lower():
                    quality_issues.append("❌ Generic 'drawing a blank' response")
                
                if "*sighs*" in response_text:
                    quality_issues.append("❌ Overuse of action descriptions")
                
                if len(response_text) < 20:
                    quality_issues.append("❌ Response too short")
                
                if "ugh" in response_text.lower():
                    quality_issues.append("❌ Negative/dismissive tone")
                
                if quality_issues:
                    print("\n🚨 QUALITY ISSUES DETECTED:")
                    for issue in quality_issues:
                        print(f"   {issue}")
                else:
                    print("\n✅ Response quality looks good!")
                    
            # Check quality control info
            if 'quality_control' in result:
                qc_info = result['quality_control']
                print(f"\n📊 Quality Control Info:")
                print(f"   Score: {qc_info.get('score', 'N/A')}")
                print(f"   Attempts: {qc_info.get('attempts', 'N/A')}")
                print(f"   Passed: {qc_info.get('passed', 'N/A')}")
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to orchestrator. Is it running?")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_quality_control_threshold():
    """Test if the quality control threshold is working properly."""
    print("\n🎯 TESTING QUALITY CONTROL THRESHOLD")
    print("=" * 60)
    
    try:
        from app.orchestrator.server import QUALITY_CONTROL_MIN_RATING
        print(f"📊 Current threshold: {QUALITY_CONTROL_MIN_RATING}")
        
        if QUALITY_CONTROL_MIN_RATING == 70.0:
            print("✅ Threshold correctly set to 70.0")
        else:
            print(f"⚠️ Threshold is {QUALITY_CONTROL_MIN_RATING}, expected 70.0")
            
    except ImportError:
        print("❌ Cannot import quality control settings")

def test_empty_database_scenario():
    """Test how the system handles empty database scenario."""
    print("\n🗄️ TESTING EMPTY DATABASE SCENARIO")
    print("=" * 60)
    
    try:
        # Test MongoDB connection
        response = requests.get("http://localhost:5003/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Orchestrator is healthy")
            
            # Check if MongoDB is connected
            if 'mongodb' in health_data:
                print(f"📊 MongoDB status: {health_data['mongodb']}")
            else:
                print("⚠️ No MongoDB status in health check")
        else:
            print("❌ Orchestrator health check failed")
            
    except Exception as e:
        print(f"❌ Health check error: {e}")

def main():
    """Run all tests."""
    print("🧪 POST-DATABASE-RESET RESPONSE TESTING")
    print("=" * 60)
    print("Testing Brian's response quality after database reset...")
    print()
    
    test_quality_control_threshold()
    test_empty_database_scenario()
    test_post_reset_response()
    
    print("\n" + "=" * 60)
    print("🎯 RECOMMENDATIONS:")
    print("1. If responses are generic, the quality control may be too strict")
    print("2. Consider lowering threshold temporarily for cold starts")
    print("3. Check if RAG context is providing relevant information")
    print("4. Verify character prompts are working properly")

if __name__ == "__main__":
    main() 