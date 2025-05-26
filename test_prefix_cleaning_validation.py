#!/usr/bin/env python3
"""
Test Enhanced Prefix Cleaning and Validation System

This script tests the enhanced cleaning and validation functions to ensure
they properly handle problematic prefixes like "Me:" and "@Character Griffin:"
that were appearing in Discord conversations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_clean_llm_response():
    """Test the enhanced clean_llm_response function."""
    print("\n🧹 Testing Enhanced clean_llm_response Function")
    print("=" * 60)
    
    # Import the function
    try:
        from app.orchestrator.server import clean_llm_response
    except ImportError:
        print("❌ Could not import clean_llm_response function")
        return False
    
    test_cases = [
        # Original problematic patterns from Discord - SELF-REFERENCES (should be removed)
        {
            "input": "Me: What the deuce? That's rather intriguing, actually.",
            "character": "Stewie",
            "expected_clean": "What the deuce? That's rather intriguing, actually.",
            "description": "Remove 'Me:' prefix (always problematic)"
        },
        {
            "input": "@Brian Griffin: Oh, Stewie, ever the surprising one.",
            "character": "Brian",
            "expected_clean": "Oh, Stewie, ever the surprising one.",
            "description": "Remove '@Brian Griffin:' self-addressing"
        },
        {
            "input": "Stewie Griffin: What the deuce are you going on about now, Brian?",
            "character": "Stewie",
            "expected_clean": "What the deuce are you going on about now, Brian?",
            "description": "Remove 'Stewie Griffin:' self-reference"
        },
        {
            "input": "Peter: Hehehehe I dunno, Brian.",
            "character": "Peter",
            "expected_clean": "Hehehehe I dunno, Brian.",
            "description": "Remove 'Peter:' self-reference"
        },
        {
            "input": "I am Stewie Griffin: What the deuce?",
            "character": "Stewie",
            "expected_clean": "What the deuce?",
            "description": "Remove 'I am Stewie Griffin:' self-reference"
        },
        # VALID CASES - Quoting other characters (should NOT be removed)
        {
            "input": "Peter: Hehehehe I dunno, Brian.",
            "character": "Brian",  # Brian quoting Peter
            "expected_clean": "Peter: Hehehehe I dunno, Brian.",
            "description": "Keep 'Peter:' when Brian is quoting Peter"
        },
        {
            "input": "Brian: Well, actually, that's quite thought-provoking.",
            "character": "Stewie",  # Stewie quoting Brian
            "expected_clean": "Brian: Well, actually, that's quite thought-provoking.",
            "description": "Keep 'Brian:' when Stewie is quoting Brian"
        },
        # Valid responses that should not be changed
        {
            "input": "What the deuce? That's rather intriguing, actually.",
            "character": "Stewie",
            "expected_clean": "What the deuce? That's rather intriguing, actually.",
            "description": "Valid response - no changes"
        },
        {
            "input": "Well, actually, I find their earlier work far more compelling.",
            "character": "Brian",
            "expected_clean": "Well, actually, I find their earlier work far more compelling.",
            "description": "Valid Brian response - no changes"
        },
        {
            "input": "Hehehehe I dunno, Brian. They sound all fancy-schmancy to me.",
            "character": "Peter",
            "expected_clean": "Hehehehe I dunno, Brian. They sound all fancy-schmancy to me.",
            "description": "Valid Peter response - no changes"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Character: {test_case['character']}")
        print(f"Input: '{test_case['input']}'")
        
        result = clean_llm_response(test_case['input'], test_case['character'])
        print(f"Output: '{result}'")
        print(f"Expected: '{test_case['expected_clean']}'")
        
        if result == test_case['expected_clean']:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
    
    print(f"\n📊 Clean LLM Response Results: {passed} passed, {failed} failed")
    return failed == 0

def test_validate_character_response():
    """Test the enhanced validate_character_response function."""
    print("\n🔍 Testing Enhanced validate_character_response Function")
    print("=" * 60)
    
    # Import the function
    try:
        from app.orchestrator.server import validate_character_response
    except ImportError:
        print("❌ Could not import validate_character_response function")
        return False
    
    test_cases = [
        # Should be rejected - self-reference prefixes
        {
            "character": "Stewie",
            "response": "Me: What the deuce? That's rather intriguing, actually.",
            "should_pass": False,
            "description": "Reject 'Me:' prefix (always problematic)"
        },
        {
            "character": "Brian",
            "response": "@Brian Griffin: Oh, Stewie, ever the surprising one.",
            "should_pass": False,
            "description": "Reject '@Brian Griffin:' self-addressing"
        },
        {
            "character": "Peter",
            "response": "Peter: Hehehehe I dunno, Brian.",
            "should_pass": False,
            "description": "Reject 'Peter:' self-reference"
        },
        {
            "character": "Stewie",
            "response": "Stewie Griffin: What the deuce are you going on about now?",
            "should_pass": False,
            "description": "Reject 'Stewie Griffin:' self-reference"
        },
        {
            "character": "Brian",
            "response": "I am Brian Griffin: Well, actually, that's quite thought-provoking.",
            "should_pass": False,
            "description": "Reject 'I am Brian Griffin:' self-reference"
        },
        # Should pass - valid responses (including quoting others)
        {
            "character": "Brian",
            "response": "Peter: Hehehehe I dunno, Brian.",
            "should_pass": True,
            "description": "Accept Brian quoting Peter"
        },
        {
            "character": "Stewie",
            "response": "What the deuce? That's rather intriguing, actually.",
            "should_pass": True,
            "description": "Accept clean Stewie response"
        },
        {
            "character": "Brian",
            "response": "Well, actually, I find their earlier work far more compelling.",
            "should_pass": True,
            "description": "Accept clean Brian response"
        },
        {
            "character": "Peter",
            "response": "Hehehehe I dunno, Brian. They sound all fancy-schmancy to me.",
            "should_pass": True,
            "description": "Accept clean Peter response"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Character: {test_case['character']}")
        print(f"Response: '{test_case['response']}'")
        print(f"Should pass: {test_case['should_pass']}")
        
        is_valid, corrected_response = validate_character_response(
            test_case['character'], 
            test_case['response']
        )
        
        print(f"Validation result: {is_valid}")
        
        if is_valid == test_case['should_pass']:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
    
    print(f"\n📊 Validation Results: {passed} passed, {failed} failed")
    return failed == 0

def main():
    """Run all tests."""
    print("🎯 Testing Enhanced Prefix Cleaning and Validation System")
    print("=" * 80)
    
    all_passed = True
    
    # Test cleaning function
    if not test_clean_llm_response():
        all_passed = False
    
    # Test validation function
    if not test_validate_character_response():
        all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Enhanced prefix cleaning and validation system is working correctly.")
        print("\n✅ The system now properly handles:")
        print("   • 'Me:' prefixes (always removed)")
        print("   • Self-addressing patterns (removed only when character addresses themselves)")
        print("   • Character name prefixes (removed only for self-references)")
        print("   • Allows quoting other characters (e.g., Brian can say 'Peter: Hehehehe')")
        print("   • 'I am Character Griffin:' patterns (always removed)")
    else:
        print("❌ SOME TESTS FAILED! Please review the implementation.")
    
    return all_passed

if __name__ == "__main__":
    main() 