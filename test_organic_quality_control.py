#!/usr/bin/env python3
"""
Test script to verify organic response quality control implementation.
"""

import requests
import json
import time

def test_quality_control_organic_response():
    """Test that organic responses go through quality control with enhanced validation."""
    print("🧪 Testing Organic Response Quality Control")
    print("=" * 50)
    
    # Test data - simulating an organic response
    test_cases = [
        {
            "name": "Good Organic Response",
            "data": {
                "response": "Yeah, totally agree! Pizza is amazing.",
                "character": "peter",
                "conversation_id": "test_channel_123",
                "context": "I think pizza is the greatest invention ever",
                "last_speaker": "brian",
                "message_type": "organic_response"
            },
            "should_pass": True
        },
        {
            "name": "Bad Organic Response - Self Response",
            "data": {
                "response": "And another thing about pizza...",
                "character": "peter",
                "conversation_id": "test_channel_123",
                "context": "I think pizza is the greatest invention ever",
                "last_speaker": "peter",  # Same character responding to self
                "message_type": "organic_response"
            },
            "should_pass": False
        },
        {
            "name": "Bad Organic Response - Stage Directions",
            "data": {
                "response": "(chuckles loudly) That's so true!",
                "character": "brian",
                "conversation_id": "test_channel_123",
                "context": "Books are amazing",
                "last_speaker": "stewie",
                "message_type": "organic_response"
            },
            "should_pass": False
        },
        {
            "name": "Bad Organic Response - Context Ignorance",
            "data": {
                "response": "I love chicken fights!",
                "character": "peter",
                "conversation_id": "test_channel_123",
                "context": "The quantum physics equations are fascinating",
                "last_speaker": "stewie",
                "message_type": "organic_response"
            },
            "should_pass": False
        },
        {
            "name": "Regular Direct Response (for comparison)",
            "data": {
                "response": "That's an interesting perspective on quantum mechanics.",
                "character": "brian",
                "conversation_id": "test_channel_123",
                "context": "The quantum physics equations are fascinating",
                "last_speaker": "stewie",
                "message_type": "direct"
            },
            "should_pass": True
        }
    ]
    
    # Quality control service URL
    quality_control_url = "http://localhost:6003/analyze"
    
    print(f"🔗 Testing against: {quality_control_url}")
    print()
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"  Character: {test_case['data']['character']}")
        print(f"  Type: {test_case['data']['message_type']}")
        print(f"  Expected: {'PASS' if test_case['should_pass'] else 'FAIL'}")
        
        try:
            # Send request to quality control
            response = requests.post(
                quality_control_url,
                json=test_case['data'],
                timeout=15
            )
            
            if response.status_code == 200:
                analysis = response.json()
                quality_passed = analysis.get('quality_check_passed', False)
                overall_score = analysis.get('overall_score', 0)
                is_organic = analysis.get('is_organic_response', False)
                threshold = analysis.get('adaptive_threshold', 70)
                
                # Check if result matches expectation
                test_passed = (quality_passed == test_case['should_pass'])
                
                print(f"  Result: {'PASS' if quality_passed else 'FAIL'} (Score: {overall_score}/{threshold})")
                print(f"  Organic Processing: {is_organic}")
                print(f"  Test Status: {'✅ CORRECT' if test_passed else '❌ UNEXPECTED'}")
                
                # Show violations if any
                violations = analysis.get('character_analysis', {}).get('violations', [])
                if violations:
                    print(f"  Violations: {violations}")
                
                # Show organic flow validation if present
                organic_flow = analysis.get('conversation_flow', {}).get('organic_flow_validation', {})
                if organic_flow:
                    print(f"  Organic Flow: {organic_flow}")
                
                results.append({
                    'test': test_case['name'],
                    'expected': test_case['should_pass'],
                    'actual': quality_passed,
                    'correct': test_passed,
                    'score': overall_score,
                    'organic': is_organic
                })
                
            else:
                print(f"  ❌ ERROR: HTTP {response.status_code}")
                print(f"  Response: {response.text}")
                results.append({
                    'test': test_case['name'],
                    'expected': test_case['should_pass'],
                    'actual': 'ERROR',
                    'correct': False,
                    'score': 0,
                    'organic': False
                })
                
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
            results.append({
                'test': test_case['name'],
                'expected': test_case['should_pass'],
                'actual': 'EXCEPTION',
                'correct': False,
                'score': 0,
                'organic': False
            })
        
        print()
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("📊 Test Summary")
    print("=" * 50)
    
    total_tests = len(results)
    correct_tests = sum(1 for r in results if r['correct'])
    organic_tests = sum(1 for r in results if r['organic'])
    
    print(f"Total Tests: {total_tests}")
    print(f"Correct Results: {correct_tests}/{total_tests}")
    print(f"Organic Processing Detected: {organic_tests}")
    print(f"Success Rate: {correct_tests/total_tests*100:.1f}%")
    
    if correct_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Organic quality control is working correctly.")
    else:
        print(f"\n⚠️ {total_tests - correct_tests} tests failed. Check implementation.")
    
    # Detailed results
    print("\n📋 Detailed Results:")
    for result in results:
        status = "✅" if result['correct'] else "❌"
        print(f"  {status} {result['test']}: Expected {result['expected']}, Got {result['actual']} (Score: {result['score']})")
    
    return results

if __name__ == "__main__":
    print("🔍 Organic Response Quality Control Test")
    print("Testing enhanced quality control for organic responses...")
    print()
    
    # Wait a moment for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(2)
    
    try:
        results = test_quality_control_organic_response()
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user.")
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc() 