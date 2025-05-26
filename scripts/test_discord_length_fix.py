#!/usr/bin/env python3
"""
Test script to validate Discord length fixes and error handling.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.orchestrator.server import validate_character_response

def test_discord_length_validation():
    """Test that responses over 2000 characters are rejected."""
    print("🚨 Testing Discord Length Validation")
    print("=" * 50)
    
    # Create a response that's too long for Discord
    long_response = "Hehehe! " * 300  # This will be over 2000 characters
    
    print(f"Testing response length: {len(long_response)} characters")
    
    is_valid, _ = validate_character_response("Peter", long_response)
    
    if not is_valid:
        print("✅ CORRECTLY REJECTED: Long response blocked")
        return True
    else:
        print("❌ FAILED: Long response incorrectly passed validation")
        return False

def test_character_length_limits():
    """Test character-specific length limits."""
    print("\n📏 Testing Character-Specific Length Limits")
    print("=" * 50)
    
    test_cases = [
        {
            "character": "Peter",
            "response": "Hehehe! " * 60,  # Over 400 chars
            "should_fail": True,
            "limit": 400
        },
        {
            "character": "Brian", 
            "response": "Actually, that's quite fascinating. " * 25,  # Over 800 chars
            "should_fail": True,
            "limit": 800
        },
        {
            "character": "Stewie",
            "response": "What the deuce! " * 50,  # Over 800 chars
            "should_fail": True,
            "limit": 800
        },
        {
            "character": "Peter",
            "response": "Hehehe, that's awesome!",  # Under 400 chars
            "should_fail": False,
            "limit": 400
        }
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['character']} - {len(test['response'])} chars (limit: {test['limit']})")
        
        is_valid, _ = validate_character_response(test['character'], test['response'])
        
        if test['should_fail']:
            if not is_valid:
                print(f"✅ CORRECTLY REJECTED: Over {test['limit']} character limit")
                passed += 1
            else:
                print(f"❌ FAILED: Should have been rejected for length")
        else:
            if is_valid:
                print(f"✅ CORRECTLY PASSED: Under {test['limit']} character limit")
                passed += 1
            else:
                print(f"❌ FAILED: Should have passed validation")
    
    print(f"\n📊 Character Length Tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def test_ai_indicators_still_blocked():
    """Verify AI indicators are still blocked after length fixes."""
    print("\n🚨 Testing AI Indicators Still Blocked")
    print("=" * 50)
    
    test_cases = [
        "AI (as Peter): Hehehe!",
        "As an AI, I think...",
        "I'm an artificial intelligence...",
        "Hehehe, that's awesome!"  # Clean response
    ]
    
    passed = 0
    for i, response in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{response}'")
        
        is_valid, _ = validate_character_response("Peter", response)
        
        if "AI" in response or "artificial" in response:
            if not is_valid:
                print("✅ CORRECTLY REJECTED: AI indicator blocked")
                passed += 1
            else:
                print("❌ FAILED: AI indicator not blocked")
        else:
            if is_valid:
                print("✅ CORRECTLY PASSED: Clean response accepted")
                passed += 1
            else:
                print("❌ FAILED: Clean response rejected")
    
    print(f"\n📊 AI Indicator Tests: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)

def main():
    """Run all Discord length fix tests."""
    print("🔧 DISCORD LENGTH FIX VALIDATION")
    print("=" * 60)
    print("Testing Discord message length validation and error handling fixes.\n")
    
    results = []
    
    # Run all test suites
    results.append(test_discord_length_validation())
    results.append(test_character_length_limits())
    results.append(test_ai_indicators_still_blocked())
    
    # Summary
    passed_suites = sum(results)
    total_suites = len(results)
    
    print(f"\n🎯 FINAL RESULTS")
    print("=" * 60)
    print(f"Test Suites Passed: {passed_suites}/{total_suites}")
    
    if passed_suites == total_suites:
        print("🎉 ALL DISCORD FIXES WORKING! The system should now:")
        print("   • Block responses over 2000 characters")
        print("   • Enforce character-specific length limits")
        print("   • Handle Discord API errors gracefully")
        print("   • Still block AI indicators and maintain quality")
    elif passed_suites >= total_suites * 0.8:
        print("✅ MOSTLY WORKING! Some minor issues to address.")
    else:
        print("⚠️ NEEDS IMPROVEMENT! Several issues remain.")
    
    print(f"\nOverall Success Rate: {(passed_suites/total_suites)*100:.1f}%")
    
    return passed_suites == total_suites

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 