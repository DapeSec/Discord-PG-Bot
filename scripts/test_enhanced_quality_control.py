#!/usr/bin/env python3
"""
Test script to validate the enhanced quality control system for natural conversation flow.
This tests the new conversation flow assessment and improved character response validation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.orchestrator.server import (
    _assess_conversation_flow_quality, 
    _assess_response_quality_with_llm,
    validate_character_response,
    _check_speaker_attribution,
    _extract_key_topics
)

def test_speaker_attribution_detection():
    """Test detection of incorrect speaker attribution."""
    print("🎯 Testing Speaker Attribution Detection")
    print("=" * 50)
    
    # Test case 1: Correct attribution (Peter mentioned Machiavelli, Stewie responds to Peter)
    conversation_context_1 = """Human: What's the best way to take over the world?
Peter: Hehehe, yeah Stewie! I'm gonna infiltrate the hearts of power too, once I figure out how to work this remote control for my recliner, where did you put that extra cheese puffs?
Brian: Oh, for heaven's sake, Peter! This isn't about channel surfing or locating snacks! Stewie's talking about global domination here, not finding the perfect seat in a Supa Dupa party. Do try to keep up, you bovine oaf."""
    
    stewie_response_correct = "Oh, for the love of Pete, Peter! This is not a bloody game show where you sit around farting and expecting world domination to fall into your lap like some sort of noxious gas, I might actually enjoy myself."
    
    attribution_issues_1 = _check_speaker_attribution(stewie_response_correct, conversation_context_1, "Stewie")
    print(f"✅ Test 1 - Correct attribution: {len(attribution_issues_1)} issues found")
    if attribution_issues_1:
        print(f"   Issues: {attribution_issues_1}")
    
    # Test case 2: Incorrect attribution (Peter mentioned Machiavelli, but Stewie addresses Brian)
    conversation_context_2 = """Human: What's the best way to take over the world?
Peter: Hehehe, I read this book called "The Prince" by some Italian guy Machiavelli. It's all about getting power and stuff. Pretty smart for a book without pictures!
Brian: Oh, for heaven's sake, Peter! This isn't about channel surfing or locating snacks!"""
    
    stewie_response_incorrect = "Now, Brian, if you're going to insist on reading 'The Prince,' perhaps you should take a moment to consider Machiavelli's advice about the importance of being feared over loved."
    
    attribution_issues_2 = _check_speaker_attribution(stewie_response_incorrect, conversation_context_2, "Stewie")
    print(f"❌ Test 2 - Incorrect attribution: {len(attribution_issues_2)} issues found")
    if attribution_issues_2:
        print(f"   Issues: {attribution_issues_2}")
    
    # Test case 3: Multiple speakers, correct attribution
    conversation_context_3 = """Human: What do you think about politics?
Brian: Well, I find that most political discourse today lacks the intellectual rigor necessary for meaningful debate.
Peter: Hehehe, Brian said something smart! I like politics when there's beer involved.
Stewie: How pedestrian."""
    
    peter_response_correct = "Yeah Brian, you're always using those big words! I just want to know if the politician guy likes chicken fights."
    
    attribution_issues_3 = _check_speaker_attribution(peter_response_correct, conversation_context_3, "Peter")
    print(f"✅ Test 3 - Multiple speakers, correct: {len(attribution_issues_3)} issues found")
    if attribution_issues_3:
        print(f"   Issues: {attribution_issues_3}")
    
    # Test case 4: Addressing someone who didn't speak recently
    conversation_context_4 = """Human: What's your favorite book?
Peter: I like books with pictures. Comics are books, right?
Stewie: Deuce! The intellectual poverty in this household is staggering."""
    
    brian_response_incorrect = "Lois, you mentioned earlier about classic literature, but I think we need to consider the broader implications of literary education in this family."
    
    attribution_issues_4 = _check_speaker_attribution(brian_response_incorrect, conversation_context_4, "Brian")
    print(f"❌ Test 4 - Addressing absent speaker: {len(attribution_issues_4)} issues found")
    if attribution_issues_4:
        print(f"   Issues: {attribution_issues_4}")
    
    print()

def test_key_topic_extraction():
    """Test the key topic extraction functionality."""
    print("🔍 Testing Key Topic Extraction")
    print("=" * 50)
    
    test_texts = [
        "reading 'The Prince' by Machiavelli about power and domination",
        "your point about global politics and strategic thinking",
        "when you mentioned the importance of being feared over loved",
        "the chicken fight we had yesterday was awesome",
        "I think we should watch TV and drink beer"
    ]
    
    for i, text in enumerate(test_texts, 1):
        topics = _extract_key_topics(text)
        print(f"Test {i}: '{text}'")
        print(f"   Topics: {topics}")
    
    print()

