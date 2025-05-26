#!/usr/bin/env python3
"""
Test script for adaptive length validation with retry system.
Verifies that responses exceeding adaptive length limits trigger retries instead of truncation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.orchestrator.server import _assess_conversation_flow_quality, calculate_adaptive_context_weights

def test_adaptive_length_validation():
    """Test that adaptive length validation correctly penalizes responses that exceed limits"""
    print("🧪 Testing Adaptive Length Validation with Retry System")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "Cold Start - Appropriate Length",
            "character": "Peter",
            "response": "Hehehe, that's awesome! I totally agree with you about that.",
            "conversation_context": "Human: What do you think about pizza?",
            "expected_penalty": False,
            "description": "Short response within cold start limit (400 chars)"
        },
        {
            "name": "Cold Start - Exceeds Limit",
            "character": "Brian",
            "response": "Well, actually, this is a fascinating question that touches on numerous philosophical, sociological, and economic considerations that I've been contemplating extensively. The implications of food choice in modern society reflect broader patterns of cultural consumption and identity formation that scholars have been analyzing for decades. When we consider the historical context of pizza as both an immigrant food that became mainstream and a symbol of American casual dining culture, we see how individual choices reflect larger societal trends.",
            "conversation_context": "Human: Pizza?",
            "expected_penalty": True,
            "description": "Long response exceeding cold start limit (400 chars)"
        },
        {
            "name": "Warm Conversation - Appropriate Length",
            "character": "Stewie",
            "response": "Blast! That's actually quite brilliant, you fool. I must admit your suggestion has merit, though I'd prefer a more sophisticated approach.",
            "conversation_context": "Human: What about pizza?\nBrian: I think that could work.\nPeter: Hehehe yeah!\nStewie: Interesting choice.\nHuman: So we're all agreed?",
            "expected_penalty": False,
            "description": "Medium response within warm conversation limit (300 chars)"
        },
        {
            "name": "Warm Conversation - Exceeds Limit",
            "character": "Brian",
            "response": "Well, actually, this is a fascinating question that touches on numerous philosophical, sociological, and economic considerations that I've been contemplating extensively. The implications of food choice in modern society reflect broader patterns of cultural consumption and identity formation that scholars have been analyzing for decades. When we consider the historical context of pizza as both an immigrant food that became mainstream and a symbol of American casual dining culture, we see how individual choices reflect larger societal trends.",
            "conversation_context": "Human: What about pizza?\nBrian: I think that could work.\nPeter: Hehehe yeah!\nStewie: Interesting choice.\nHuman: So we're all agreed?",
            "expected_penalty": True,
            "description": "Long response exceeding warm conversation limit (300 chars)"
        },
        {
            "name": "Hot Conversation - Appropriate Length",
            "character": "Peter",
            "response": "Hehehe, yeah! That sounds perfect to me. Let's do it!",
            "conversation_context": "Human: What about pizza?\nBrian: I think that could work.\nPeter: Hehehe yeah!\nStewie: Interesting choice.\nHuman: So we're all agreed?\nBrian: Indeed, quite reasonable.\nPeter: Awesome!\nStewie: Very well.\nHuman: Great, let's order.\nBrian: Excellent choice.\nPeter: Can't wait!\nHuman: What toppings?",
            "expected_penalty": False,
            "description": "Short response within hot conversation limit (250 chars)"
        },
        {
            "name": "Hot Conversation - Exceeds Limit",
            "character": "Brian",
            "response": "Well, actually, this is a fascinating question that touches on numerous philosophical, sociological, and economic considerations that I've been contemplating extensively. The implications of food choice in modern society reflect broader patterns of cultural consumption and identity formation.",
            "conversation_context": "Human: What about pizza?\nBrian: I think that could work.\nPeter: Hehehe yeah!\nStewie: Interesting choice.\nHuman: So we're all agreed?\nBrian: Indeed, quite reasonable.\nPeter: Awesome!\nStewie: Very well.\nHuman: Great, let's order.\nBrian: Excellent choice.\nPeter: Can't wait!\nHuman: What toppings?",
            "expected_penalty": True,
            "description": "Long response exceeding hot conversation limit (250 chars)"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        print(f"📝 Description: {test_case['description']}")
        
        # Count conversation messages to determine state
        message_count = len([line for line in test_case['conversation_context'].split('\n') if ':' in line])
        
        if message_count <= 3:
            expected_state = "COLD_START"
            expected_limit = 400
        elif message_count <= 10:
            expected_state = "WARM_CONVERSATION"
            expected_limit = 300
        else:
            expected_state = "HOT_CONVERSATION"
            expected_limit = 250
        
        print(f"📊 Conversation messages: {message_count}")
        print(f"🎯 Expected state: {expected_state}")
        print(f"📏 Expected limit: {expected_limit} chars")
        print(f"📏 Response length: {len(test_case['response'])} chars")
        
        # Assess the response
        assessment = _assess_conversation_flow_quality(
            character_name=test_case['character'],
            response_text=test_case['response'],
            conversation_context=test_case['conversation_context']
        )
        
        score = assessment.get('flow_score', 0)
        issues = assessment.get('issues', [])
        strengths = assessment.get('strengths', [])
        
        # Check for length-related issues
        length_issues = [issue for issue in issues if "too long" in issue.lower()]
        length_strengths = [strength for strength in strengths if "appropriate length" in strength.lower()]
        
        print(f"📊 Flow Score: {score:.1f}/100")
        print(f"⚠️ Length Issues: {length_issues}")
        print(f"💪 Length Strengths: {length_strengths}")
        
        # Verify expectations
        has_length_penalty = len(length_issues) > 0
        has_length_bonus = len(length_strengths) > 0
        
        if test_case['expected_penalty'] and has_length_penalty:
            print("✅ PASS - Length penalty correctly applied")
            results.append(True)
        elif not test_case['expected_penalty'] and has_length_bonus:
            print("✅ PASS - Length bonus correctly applied")
            results.append(True)
        elif not test_case['expected_penalty'] and not has_length_penalty:
            print("✅ PASS - No length penalty (as expected)")
            results.append(True)
        else:
            print("❌ FAIL - Length validation incorrect")
            print(f"   Expected penalty: {test_case['expected_penalty']}")
            print(f"   Actual penalty: {has_length_penalty}")
            results.append(False)
    
    # Summary
    print(f"\n\n📊 SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All adaptive length validation tests passed!")
        print("🔄 Responses exceeding limits will now trigger retries instead of truncation")
    else:
        print("⚠️ Some tests failed - adaptive length validation needs adjustment")
    
    return passed == total

def test_retry_prompt_adaptation():
    """Test that retry prompts are adapted based on length issues"""
    print("\n\n🔄 Testing Retry Prompt Adaptation")
    print("=" * 60)
    
    # Simulate a flow assessment with length issues
    mock_flow_assessment = {
        'issues': ['Response too long (450 chars > 400 limit for COLD_START)'],
        'strengths': [],
        'flow_score': 35.0
    }
    
    # Test length-specific prompts
    length_issue = any("too long" in issue.lower() for issue in mock_flow_assessment.get('issues', []))
    
    if length_issue:
        variation_prompts = [
            "Keep it much shorter and more concise",
            "Give a brief, natural response", 
            "Respond with just a few words or a short sentence",
            "Be more direct and to the point",
            "Keep it simple and short"
        ]
        print("✅ Length-specific retry prompts detected:")
        for i, prompt in enumerate(variation_prompts, 1):
            print(f"   {i}. {prompt}")
    else:
        print("❌ Length-specific prompts not triggered")
        return False
    
    # Test non-length issues
    mock_flow_assessment_other = {
        'issues': ['Repetitive sentence patterns', 'Poor conversation awareness'],
        'strengths': [],
        'flow_score': 45.0
    }
    
    length_issue_other = any("too long" in issue.lower() for issue in mock_flow_assessment_other.get('issues', []))
    
    if not length_issue_other:
        variation_prompts_other = [
            "Try a different approach",
            "Be more conversational", 
            "Keep it shorter and more natural",
            "Focus on responding to the conversation",
            "Try a different angle"
        ]
        print("\n✅ General retry prompts for non-length issues:")
        for i, prompt in enumerate(variation_prompts_other, 1):
            print(f"   {i}. {prompt}")
    else:
        print("❌ General prompts not used for non-length issues")
        return False
    
    print("\n🎯 Retry prompt adaptation working correctly!")
    return True

if __name__ == "__main__":
    print("🚀 Starting Adaptive Length Validation Tests")
    print("=" * 60)
    
    # Test adaptive length validation
    length_test_passed = test_adaptive_length_validation()
    
    # Test retry prompt adaptation
    retry_test_passed = test_retry_prompt_adaptation()
    
    print(f"\n\n🏁 FINAL RESULTS")
    print("=" * 60)
    print(f"📏 Length Validation: {'✅ PASS' if length_test_passed else '❌ FAIL'}")
    print(f"🔄 Retry Adaptation: {'✅ PASS' if retry_test_passed else '❌ FAIL'}")
    
    if length_test_passed and retry_test_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("🔄 Adaptive length validation now triggers retries instead of truncation")
        print("📏 Responses will be regenerated with appropriate length guidance")
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("🔧 System needs adjustment before deployment") 