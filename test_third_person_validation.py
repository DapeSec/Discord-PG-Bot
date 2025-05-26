#!/usr/bin/env python3
"""
Test script to validate enhanced third-person and direct addressing validation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from app.orchestrator.server import validate_character_response, _assess_conversation_flow_quality

def test_problematic_responses():
    """Test responses that should be caught by validation"""
    
    print("🧪 Testing Problematic Response Validation")
    print("=" * 60)
    
    # Test cases from the actual Discord conversation that should FAIL validation
    problematic_cases = [
        # Self-addressing issues (these should FAIL)
        ("@Stewie Griffin: Ah, Brian old chap, you're missing the point entirely!", "Stewie", "@Stewie Griffin self-mention"),
        ("@Peter Griffin: Oh, hey! While you're on your pill thingy", "Peter", "@Peter Griffin self-mention"),
        ("@Brian: Well, actually, that's quite interesting", "Brian", "@Brian self-mention"),
        
        # Third-person self-references (these should FAIL)
        ("Stewie's plan for world domination is quite brilliant", "Stewie", "Third-person self-reference 'Stewie's plan'"),
        ("Brian thinks this is a good idea", "Brian", "Third-person self-reference 'Brian thinks'"),
        ("Peter Griffin is confused about this", "Peter", "Third-person self-reference 'Peter Griffin'"),
        
        # Mixed character conversation (these should FAIL)
        ("Brian said something and then Stewie replied", "Peter", "Mixed character conversation"),
        ("Peter and Brian both think this is funny", "Stewie", "Multi-character narrative"),
    ]
    
    # Test cases that should PASS validation (good first-person responses)
    good_cases = [
        ("Well, actually, that's quite an intriguing prospect", "Brian", "Good Brian response"),
        ("What the deuce? That's rather fascinating!", "Stewie", "Good Stewie response"),
        ("Hehehe, that sounds awesome!", "Peter", "Good Peter response"),
        ("I think that's a brilliant idea", "Brian", "First-person response"),
        ("Blast! How unexpected", "Stewie", "British mannerisms without addressing"),
        # Inter-character addressing (these should PASS now)
        ("Well, actually, Stewie, that's quite an intriguing prospect", "Brian", "Brian addressing Stewie (should be allowed)"),
        ("Look, Peter, I'm just saying that seven days might seem daunting", "Brian", "Brian addressing Peter (should be allowed)"),
        ("Well, Brian, you misunderstand me entirely!", "Stewie", "Stewie addressing Brian (should be allowed)"),
        ("Peter, you're absolutely right about that", "Stewie", "Natural character addressing (should be allowed)"),
    ]
    
    print("🔍 Testing Problematic Cases (should FAIL):")
    print("-" * 50)
    
    failed_to_catch = 0
    correctly_caught = 0
    
    for response, character, description in problematic_cases:
        is_valid, _ = validate_character_response(character, response)
        
        if is_valid:
            print(f"❌ MISSED: {description}")
            print(f"   Character: {character}")
            print(f"   Response: '{response}'")
            print(f"   Expected: FAIL, Got: PASS")
            failed_to_catch += 1
        else:
            print(f"✅ CAUGHT: {description}")
            correctly_caught += 1
        print()
    
    print(f"📊 Problematic Cases: {correctly_caught} caught, {failed_to_catch} missed")
    print()
    
    print("🔍 Testing Good Cases (should PASS):")
    print("-" * 50)
    
    incorrectly_failed = 0
    correctly_passed = 0
    
    for response, character, description in good_cases:
        is_valid, _ = validate_character_response(character, response)
        
        if not is_valid:
            print(f"❌ FAILED: {description}")
            print(f"   Character: {character}")
            print(f"   Response: '{response}'")
            print(f"   Expected: PASS, Got: FAIL")
            incorrectly_failed += 1
        else:
            print(f"✅ PASSED: {description}")
            correctly_passed += 1
        print()
    
    print(f"📊 Good Cases: {correctly_passed} passed, {incorrectly_failed} incorrectly failed")
    
    return failed_to_catch == 0 and incorrectly_failed == 0

def test_flow_quality_assessment():
    """Test the conversation flow quality assessment"""
    
    print("\n🧪 Testing Flow Quality Assessment")
    print("=" * 60)
    
    # Test cases with conversation context
    test_cases = [
        # Self-addressing (should get low score)
        ("@Brian: Well, actually, that's quite interesting", "Brian", "Human: How do you feel about world domination?\nStewie: It's fascinating!", "Self-addressing with @mention"),
        
        # Third-person self-reference (should get low score)
        ("Brian thinks this is a good point", "Brian", "Human: What do you think?\nStewie: I have an idea!", "Third-person self-reference"),
        
        # Good first-person response (should get high score)
        ("Well, actually, that's quite thought-provoking", "Brian", "Human: What do you think?\nStewie: I have an idea!", "Good first-person response"),
        
        # Inter-character addressing (should get good score)
        ("Well, actually, Stewie, that's quite interesting", "Brian", "Human: How do you feel about world domination?\nStewie: It's fascinating!", "Natural inter-character addressing"),
        
        # AI meta-reference (should get very low score)
        ("As an AI assistant, I think that's interesting", "Brian", "Human: What do you think?", "AI meta-reference"),
    ]
    
    for response, character, context, description in test_cases:
        assessment = _assess_conversation_flow_quality(character, response, context)
        score = assessment.get("flow_score", 0)
        issues = assessment.get("issues", [])
        
        print(f"🎯 {description}:")
        print(f"   Character: {character}")
        print(f"   Response: '{response}'")
        print(f"   Score: {score:.1f}/100")
        if issues:
            print(f"   Issues: {', '.join(issues)}")
        print()
    
    return True

if __name__ == "__main__":
    print("🔧 Testing Enhanced Third-Person and Direct Addressing Validation")
    print("=" * 80)
    
    validation_success = test_problematic_responses()
    flow_success = test_flow_quality_assessment()
    
    if validation_success and flow_success:
        print("\n🎉 All tests passed! Enhanced validation is working correctly.")
        print("✅ The system should now catch third-person and direct addressing issues.")
    else:
        print("\n⚠️ Some tests failed. The validation may need further improvements.") 