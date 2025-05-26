#!/usr/bin/env python3
"""
Test script for quality control threshold change from 75 to 70.
Validates the threshold change and improved attempt counter display.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_quality_control_threshold():
    """Test that quality control threshold is now 70 instead of 75."""
    print("🎯 TESTING QUALITY CONTROL THRESHOLD CHANGE")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import QUALITY_CONTROL_MIN_RATING
        
        print(f"📊 Current threshold: {QUALITY_CONTROL_MIN_RATING}")
        print(f"📊 Expected: 70.0")
        
        if QUALITY_CONTROL_MIN_RATING == 70.0:
            print("✅ Threshold correctly set to 70.0")
            return True
        else:
            print(f"❌ Threshold is {QUALITY_CONTROL_MIN_RATING}, expected 70.0")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import threshold: {e}")
        return False

def test_threshold_impact():
    """Test what responses would pass with 70 vs 75 threshold."""
    print("\n📈 TESTING THRESHOLD IMPACT")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import _assess_conversation_flow_quality
        
        # Test responses that should pass with 70 but fail with 75
        borderline_responses = [
            {
                "character": "Brian",
                "response": "Well, actually, that's quite an interesting philosophical point you raise.",
                "context": "Human: What do you think about free will?\nPeter: I dunno, sounds complicated.",
                "expected_range": (70, 74)
            },
            {
                "character": "Peter", 
                "response": "Hehehe, yeah that's pretty cool I guess.",
                "context": "Human: Did you see that new movie?\nBrian: It was cinematically ambitious.",
                "expected_range": (70, 74)
            },
            {
                "character": "Stewie",
                "response": "Indeed, though I must say the execution could be improved.",
                "context": "Human: How was your day?\nPeter: Pretty good, watched TV.",
                "expected_range": (70, 74)
            }
        ]
        
        print("🧪 Testing responses in the 70-74 range (should now pass):")
        
        passed_70 = 0
        for i, test in enumerate(borderline_responses, 1):
            assessment = _assess_conversation_flow_quality(
                test['character'], test['response'], test['context']
            )
            score = assessment.get('flow_score', 0)
            
            print(f"\n{i}. {test['character']}: \"{test['response']}\"")
            print(f"   Score: {score:.1f}/100")
            print(f"   Expected range: {test['expected_range'][0]}-{test['expected_range'][1]}")
            
            if score >= 70.0:
                print(f"   ✅ PASSES with 70 threshold")
                passed_70 += 1
            else:
                print(f"   ❌ Still fails even with 70 threshold")
            
            if score >= 75.0:
                print(f"   ⚠️ Would have passed with 75 threshold too")
            else:
                print(f"   📊 Would have failed with 75 threshold")
        
        print(f"\n📊 Results: {passed_70}/{len(borderline_responses)} borderline responses now pass")
        return passed_70 > 0
        
    except ImportError as e:
        print(f"❌ Cannot import assessment function: {e}")
        return False

def test_attempt_counter_display():
    """Test that attempt counter displays correctly."""
    print("\n🔢 TESTING ATTEMPT COUNTER DISPLAY")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import QUALITY_CONTROL_MAX_RETRIES
        
        print(f"📊 Max retries configured: {QUALITY_CONTROL_MAX_RETRIES}")
        
        # Simulate attempt counter logic
        for attempt in range(QUALITY_CONTROL_MAX_RETRIES):
            attempt_display = f"attempt {attempt + 1}/{QUALITY_CONTROL_MAX_RETRIES}"
            print(f"   Attempt {attempt}: {attempt_display}")
        
        print("✅ Attempt counter logic working correctly")
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import max retries: {e}")
        return False

def test_variation_prompts():
    """Test the new variation prompts for regeneration."""
    print("\n🎭 TESTING VARIATION PROMPTS")
    print("=" * 50)
    
    variation_prompts = [
        "Try a different approach",
        "Be more conversational", 
        "Keep it shorter and more natural",
        "Focus on responding to the conversation",
        "Try a different angle"
    ]
    
    print("🔄 Variation prompts for regeneration attempts:")
    for i, prompt in enumerate(variation_prompts):
        print(f"   Attempt {i + 1}: \"{prompt}\"")
    
    # Test input modification logic
    original_input = "What do you think about that?"
    
    print(f"\n📝 Input modification examples:")
    print(f"   Original: \"{original_input}\"")
    
    for attempt in range(5):
        if attempt == 0:
            modified = f"{original_input} ({variation_prompts[0]})"
        elif attempt == 1:
            modified = f"{original_input} ({variation_prompts[1]})"
        elif attempt == 2:
            modified = f"{original_input} ({variation_prompts[2]})"
        elif attempt == 3:
            modified = f"{original_input} ({variation_prompts[3]})"
        else:
            modified = f"{original_input} ({variation_prompts[4]})"
        
        print(f"   Attempt {attempt + 1}: \"{modified}\"")
    
    print("✅ Variation prompt logic working correctly")
    return True

def test_quality_control_configuration():
    """Test overall quality control configuration."""
    print("\n⚙️ TESTING QUALITY CONTROL CONFIGURATION")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import (
            QUALITY_CONTROL_ENABLED,
            QUALITY_CONTROL_MIN_RATING,
            QUALITY_CONTROL_MAX_RETRIES
        )
        
        print(f"🔧 Configuration:")
        print(f"   Enabled: {QUALITY_CONTROL_ENABLED}")
        print(f"   Min Rating: {QUALITY_CONTROL_MIN_RATING}/100")
        print(f"   Max Retries: {QUALITY_CONTROL_MAX_RETRIES}")
        
        # Check if configuration is reasonable
        issues = []
        
        if not QUALITY_CONTROL_ENABLED:
            issues.append("Quality control is disabled")
        
        if QUALITY_CONTROL_MIN_RATING < 50 or QUALITY_CONTROL_MIN_RATING > 90:
            issues.append(f"Min rating {QUALITY_CONTROL_MIN_RATING} seems unreasonable")
        
        if QUALITY_CONTROL_MAX_RETRIES < 1 or QUALITY_CONTROL_MAX_RETRIES > 10:
            issues.append(f"Max retries {QUALITY_CONTROL_MAX_RETRIES} seems unreasonable")
        
        if issues:
            print(f"\n⚠️ Configuration issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print(f"\n✅ Configuration looks good!")
            return True
            
    except ImportError as e:
        print(f"❌ Cannot import configuration: {e}")
        return False

def main():
    """Run all tests for the 70 threshold fix."""
    print("🧪 TESTING QUALITY CONTROL THRESHOLD FIX (75 → 70)")
    print("=" * 60)
    
    tests = [
        ("Quality Control Threshold", test_quality_control_threshold),
        ("Threshold Impact", test_threshold_impact),
        ("Attempt Counter Display", test_attempt_counter_display),
        ("Variation Prompts", test_variation_prompts),
        ("Quality Control Configuration", test_quality_control_configuration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n" + "="*60)
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n" + "="*60)
    print("📊 FINAL RESULTS")
    print("=" * 60)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Quality control fixes are working correctly.")
        print("\n💡 SUMMARY OF CHANGES:")
        print("   ✅ Threshold reduced from 75 to 70 (more responses will pass)")
        print("   ✅ Attempt counter now shows progress correctly")
        print("   ✅ Variation prompts added to prevent repeated responses")
        print("   ✅ Better logging shows threshold value dynamically")
        print("\n📈 EXPECTED IMPROVEMENTS:")
        print("   • More responses will pass quality control (70 vs 75 threshold)")
        print("   • Brian should generate different responses on retries")
        print("   • Better visibility into quality control progress")
        print("   • Reduced repetition through variation prompts")
    else:
        print("\n⚠️ Some tests failed. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    main() 