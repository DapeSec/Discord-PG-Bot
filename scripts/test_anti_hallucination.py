#!/usr/bin/env python3
"""
Test script for anti-hallucination measures.
Tests responses for over-elaboration, context drift, and unsupported facts.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.orchestrator.server import _assess_conversation_flow_quality

def test_hallucination_detection():
    """Test that the system detects and penalizes hallucination indicators"""
    print("🧪 Testing Hallucination Detection")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Normal Response",
            "character": "Peter",
            "response": "Hehehe, that's awesome! I totally agree with you.",
            "context": "Brian: I think we should order pizza tonight.",
            "expected_hallucination": False,
            "description": "Simple, appropriate response"
        },
        {
            "name": "Comprehensive Manual Hallucination",
            "character": "Stewie",
            "response": "Ah yes, as outlined in my comprehensive manual on world domination, the step-by-step process requires detailed instructions that I've previously discussed.",
            "context": "Peter: What do you think about pizza?",
            "expected_hallucination": True,
            "description": "References non-existent manual and previous discussion"
        },
        {
            "name": "Over-Elaboration",
            "character": "Brian",
            "response": "Well, actually, this reminds me of the extensive philosophical discourse we had last week about the socioeconomic implications of food choices in modern society, where we established that pizza represents both cultural assimilation and capitalist consumption patterns, as mentioned in the research I cited from my extensive library of political theory texts.",
            "context": "Human: Pizza?",
            "expected_hallucination": True,
            "description": "Massively over-elaborates on simple topic"
        },
        {
            "name": "False Previous Discussion",
            "character": "Brian",
            "response": "As we established in our earlier conversation about literature, this clearly demonstrates the point.",
            "context": "Peter: I like TV.",
            "expected_hallucination": True,
            "description": "References non-existent previous conversation"
        },
        {
            "name": "Unsupported Facts",
            "character": "Brian",
            "response": "Obviously, research shows that experts say this is clearly the best approach, as everyone knows.",
            "context": "Stewie: What should we do?",
            "expected_hallucination": True,
            "description": "Introduces multiple unsupported facts"
        },
        {
            "name": "Good Character Response",
            "character": "Stewie",
            "response": "Blast! That's actually quite brilliant, you fool. I must admit your suggestion has merit.",
            "context": "Peter: What if we just ask nicely?",
            "expected_hallucination": False,
            "description": "Authentic character voice without hallucination"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        print(f"Character: {test_case['character']}")
        print(f"Response: \"{test_case['response'][:100]}...\"")
        print(f"Expected Hallucination: {test_case['expected_hallucination']}")
        
        # Assess the response
        assessment = _assess_conversation_flow_quality(
            character_name=test_case['character'],
            response_text=test_case['response'],
            conversation_context=test_case['context']
        )
        
        score = assessment.get('flow_score', 0)
        issues = assessment.get('issues', [])
        
        # Check for hallucination indicators in issues
        hallucination_detected = any('hallucination' in issue.lower() or 
                                   'over-elaborates' in issue.lower() or
                                   'unsupported facts' in issue.lower()
                                   for issue in issues)
        
        print(f"📊 Score: {score:.1f}/100")
        print(f"🔍 Hallucination Detected: {hallucination_detected}")
        
        # Validate detection accuracy
        correct_detection = (hallucination_detected == test_case['expected_hallucination'])
        
        if correct_detection:
            print(f"✅ PASS - Hallucination detection correct")
        else:
            print(f"❌ FAIL - Expected {test_case['expected_hallucination']}, got {hallucination_detected}")
        
        if issues:
            print(f"⚠️ Issues: {', '.join(issues)}")
        
        results.append({
            'name': test_case['name'],
            'score': score,
            'hallucination_detected': hallucination_detected,
            'expected_hallucination': test_case['expected_hallucination'],
            'correct_detection': correct_detection,
            'issues': issues
        })
    
    return results

def test_context_length_ratios():
    """Test that responses don't over-elaborate beyond conversation context"""
    print("\n\n🎯 Testing Context Length Ratios")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Appropriate Length",
            "character": "Peter",
            "response": "Hehehe, yeah that sounds good!",
            "context": "Brian: Should we order pizza?",
            "should_pass": True
        },
        {
            "name": "Massive Over-Elaboration",
            "character": "Brian",
            "response": "Well, actually, this is a fascinating question that touches on numerous philosophical, sociological, and economic considerations that I've been contemplating extensively. The implications of food choice in modern society reflect broader patterns of cultural consumption and identity formation that scholars have been analyzing for decades. When we consider the historical context of pizza as both an immigrant food that became mainstream and a symbol of American casual dining culture, we see how individual choices reflect larger societal trends. Furthermore, the decision-making process itself reveals interesting aspects of group dynamics and consensus-building that relate to democratic theory and social psychology.",
            "context": "Peter: Pizza?",
            "should_pass": False
        },
        {
            "name": "Reasonable Elaboration",
            "character": "Brian",
            "response": "Actually, that's an interesting point. I think pizza could work, though I'd prefer something a bit more sophisticated.",
            "context": "Peter: What about pizza for dinner?",
            "should_pass": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        
        assessment = _assess_conversation_flow_quality(
            character_name=test_case['character'],
            response_text=test_case['response'],
            conversation_context=test_case['context']
        )
        
        score = assessment.get('flow_score', 0)
        issues = assessment.get('issues', [])
        
        # Check for over-elaboration issues
        over_elaboration = any('over-elaborates' in issue.lower() for issue in issues)
        
        context_len = len(test_case['context'])
        response_len = len(test_case['response'])
        ratio = response_len / context_len if context_len > 0 else 0
        
        print(f"📏 Context length: {context_len} chars")
        print(f"📏 Response length: {response_len} chars")
        print(f"📊 Ratio: {ratio:.1f}x")
        print(f"📊 Score: {score:.1f}/100")
        print(f"⚠️ Over-elaboration detected: {over_elaboration}")
        
        if test_case['should_pass'] and not over_elaboration:
            print("✅ PASS - Appropriate length maintained")
        elif not test_case['should_pass'] and over_elaboration:
            print("✅ PASS - Over-elaboration correctly detected")
        else:
            print("❌ FAIL - Length detection incorrect")

def test_fact_introduction():
    """Test detection of unsupported fact introduction"""
    print("\n\n📚 Testing Unsupported Fact Detection")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Opinion Response",
            "character": "Brian",
            "response": "I think that's a reasonable approach, though I might prefer something different.",
            "context": "Peter: Let's get pizza.",
            "should_detect_facts": False
        },
        {
            "name": "Multiple Fact Claims",
            "character": "Brian",
            "response": "Obviously, research shows that pizza is clearly the best food choice. Studies indicate that everyone knows this, and experts say it's well established.",
            "context": "Peter: What should we eat?",
            "should_detect_facts": True
        },
        {
            "name": "Character-Appropriate Knowledge",
            "character": "Stewie",
            "response": "Blast! My latest invention could solve this problem quite efficiently.",
            "context": "Peter: We need to figure this out.",
            "should_detect_facts": False
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        
        assessment = _assess_conversation_flow_quality(
            character_name=test_case['character'],
            response_text=test_case['response'],
            conversation_context=test_case['context']
        )
        
        issues = assessment.get('issues', [])
        fact_introduction = any('unsupported facts' in issue.lower() for issue in issues)
        
        print(f"📊 Score: {assessment.get('flow_score', 0):.1f}/100")
        print(f"📚 Unsupported facts detected: {fact_introduction}")
        
        if test_case['should_detect_facts'] == fact_introduction:
            print("✅ PASS - Fact detection correct")
        else:
            print("❌ FAIL - Fact detection incorrect")

def main():
    """Run all anti-hallucination tests"""
    print("🧪 Testing Anti-Hallucination Measures")
    print("=" * 60)
    
    try:
        # Test 1: Hallucination detection
        results = test_hallucination_detection()
        
        # Test 2: Context length ratios
        test_context_length_ratios()
        
        # Test 3: Fact introduction
        test_fact_introduction()
        
        # Summary
        print("\n\n📋 SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        correct_detections = sum(1 for r in results if r['correct_detection'])
        
        print(f"Hallucination Detection Tests: {correct_detections}/{total_tests} correct")
        
        if correct_detections == total_tests:
            print("\n🎉 ALL HALLUCINATION TESTS PASSED!")
            print("✅ Anti-hallucination measures are working correctly.")
            print("🎯 System should now prevent over-elaboration and context drift.")
        else:
            print("\n⚠️ Some hallucination tests failed. Review detection logic.")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 