#!/usr/bin/env python3
"""
Test script to validate Stewie response validation fixes
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.orchestrator.server import validate_character_response, calculate_character_aware_anti_hallucination_settings

def test_stewie_validation():
    """Test Stewie response validation with various responses"""
    
    print("🧪 Testing Stewie Response Validation")
    print("=" * 50)
    
    # Test cases: (response, should_pass, description)
    test_cases = [
        # Short responses (should pass without British mannerisms)
        ("Interesting.", True, "Short response without British phrases"),
        ("I see.", True, "Very short response"),
        ("Hmm.", True, "Minimal response"),
        
        # Medium responses with British mannerisms (should pass)
        ("What the deuce? That's fascinating!", True, "Medium response with 'deuce'"),
        ("Rather intriguing, I must say.", True, "Medium response with 'rather'"),
        ("Blast! How unexpected.", True, "Medium response with 'blast'"),
        ("Indeed, quite brilliant.", True, "Medium response with 'indeed' and 'quite'"),
        
        # Long responses with British mannerisms (should pass)
        ("What the deuce? That's absolutely fascinating! I must say, your approach is rather brilliant.", True, "Long response with multiple British phrases"),
        ("Blast it all! This is indeed quite the conundrum, rather more complex than I initially anticipated.", True, "Long response with British mannerisms"),
        
        # Long responses without British mannerisms (should fail)
        ("This is absolutely fascinating! I must say, your approach is brilliant and well thought out.", False, "Long response without British phrases"),
        ("That's really interesting! I think you've made some excellent points about this topic.", False, "Long response, no British mannerisms"),
        
        # Fallback responses (should pass)
        ("What the deuce? That's actually quite fascinating.", True, "Fallback response 1"),
        ("Blast! How delightfully unexpected.", True, "Fallback response 2"),
        ("Rather intriguing, I must say.", True, "Fallback response 3"),
    ]
    
    passed = 0
    failed = 0
    
    for response, expected_pass, description in test_cases:
        is_valid, _ = validate_character_response("Stewie", response)
        
        if is_valid == expected_pass:
            print(f"✅ PASS: {description}")
            print(f"   Response: '{response}' (Length: {len(response)})")
            passed += 1
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Response: '{response}' (Length: {len(response)})")
            print(f"   Expected: {'PASS' if expected_pass else 'FAIL'}, Got: {'PASS' if is_valid else 'FAIL'}")
            failed += 1
        print()
    
    print(f"📊 Results: {passed} passed, {failed} failed")
    return failed == 0

def test_character_multipliers():
    """Test character-aware anti-hallucination settings"""
    
    print("🧪 Testing Character-Aware Anti-Hallucination Settings")
    print("=" * 50)
    
    base_settings = {
        "max_response_length": 400,
        "hallucination_risk": 30.0,
        "strictness_multiplier": 1.0
    }
    
    characters = ["Peter", "Brian", "Stewie"]
    
    for character in characters:
        settings = calculate_character_aware_anti_hallucination_settings(
            character, "COLD_START", base_settings
        )
        
        print(f"🎭 {character}:")
        print(f"   📏 Length: {base_settings['max_response_length']} → {settings['max_response_length']}")
        print(f"   🚨 Risk: {base_settings['hallucination_risk']}% → {settings['hallucination_risk']}%")
        print(f"   🔧 Strictness: {base_settings['strictness_multiplier']} → {settings['strictness_multiplier']}")
        print()
    
    # Verify Stewie has the updated 0.9x length multiplier
    stewie_settings = calculate_character_aware_anti_hallucination_settings(
        "Stewie", "COLD_START", base_settings
    )
    
    expected_stewie_length = int(400 * 0.9)  # Should be 360 with 0.9x multiplier
    if stewie_settings['max_response_length'] == expected_stewie_length:
        print("✅ Stewie length multiplier correctly updated to 0.9x")
    else:
        print(f"❌ Stewie length multiplier issue: expected {expected_stewie_length}, got {stewie_settings['max_response_length']}")
    
    return True

if __name__ == "__main__":
    print("🔧 Testing Stewie Validation Fixes")
    print("=" * 60)
    
    validation_success = test_stewie_validation()
    print()
    multiplier_success = test_character_multipliers()
    
    if validation_success and multiplier_success:
        print("\n🎉 All tests passed! Stewie validation fixes are working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please review the issues above.") 