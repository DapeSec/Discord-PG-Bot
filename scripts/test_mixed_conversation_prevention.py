#!/usr/bin/env python3
"""
Test script to verify that the improved quality control prevents mixed character conversations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.orchestrator.server import validate_character_response, _assess_response_quality_basic

def test_mixed_conversation_prevention():
    """Test that the validation catches mixed character conversations."""
    
    print("🧪 Testing Mixed Character Conversation Prevention")
    print("=" * 50)
    
    # Test cases that should FAIL validation (mixed conversations)
    bad_responses = [
        {
            "character": "Brian",
            "response": 'Brian: "Well, actually, that\'s quite interesting." Peter: "Hehehe, yeah!"',
            "issue": "Multiple character dialogue with colons"
        },
        {
            "character": "Brian", 
            "response": "Peter, you really need to think about this more carefully.",
            "issue": "Direct addressing of another character"
        },
        {
            "character": "Brian",
            "response": "Brian looks at Peter with disdain while considering the philosophical implications.",
            "issue": "Third person self-reference and narrative description"
        },
        {
            "character": "Brian",
            "response": '"That\'s ridiculous," Brian said to Peter. "You never think things through."',
            "issue": "Narrative format with character attribution"
        },
        {
            "character": "Brian",
            "response": "Hey Stewie, what do you think about this situation?",
            "issue": "Direct addressing with greeting"
        },
        {
            "character": "Peter",
            "response": "Peter thinks this is stupid. Brian responds with his usual pretentious attitude.",
            "issue": "Third person narrative about multiple characters"
        }
    ]
    
    # Test cases that should PASS validation (single character voice)
    good_responses = [
        {
            "character": "Brian",
            "response": "Well, actually, I find this quite fascinating from a philosophical perspective.",
            "issue": "Should pass - single character, first person"
        },
        {
            "character": "Peter", 
            "response": "Hehehe, holy crap! That's freakin' awesome!",
            "issue": "Should pass - single character, appropriate voice"
        },
        {
            "character": "Stewie",
            "response": "What the deuce? This is absolutely brilliant! My latest invention shall surpass all expectations.",
            "issue": "Should pass - single character, British accent, first person"
        }
    ]
    
    print("\n🚫 Testing responses that SHOULD FAIL validation:")
    print("-" * 45)
    
    failed_correctly = 0
    for i, test_case in enumerate(bad_responses, 1):
        character = test_case["character"]
        response = test_case["response"]
        issue = test_case["issue"]
        
        is_valid, _ = validate_character_response(character, response)
        basic_score = _assess_response_quality_basic(character, response)
        
        if not is_valid or basic_score < 2.0:
            print(f"✅ Test {i}: CORRECTLY REJECTED")
            print(f"   Character: {character}")
            print(f"   Issue: {issue}")
            print(f"   Validation: {'FAILED' if not is_valid else 'PASSED'}")
            print(f"   Basic Score: {basic_score:.1f}/5.0")
            failed_correctly += 1
        else:
            print(f"❌ Test {i}: INCORRECTLY ACCEPTED")
            print(f"   Character: {character}")
            print(f"   Issue: {issue}")
            print(f"   Response: {response[:50]}...")
            print(f"   Validation: {'FAILED' if not is_valid else 'PASSED'}")
            print(f"   Basic Score: {basic_score:.1f}/5.0")
        print()
    
    print(f"\n✅ Testing responses that SHOULD PASS validation:")
    print("-" * 45)
    
    passed_correctly = 0
    for i, test_case in enumerate(good_responses, 1):
        character = test_case["character"]
        response = test_case["response"]
        issue = test_case["issue"]
        
        is_valid, _ = validate_character_response(character, response)
        basic_score = _assess_response_quality_basic(character, response)
        
        if is_valid and basic_score >= 2.0:
            print(f"✅ Test {i}: CORRECTLY ACCEPTED")
            print(f"   Character: {character}")
            print(f"   Note: {issue}")
            print(f"   Validation: {'FAILED' if not is_valid else 'PASSED'}")
            print(f"   Basic Score: {basic_score:.1f}/5.0")
            passed_correctly += 1
        else:
            print(f"❌ Test {i}: INCORRECTLY REJECTED")
            print(f"   Character: {character}")
            print(f"   Note: {issue}")
            print(f"   Response: {response[:50]}...")
            print(f"   Validation: {'FAILED' if not is_valid else 'PASSED'}")
            print(f"   Basic Score: {basic_score:.1f}/5.0")
        print()
    
    print("\n📊 SUMMARY:")
    print("=" * 30)
    print(f"Bad responses correctly rejected: {failed_correctly}/{len(bad_responses)}")
    print(f"Good responses correctly accepted: {passed_correctly}/{len(good_responses)}")
    
    total_correct = failed_correctly + passed_correctly
    total_tests = len(bad_responses) + len(good_responses)
    accuracy = (total_correct / total_tests) * 100
    
    print(f"Overall accuracy: {total_correct}/{total_tests} ({accuracy:.1f}%)")
    
    if accuracy >= 90:
        print("🎉 EXCELLENT: Quality control is working well!")
    elif accuracy >= 75:
        print("✅ GOOD: Quality control is mostly working")
    else:
        print("⚠️ NEEDS IMPROVEMENT: Quality control needs refinement")
    
    return accuracy >= 75

if __name__ == "__main__":
    success = test_mixed_conversation_prevention()
    sys.exit(0 if success else 1) 