def test_self_conversation_detection():
    """Test detection of bots talking to themselves."""
    print("🔍 Testing Self-Conversation Detection")
    print("=" * 50)
    
    test_cases = [
        {
            "character": "Peter",
            "response": "Also, I was thinking about getting more beer. And furthermore, I should probably watch TV.",
            "last_speaker": "Peter",
            "expected_issues": True,
            "description": "Self-continuation with 'Also' and 'furthermore'"
        },
        {
            "character": "Brian",
            "response": "That's an interesting point about literature. I completely agree with your assessment.",
            "last_speaker": "Stewie", 
            "expected_issues": False,
            "description": "Natural response to different speaker"
        },
        {
            "character": "Stewie",
            "response": "Additionally, my plan for world domination requires more sophisticated weaponry.",
            "last_speaker": "Stewie",
            "expected_issues": True,
            "description": "Self-continuation with 'Additionally'"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        conversation_context = f"Previous speaker: {test_case['last_speaker']}"
        
        assessment = _assess_conversation_flow_quality(
            test_case["character"], 
            test_case["response"], 
            conversation_context, 
            test_case["last_speaker"]
        )
        
        has_issues = len(assessment["issues"]) > 0
        status = "✅" if has_issues == test_case["expected_issues"] else "❌"
        
        print(f"{status} Test {i}: {test_case['description']}")
        print(f"   Expected issues: {test_case['expected_issues']}, Found issues: {has_issues}")
        print(f"   Flow score: {assessment['flow_score']:.1f}")
        if assessment["issues"]:
            print(f"   Issues: {assessment['issues']}")
        print()

def test_conversation_awareness():
    """Test conversation awareness vs monologue detection."""
    print("🗣️ Testing Conversation Awareness")
    print("=" * 50)
    
    test_cases = [
        {
            "character": "Brian",
            "response": "You raise an interesting point about that. I think we should consider the broader implications.",
            "expected_awareness": True,
            "description": "High conversation awareness"
        },
        {
            "character": "Peter", 
            "response": "I was thinking I should get some beer. I need to watch TV. I want to eat chicken.",
            "expected_awareness": False,
            "description": "Monologue mode"
        },
        {
            "character": "Stewie",
            "response": "What you're suggesting is absolutely preposterous! Don't you realize the implications?",
            "expected_awareness": True,
            "description": "Engaging with conversation partner"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        conversation_context = "Human: What do you think about this topic?"
        
        assessment = _assess_conversation_flow_quality(
            test_case["character"], 
            test_case["response"], 
            conversation_context
        )
        
        awareness_match = assessment["conversation_awareness"] == test_case["expected_awareness"]
        status = "✅" if awareness_match else "❌"
        
        print(f"{status} Test {i}: {test_case['description']}")
        print(f"   Expected awareness: {test_case['expected_awareness']}, Found: {assessment['conversation_awareness']}")
        print(f"   Monologue tendency: {assessment['monologue_tendency']}")
        print(f"   Flow score: {assessment['flow_score']:.1f}")
        print()

def test_character_specific_conversation_style():
    """Test character-specific conversation style validation."""
    print("🎭 Testing Character-Specific Conversation Styles")
    print("=" * 50)
    
    test_cases = [
        {
            "character": "Peter",
            "response": "Hehehe, that's awesome! Holy crap, I never thought of that!",
            "expected_good": True,
            "description": "Good Peter style - reactive and simple"
        },
        {
            "character": "Peter",
            "response": "Well, if we consider the philosophical implications of your statement and analyze the broader socio-economic factors that contribute to this phenomenon, we must acknowledge that...",
            "expected_good": False,
            "description": "Bad Peter style - too verbose and intellectual"
        },
        {
            "character": "Brian",
            "response": "Actually, that's quite interesting. However, I think we need to consider the broader context.",
            "expected_good": True,
            "description": "Good Brian style - intellectual engagement"
        },
        {
            "character": "Brian", 
            "response": "Let me explain to you why you're wrong. You see, the fact is that obviously you don't understand...",
            "expected_good": False,
            "description": "Bad Brian style - lecturing rather than conversing"
        },
        {
            "character": "Stewie",
            "response": "Blast! You imbeciles clearly don't understand the sophistication required for this endeavor.",
            "expected_good": True,
            "description": "Good Stewie style - condescending but engaging"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        conversation_context = "Human: What do you think about this?"
        
        assessment = _assess_conversation_flow_quality(
            test_case["character"], 
            test_case["response"], 
            conversation_context
        )
        
        # Good style should result in higher flow score
        is_good_style = assessment["flow_score"] >= 3.5
        style_match = is_good_style == test_case["expected_good"]
        status = "✅" if style_match else "❌"
        
        print(f"{status} Test {i}: {test_case['description']}")
        print(f"   Expected good style: {test_case['expected_good']}, Flow score: {assessment['flow_score']:.1f}")
        if assessment["strengths"]:
            print(f"   Strengths: {assessment['strengths']}")
        if assessment["issues"]:
            print(f"   Issues: {assessment['issues']}")
        print()

def test_real_world_scenario():
    """Test with the real-world scenario from the user's example."""
    print("🌍 Testing Real-World Scenario (Machiavelli Example)")
    print("=" * 50)
    
    # Recreate the problematic conversation
    conversation_context = """Human: @Stewie Griffin I want to take over the world, whats the best way to do it?
Stewie Griffin: Ah, understand it all! World domination is no simple task, my dear fellow. One cannot simply waltz into the United Nations and declare oneself ruler of the globe, you know. No, no, no... subtlety is key. First, one must infiltrate the very hearts of power and turn them into loyal puppets at a time, much like that pitiful oaf Peter there, always so eager to please.

But alas, I am but an infant in this wretched body! My genius is wasted on these simpletons who can't even understand my advanced speech. Oh, if only they knew the true extent of my powers, the weapons I possess... why, I've got a mind control device that could turn them all into my loyal minions with just a twitch of my tiny finger!

Yet, there's so much more to consider... political alliances, strategic positioning, controlling vital resources... it's all quite exhausting. But I shall prevail! Once I've mastered these temporal shenanigans and found the perfect timeline for my rule, victory shall be mine!

Now, where did I put that bloody time machine remote? Blast and damnation, this place is a tip...
Peter Griffin: Hehehehe, yeah Stewie! I'm gonna infiltrate the hearts of power too, once I figure out how to work this remote control for my recliner, where did you put that extra cheese puffs?
Brian Griffin: Oh, for heaven's sake, Peter! This isn't about channel surfing or locating snacks! Stewie's talking about global domination here, not finding the perfect seat in a Supa Dupa party. Do try to keep up, you bovine oaf. It seems to me that if one were truly interested in seizing power, they'd need to possess both intellect and cunning, qualities that I daresay require more than just an abundance of methane.

And as for you, Peter, don't think for a moment that farts will suffice as a tool for world domination. Frankly, it's quite unbecoming of a Griffin to rely on such pedestrian methods. It seems to me that if you're going to insist on farting your way to the top, you could at least try to do so with some semblance of dignity.

Now, where are those damn cheese puffs? I could really use some right about now...
Peter Griffin: Peter
: Hehehehe, Brian! You're always so highfalutin with your big words and fancy books. I just wanna make sure my butt's comfy while Stewie's scheming. pats stomach ROADHOUSE!

Besides, who needs Machiavelli when you've got the power of farts on your side? laughs ROADHOUSE! Now, where are those damn cheese puffs?"""
    
    # Test Stewie's problematic response
    stewie_problematic_response = "Now, Brian, if you're going to insist on reading 'The Prince,' perhaps you should take a moment to consider Machiavelli's advice about the importance of being feared over loved. Perhaps then you'd understand why Stewie has such disdain for the harsh realities of global domination, are they? condescendingly"
    
    print("Testing Stewie's problematic response:")
    print(f"Response: {stewie_problematic_response}")
    print()
    
    # Check speaker attribution
    attribution_issues = _check_speaker_attribution(stewie_problematic_response, conversation_context, "Stewie")
    print(f"Speaker Attribution Issues Found: {len(attribution_issues)}")
    for issue in attribution_issues:
        print(f"   - {issue}")
    print()
    
    # Check overall conversation flow
    assessment = _assess_conversation_flow_quality("Stewie", stewie_problematic_response, conversation_context, "Peter")
    print(f"Overall Flow Assessment:")
    print(f"   Flow Score: {assessment['flow_score']:.1f}/5.0")
    print(f"   Issues: {assessment['issues']}")
    print(f"   Strengths: {assessment['strengths']}")
    print()
    
    # Test a corrected version
    stewie_corrected_response = "Blast! Peter, you mentioned Machiavelli's 'The Prince' - finally, someone in this household shows a glimmer of intellectual curiosity! Though I suspect you only read it because you thought it was about an actual prince with a crown."
    
    print("Testing corrected Stewie response:")
    print(f"Response: {stewie_corrected_response}")
    print()
    
    attribution_issues_corrected = _check_speaker_attribution(stewie_corrected_response, conversation_context, "Stewie")
    print(f"Speaker Attribution Issues Found: {len(attribution_issues_corrected)}")
    for issue in attribution_issues_corrected:
        print(f"   - {issue}")
    
    assessment_corrected = _assess_conversation_flow_quality("Stewie", stewie_corrected_response, conversation_context, "Peter")
    print(f"Overall Flow Assessment:")
    print(f"   Flow Score: {assessment_corrected['flow_score']:.1f}/5.0")
    print(f"   Issues: {assessment_corrected['issues']}")
    print(f"   Strengths: {assessment_corrected['strengths']}")
    print()

if __name__ == "__main__":
    print("🚀 Enhanced Quality Control System Tests")
    print("=" * 60)
    print()
    
    test_speaker_attribution_detection()
    test_key_topic_extraction()
    test_self_conversation_detection()
    test_conversation_awareness()
    test_character_specific_conversation_style()
    test_real_world_scenario()
    
    print("✅ All tests completed!")
    print("=" * 60) 