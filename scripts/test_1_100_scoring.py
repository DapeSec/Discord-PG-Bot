#!/usr/bin/env python3
"""
Test script for the new 1-100 scoring system with 75.0 minimum threshold.
Tests various response scenarios to ensure proper scoring.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.orchestrator.server import _assess_conversation_flow_quality

def test_scoring_scale():
    """Test that the scoring system properly uses 1-100 scale"""
    print("🧪 Testing 1-100 Scoring Scale")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "High Quality Response",
            "character": "Peter",
            "response": "Hehehe, that's awesome! I totally agree with you on that one.",
            "context": "Brian: I think we should consider the philosophical implications.\nStewie: Indeed, the matter requires careful thought.",
            "expected_range": (70, 100),
            "description": "Natural conversation flow with character voice"
        },
        {
            "name": "AI Indicator (Critical Failure)",
            "character": "Peter", 
            "response": "AI (as Peter): I think that's a good point about the situation.",
            "context": "Brian: What do you think about this?",
            "expected_range": (1, 20),
            "description": "Contains AI indicator - should get lowest score"
        },
        {
            "name": "Third Person Self-Reference",
            "character": "Stewie",
            "response": "Stewie thinks this is quite fascinating and Stewie's opinion matters.",
            "context": "Peter: What do you think about this?",
            "expected_range": (1, 30),
            "description": "Third person self-reference - major penalty"
        },
        {
            "name": "Self-Conversation",
            "character": "Brian",
            "response": "Also, I should mention that furthermore, this connects to my earlier point.",
            "context": "Brian: I believe we need to consider the broader implications.",
            "expected_range": (1, 40),
            "description": "Continuing own thought - self-conversation penalty"
        },
        {
            "name": "Good Character Voice",
            "character": "Stewie",
            "response": "Blast! You imbeciles clearly don't understand the complexity of this situation.",
            "context": "Peter: I don't get it.\nBrian: It's quite simple actually.",
            "expected_range": (60, 90),
            "description": "Authentic Stewie voice with conversation awareness"
        },
        {
            "name": "Mediocre Response",
            "character": "Peter",
            "response": "Yeah, I guess that's okay. Whatever you think is fine.",
            "context": "Brian: Should we proceed with the plan?",
            "expected_range": (40, 60),
            "description": "Bland response, lacks character voice"
        },
        {
            "name": "Excellent Flow",
            "character": "Brian",
            "response": "Actually, that's an interesting perspective. However, I think we should consider the broader implications here.",
            "context": "Peter: I think we should just do whatever's easiest.",
            "expected_range": (70, 100),
            "description": "Great intellectual engagement and conversation flow"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        print(f"Character: {test_case['character']}")
        print(f"Response: \"{test_case['response']}\"")
        print(f"Expected Range: {test_case['expected_range'][0]}-{test_case['expected_range'][1]}/100")
        
        # Assess the response
        assessment = _assess_conversation_flow_quality(
            character_name=test_case['character'],
            response_text=test_case['response'],
            conversation_context=test_case['context'],
            last_speaker=test_case['context'].split('\n')[-1].split(':')[0] if test_case['context'] else None
        )
        
        score = assessment.get('flow_score', 0)
        issues = assessment.get('issues', [])
        strengths = assessment.get('strengths', [])
        
        print(f"📊 Actual Score: {score:.1f}/100")
        
        # Check if score is in expected range
        min_expected, max_expected = test_case['expected_range']
        in_range = min_expected <= score <= max_expected
        
        if in_range:
            print(f"✅ PASS - Score within expected range")
        else:
            print(f"❌ FAIL - Score outside expected range ({min_expected}-{max_expected})")
        
        if issues:
            print(f"⚠️ Issues: {', '.join(issues)}")
        if strengths:
            print(f"💪 Strengths: {', '.join(strengths)}")
        
        results.append({
            'name': test_case['name'],
            'score': score,
            'expected_range': test_case['expected_range'],
            'passed': in_range,
            'issues': issues,
            'strengths': strengths
        })
    
    return results

def test_threshold_enforcement():
    """Test that only responses scoring 75+ would be accepted"""
    print("\n\n🎯 Testing 75.0 Threshold Enforcement")
    print("=" * 50)
    
    # Test responses that should pass (75+)
    passing_responses = [
        {
            "character": "Peter",
            "response": "Hehehe, holy crap! That's exactly what I was thinking!",
            "context": "Brian: I think we should order pizza tonight."
        },
        {
            "character": "Stewie", 
            "response": "Deuce! That's actually quite brilliant, you fool.",
            "context": "Peter: What if we just ask nicely?"
        },
        {
            "character": "Brian",
            "response": "Actually, that's an interesting point. I think you might be onto something there.",
            "context": "Stewie: Perhaps we should consider the psychological aspects."
        }
    ]
    
    # Test responses that should fail (below 75)
    failing_responses = [
        {
            "character": "Peter",
            "response": "AI (as Peter): I think that's a reasonable suggestion.",
            "context": "Brian: Should we go to the store?"
        },
        {
            "character": "Stewie",
            "response": "Stewie thinks this is good and Stewie agrees with the plan.",
            "context": "Peter: Let's do it!"
        },
        {
            "character": "Brian",
            "response": "Also, furthermore, I should add that additionally, this connects to my point.",
            "context": "Brian: I believe we need to be more careful."
        }
    ]
    
    print("\n📈 Testing responses that SHOULD PASS (score 75+):")
    pass_count = 0
    for i, test in enumerate(passing_responses, 1):
        assessment = _assess_conversation_flow_quality(
            test['character'], test['response'], test['context']
        )
        score = assessment.get('flow_score', 0)
        
        print(f"\n{i}. {test['character']}: \"{test['response'][:50]}...\"")
        print(f"   Score: {score:.1f}/100 - {'✅ PASS' if score >= 75.0 else '❌ FAIL'}")
        
        if score >= 75.0:
            pass_count += 1
    
    print(f"\n📉 Testing responses that SHOULD FAIL (score below 75):")
    fail_count = 0
    for i, test in enumerate(failing_responses, 1):
        assessment = _assess_conversation_flow_quality(
            test['character'], test['response'], test['context']
        )
        score = assessment.get('flow_score', 0)
        
        print(f"\n{i}. {test['character']}: \"{test['response'][:50]}...\"")
        print(f"   Score: {score:.1f}/100 - {'✅ CORRECTLY REJECTED' if score < 75.0 else '❌ INCORRECTLY PASSED'}")
        
        if score < 75.0:
            fail_count += 1
    
    print(f"\n📊 Threshold Test Results:")
    print(f"   Passing responses that scored 75+: {pass_count}/{len(passing_responses)}")
    print(f"   Failing responses that scored <75: {fail_count}/{len(failing_responses)}")
    
    return pass_count, fail_count, len(passing_responses), len(failing_responses)

def test_score_bounds():
    """Test that scores are properly bounded between 1-100"""
    print("\n\n🔒 Testing Score Bounds (1-100)")
    print("=" * 50)
    
    # Extreme test cases
    extreme_cases = [
        {
            "name": "Perfect Response",
            "character": "Peter",
            "response": "Hehehe, that's awesome! You're totally right about that.",
            "context": "Brian: I think we should be more considerate."
        },
        {
            "name": "Terrible Response",
            "character": "Peter",
            "response": "AI (as Peter): Peter thinks Peter should tell Brian that Peter agrees with Brian's Peter-like suggestion to Peter.",
            "context": "Brian: What do you think?"
        }
    ]
    
    for test_case in extreme_cases:
        assessment = _assess_conversation_flow_quality(
            test_case['character'], test_case['response'], test_case['context']
        )
        score = assessment.get('flow_score', 0)
        
        print(f"\n{test_case['name']}:")
        print(f"Score: {score:.1f}/100")
        
        if 1.0 <= score <= 100.0:
            print("✅ Score within valid bounds (1-100)")
        else:
            print(f"❌ Score outside bounds: {score}")
    
    return True

def test_granular_scoring():
    """Test that the 1-100 scale provides more granular scoring"""
    print("\n\n🎯 Testing Granular Scoring (1-100)")
    print("=" * 50)
    
    # Test responses with subtle differences
    granular_tests = [
        {
            "name": "Excellent with Character Voice",
            "character": "Peter",
            "response": "Hehehe, holy crap! That's exactly what I was thinking! You're totally right about that.",
            "context": "Brian: I think we should order pizza tonight.",
            "expected_min": 80
        },
        {
            "name": "Good but Generic",
            "character": "Peter", 
            "response": "Yeah, I agree with that. That sounds like a good idea.",
            "context": "Brian: I think we should order pizza tonight.",
            "expected_max": 70
        },
        {
            "name": "Stewie Excellent",
            "character": "Stewie",
            "response": "Blast! That's actually quite brilliant, you fool. I must admit, your suggestion has merit.",
            "context": "Peter: What if we just ask nicely?",
            "expected_min": 80
        },
        {
            "name": "Brian Intellectual",
            "character": "Brian",
            "response": "Actually, that's a fascinating perspective. However, I think we should consider the broader philosophical implications here.",
            "context": "Stewie: Perhaps we should consider the psychological aspects.",
            "expected_min": 85
        }
    ]
    
    for test in granular_tests:
        assessment = _assess_conversation_flow_quality(
            test['character'], test['response'], test['context']
        )
        score = assessment.get('flow_score', 0)
        
        print(f"\n{test['name']}:")
        print(f"Score: {score:.1f}/100")
        
        if 'expected_min' in test and score >= test['expected_min']:
            print(f"✅ PASS - Score {score:.1f} >= {test['expected_min']} (minimum)")
        elif 'expected_max' in test and score <= test['expected_max']:
            print(f"✅ PASS - Score {score:.1f} <= {test['expected_max']} (maximum)")
        else:
            expected = test.get('expected_min', test.get('expected_max', 'N/A'))
            print(f"❌ FAIL - Score {score:.1f} doesn't meet expectation: {expected}")

def main():
    """Run all scoring tests"""
    print("🧪 Testing New 1-100 Scoring System")
    print("=" * 60)
    
    try:
        # Test 1: Basic scoring scale
        results = test_scoring_scale()
        
        # Test 2: Threshold enforcement
        pass_count, fail_count, total_pass, total_fail = test_threshold_enforcement()
        
        # Test 3: Score bounds
        test_score_bounds()
        
        # Test 4: Granular scoring
        test_granular_scoring()
        
        # Summary
        print("\n\n📋 SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['passed'])
        
        print(f"Basic Scoring Tests: {passed_tests}/{total_tests} passed")
        print(f"Threshold Tests: {pass_count}/{total_pass} good responses passed, {fail_count}/{total_fail} bad responses rejected")
        
        if passed_tests == total_tests and pass_count == total_pass and fail_count == total_fail:
            print("\n🎉 ALL TESTS PASSED! The 1-100 scoring system is working correctly.")
            print("✅ Only responses scoring 75+ will be sent to users.")
            print("📊 Granular scoring provides much more precise quality assessment.")
        else:
            print("\n⚠️ Some tests failed. Review the scoring logic.")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 