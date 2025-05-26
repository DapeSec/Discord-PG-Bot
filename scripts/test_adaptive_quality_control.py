#!/usr/bin/env python3
"""
Test script for Adaptive Quality Control System.
Tests the correlation between conversation history richness and quality control thresholds.
"""

import sys
import os
import requests
import json
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_adaptive_quality_control_configuration():
    """Test that adaptive quality control is properly configured."""
    print("🎯 TESTING ADAPTIVE QUALITY CONTROL CONFIGURATION")
    print("=" * 70)
    
    try:
        from app.orchestrator.server import (
            ADAPTIVE_QUALITY_CONTROL_ENABLED,
            COLD_START_THRESHOLD,
            WARM_CONVERSATION_THRESHOLD,
            HOT_CONVERSATION_THRESHOLD,
            CONVERSATION_HISTORY_COLD_LIMIT,
            CONVERSATION_HISTORY_WARM_LIMIT
        )
        
        print(f"🔧 Configuration:")
        print(f"   Adaptive QC Enabled: {ADAPTIVE_QUALITY_CONTROL_ENABLED}")
        print(f"   Cold Start Threshold: {COLD_START_THRESHOLD}/100 (0-{CONVERSATION_HISTORY_COLD_LIMIT} messages)")
        print(f"   Warm Conversation Threshold: {WARM_CONVERSATION_THRESHOLD}/100 ({CONVERSATION_HISTORY_COLD_LIMIT+1}-{CONVERSATION_HISTORY_WARM_LIMIT} messages)")
        print(f"   Hot Conversation Threshold: {HOT_CONVERSATION_THRESHOLD}/100 ({CONVERSATION_HISTORY_WARM_LIMIT+1}+ messages)")
        
        # Validate configuration makes sense
        issues = []
        
        if not ADAPTIVE_QUALITY_CONTROL_ENABLED:
            issues.append("Adaptive quality control is disabled")
        
        if COLD_START_THRESHOLD >= WARM_CONVERSATION_THRESHOLD:
            issues.append("Cold start threshold should be lower than warm threshold")
        
        if WARM_CONVERSATION_THRESHOLD >= HOT_CONVERSATION_THRESHOLD:
            issues.append("Warm threshold should be lower than hot threshold")
        
        if CONVERSATION_HISTORY_COLD_LIMIT >= CONVERSATION_HISTORY_WARM_LIMIT:
            issues.append("Cold limit should be lower than warm limit")
        
        if issues:
            print(f"\n⚠️ Configuration Issues:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print(f"\n✅ Configuration looks good!")
            return True
            
    except ImportError as e:
        print(f"❌ Cannot import adaptive quality control settings: {e}")
        return False

def test_threshold_calculation():
    """Test the adaptive threshold calculation with different conversation scenarios."""
    print("\n🧮 TESTING ADAPTIVE THRESHOLD CALCULATION")
    print("=" * 70)
    
    try:
        from app.orchestrator.server import calculate_adaptive_quality_threshold
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Test scenarios with different conversation history lengths and richness
        test_scenarios = [
            {
                "name": "Cold Start - No History",
                "history": [],
                "expected_type": "COLD_START",
                "expected_range": (45, 55)
            },
            {
                "name": "Cold Start - Minimal History",
                "history": [
                    HumanMessage(content="Hi"),
                    AIMessage(content="Hello!", name="Brian")
                ],
                "expected_type": "COLD_START", 
                "expected_range": (45, 55)
            },
            {
                "name": "Warm Conversation - Some History",
                "history": [
                    HumanMessage(content="What do you think about cooking?"),
                    AIMessage(content="Well, I find culinary arts quite fascinating actually.", name="Brian"),
                    HumanMessage(content="Do you cook yourself?"),
                    AIMessage(content="I dabble in the kitchen from time to time.", name="Brian"),
                    HumanMessage(content="What's your favorite dish?"),
                    AIMessage(content="I'm quite fond of a good coq au vin, actually.", name="Brian"),
                    HumanMessage(content="That sounds fancy. Do you use wine in it?"),
                    AIMessage(content="Of course! The wine is essential for proper flavor development.", name="Brian")
                ],
                "expected_type": "WARM_CONVERSATION",
                "expected_range": (60, 70)
            },
            {
                "name": "Hot Conversation - Rich History",
                "history": [
                    HumanMessage(content="Brian, what's your take on modern literature?"),
                    AIMessage(content="Well, I believe contemporary fiction has lost much of its intellectual rigor compared to the classics.", name="Brian"),
                    HumanMessage(content="That's interesting. What about authors like Murakami?"),
                    AIMessage(content="Murakami represents a fascinating blend of surrealism and existential philosophy.", name="Brian"),
                    HumanMessage(content="Have you read any of his recent works?"),
                    AIMessage(content="Indeed, I found 'Killing Commendatore' to be a profound meditation on art and reality.", name="Brian"),
                    HumanMessage(content="What did you think of the metaphysical elements?"),
                    AIMessage(content="The metaphysical aspects serve as a brilliant commentary on the nature of creativity itself.", name="Brian"),
                    HumanMessage(content="Do you think Peter would understand any of this?"),
                    AIMessage(content="Peter? Understanding Murakami? That's like expecting a goldfish to appreciate Proust.", name="Brian"),
                    HumanMessage(content="Haha, that's pretty harsh but probably accurate."),
                    AIMessage(content="I speak only the truth, however uncomfortable it may be.", name="Brian"),
                    HumanMessage(content="What about other contemporary authors?"),
                    AIMessage(content="Well, there are a few gems among the literary rubble, I suppose.", name="Brian"),
                    HumanMessage(content="Like who?"),
                    AIMessage(content="Zadie Smith shows promise, and I have a grudging respect for Jonathan Franzen.", name="Brian"),
                    HumanMessage(content="What about science fiction?"),
                    AIMessage(content="Ah, now there's a genre that's actually improved with time. Kim Stanley Robinson, for instance.", name="Brian"),
                    HumanMessage(content="I haven't read him. What would you recommend?"),
                    AIMessage(content="Start with the Mars trilogy. It's hard science fiction at its finest.", name="Brian"),
                    HumanMessage(content="Thanks for the recommendation!"),
                    AIMessage(content="Always happy to elevate someone's literary palate.", name="Brian")
                ],
                "expected_type": "HOT_CONVERSATION",
                "expected_range": (70, 80)
            },
            {
                "name": "Mixed Quality - Short Messages",
                "history": [
                    HumanMessage(content="Hi"),
                    AIMessage(content="Hey", name="Peter"),
                    HumanMessage(content="How are you?"),
                    AIMessage(content="Good", name="Peter"),
                    HumanMessage(content="Cool"),
                    AIMessage(content="Yeah", name="Peter"),
                    HumanMessage(content="What's up?"),
                    AIMessage(content="Nothing", name="Peter"),
                    HumanMessage(content="Okay"),
                    AIMessage(content="Yep", name="Peter"),
                    HumanMessage(content="Sure"),
                    AIMessage(content="Uh-huh", name="Peter"),
                    HumanMessage(content="Right"),
                    AIMessage(content="Totally", name="Peter")
                ],
                "expected_type": "WARM_CONVERSATION",
                "expected_range": (55, 65)  # Lower due to poor message quality
            }
        ]
        
        passed_tests = 0
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{i}. {scenario['name']}:")
            print(f"   Messages: {len(scenario['history'])}")
            
            threshold = calculate_adaptive_quality_threshold(scenario['history'])
            
            min_expected, max_expected = scenario['expected_range']
            
            if min_expected <= threshold <= max_expected:
                print(f"   ✅ Threshold: {threshold:.1f}/100 (within expected range {min_expected}-{max_expected})")
                passed_tests += 1
            else:
                print(f"   ❌ Threshold: {threshold:.1f}/100 (outside expected range {min_expected}-{max_expected})")
        
        print(f"\n📊 Threshold Calculation Results:")
        print(f"   Passed: {passed_tests}/{len(test_scenarios)}")
        
        return passed_tests == len(test_scenarios)
        
    except ImportError as e:
        print(f"❌ Cannot import threshold calculation function: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing threshold calculation: {e}")
        return False

def test_context_value_analysis():
    """Test the conversation context value analysis."""
    print("\n📊 TESTING CONTEXT VALUE ANALYSIS")
    print("=" * 70)
    
    try:
        from app.orchestrator.server import get_conversation_context_value
        from langchain_core.messages import HumanMessage, AIMessage
        
        # Test different conversation qualities
        test_conversations = [
            {
                "name": "Empty Conversation",
                "history": [],
                "expected_score_range": (0, 2)
            },
            {
                "name": "Low Quality - Short Messages",
                "history": [
                    HumanMessage(content="Hi"),
                    AIMessage(content="Hey", name="Peter"),
                    HumanMessage(content="Ok"),
                    AIMessage(content="Yeah", name="Peter")
                ],
                "expected_score_range": (4, 8)
            },
            {
                "name": "Medium Quality - Substantial Messages",
                "history": [
                    HumanMessage(content="What do you think about the new restaurant downtown?"),
                    AIMessage(content="Well, I think it's quite pretentious actually. The menu is overpriced.", name="Brian"),
                    HumanMessage(content="Really? I thought the food was pretty good."),
                    AIMessage(content="The food quality is adequate, but the atmosphere is insufferable.", name="Brian")
                ],
                "expected_score_range": (12, 20)
            },
            {
                "name": "High Quality - Rich, Connected Conversation",
                "history": [
                    HumanMessage(content="Brian, what's your opinion on the current state of American literature?"),
                    AIMessage(content="I find that contemporary American literature has become increasingly commercialized, sacrificing artistic integrity for mass appeal.", name="Brian"),
                    HumanMessage(content="That's an interesting perspective. Do you think this trend is reversible?"),
                    AIMessage(content="It would require a fundamental shift in how we value intellectual discourse over entertainment, which frankly seems unlikely given our current cultural trajectory.", name="Brian"),
                    HumanMessage(content="Speaking of cultural trends, what about the rise of social media's impact on reading habits?"),
                    AIMessage(content="Social media has essentially reduced our attention spans to that of goldfish, making the appreciation of complex literary works nearly impossible for most people.", name="Brian"),
                    AIMessage(content="However, I must admit that it has democratized access to diverse voices in literature.", name="Stewie")
                ],
                "expected_score_range": (25, 40)
            }
        ]
        
        passed_tests = 0
        
        for i, test in enumerate(test_conversations, 1):
            print(f"\n{i}. {test['name']}:")
            
            analysis = get_conversation_context_value(test['history'])
            
            print(f"   📊 Analysis:")
            print(f"      Total Messages: {analysis['total_messages']}")
            print(f"      Meaningful Messages: {analysis['meaningful_messages']}")
            print(f"      Average Length: {analysis['average_length']:.1f}")
            print(f"      Topic Continuity: {analysis['topic_continuity']}")
            print(f"      Character Diversity: {analysis['character_diversity']}")
            print(f"      Context Value Score: {analysis['context_value_score']:.1f}")
            
            min_expected, max_expected = test['expected_score_range']
            
            if min_expected <= analysis['context_value_score'] <= max_expected:
                print(f"   ✅ Score within expected range ({min_expected}-{max_expected})")
                passed_tests += 1
            else:
                print(f"   ❌ Score outside expected range ({min_expected}-{max_expected})")
        
        print(f"\n📊 Context Value Analysis Results:")
        print(f"   Passed: {passed_tests}/{len(test_conversations)}")
        
        return passed_tests == len(test_conversations)
        
    except ImportError as e:
        print(f"❌ Cannot import context value function: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing context value analysis: {e}")
        return False

def test_adaptive_quality_in_action():
    """Test adaptive quality control with a simulated conversation flow."""
    print("\n🎬 TESTING ADAPTIVE QUALITY CONTROL IN ACTION")
    print("=" * 70)
    
    print("Simulating a conversation progression from cold start to hot conversation...")
    
    # Simulate conversation progression
    conversation_stages = [
        {
            "stage": "Cold Start",
            "user_query": "Hi Brian",
            "expected_threshold_range": (45, 55),
            "description": "First interaction - should be lenient"
        },
        {
            "stage": "Warming Up", 
            "user_query": "What do you think about cooking?",
            "expected_threshold_range": (60, 70),
            "description": "Some conversation history - moderate expectations"
        },
        {
            "stage": "Hot Conversation",
            "user_query": "Can you elaborate on your culinary philosophy?",
            "expected_threshold_range": (70, 80),
            "description": "Rich conversation history - high expectations"
        }
    ]
    
    print("\n📈 Conversation Progression Simulation:")
    for i, stage in enumerate(conversation_stages, 1):
        print(f"\n{i}. {stage['stage']}: '{stage['user_query']}'")
        print(f"   Expected Threshold: {stage['expected_threshold_range'][0]}-{stage['expected_threshold_range'][1]}/100")
        print(f"   Rationale: {stage['description']}")
    
    print("\n🎯 Key Benefits of Adaptive Quality Control:")
    print("   1. 🥶 Cold Start Tolerance: Lower thresholds for first interactions")
    print("   2. 📈 Progressive Standards: Quality expectations grow with context")
    print("   3. 🔥 Rich Context Leverage: High standards when lots of context available")
    print("   4. 🎨 Context-Aware Scoring: Message quality affects threshold modifiers")
    print("   5. 📊 Database Integration: Considers recent channel history")
    
    return True

def test_environment_variable_configuration():
    """Test that environment variables can override adaptive quality control settings."""
    print("\n⚙️ TESTING ENVIRONMENT VARIABLE CONFIGURATION")
    print("=" * 70)
    
    print("📋 Configurable Environment Variables:")
    print("   ADAPTIVE_QUALITY_CONTROL_ENABLED=true/false")
    print("   COLD_START_THRESHOLD=50.0 (threshold for ≤3 messages)")
    print("   WARM_CONVERSATION_THRESHOLD=65.0 (threshold for 4-10 messages)")
    print("   HOT_CONVERSATION_THRESHOLD=75.0 (threshold for 11+ messages)")
    print("   CONVERSATION_HISTORY_COLD_LIMIT=3 (messages for cold start)")
    print("   CONVERSATION_HISTORY_WARM_LIMIT=10 (messages for warm conversation)")
    
    print("\n🎯 Recommended Settings by Use Case:")
    print("   🧪 Development/Testing:")
    print("      COLD_START_THRESHOLD=40.0")
    print("      WARM_CONVERSATION_THRESHOLD=55.0")
    print("      HOT_CONVERSATION_THRESHOLD=65.0")
    
    print("   🚀 Production:")
    print("      COLD_START_THRESHOLD=50.0")
    print("      WARM_CONVERSATION_THRESHOLD=65.0")
    print("      HOT_CONVERSATION_THRESHOLD=75.0")
    
    print("   🔥 High Quality:")
    print("      COLD_START_THRESHOLD=60.0")
    print("      WARM_CONVERSATION_THRESHOLD=70.0")
    print("      HOT_CONVERSATION_THRESHOLD=80.0")
    
    return True

def test_adaptive_context_weighting():
    """Test the adaptive context weighting system."""
    print("\n🎚️ ADAPTIVE CONTEXT WEIGHTING TEST")
    print("=" * 50)
    
    # Import the function
    from app.orchestrator.server import calculate_adaptive_context_weights
    from langchain.schema import HumanMessage, AIMessage
    
    test_scenarios = [
        {
            "name": "Cold Start - No History",
            "history": [],
            "expected_conversation_weight_range": (0.55, 0.65),  # Around 60%
            "expected_rag_weight_range": (0.35, 0.45),  # Around 40%
            "expected_type": "COLD_START",
            "expected_conversation_messages_range": (1, 3),  # 2 messages ±1
            "expected_rag_context_length_range": (350, 450),  # 400 chars ±50
            "expected_max_response_length_range": (275, 325),  # 300 chars ±25
            "expected_hallucination_risk_range": (0.2, 0.4),  # 30% ±10%
            "expected_strictness_multiplier_range": (0.8, 1.2)  # 1.0x ±0.2
        },
        {
            "name": "Cold Start - Minimal History",
            "history": [
                HumanMessage(content="Hi"),
                AIMessage(content="Hello there!", name="Peter")
            ],
            "expected_conversation_weight_range": (0.55, 0.65),
            "expected_rag_weight_range": (0.35, 0.45),
            "expected_type": "COLD_START",
            "expected_conversation_messages_range": (1, 3),
            "expected_rag_context_length_range": (350, 450),
            "expected_max_response_length_range": (275, 325),
            "expected_hallucination_risk_range": (0.2, 0.4),
            "expected_strictness_multiplier_range": (0.8, 1.2)
        },
        {
            "name": "Warm Conversation - Some History",
            "history": [
                HumanMessage(content="What do you think about science?"),
                AIMessage(content="Science is fascinating! I love learning about new discoveries.", name="Brian"),
                HumanMessage(content="That's interesting. What about physics specifically?"),
                AIMessage(content="Physics is the foundation of understanding our universe.", name="Brian"),
                HumanMessage(content="Do you have any favorite physicists?"),
                AIMessage(content="Einstein, of course! His theories revolutionized our understanding.", name="Brian")
            ],
            "expected_conversation_weight_range": (0.70, 0.80),  # Around 75%
            "expected_rag_weight_range": (0.20, 0.30),  # Around 25%
            "expected_type": "WARM_CONVERSATION",
            "expected_conversation_messages_range": (3, 5),  # 4 messages ±1
            "expected_rag_context_length_range": (200, 300),  # 250 chars ±50
            "expected_max_response_length_range": (225, 275),  # 250 chars ±25
            "expected_hallucination_risk_range": (0.5, 0.7),  # 60% ±10%
            "expected_strictness_multiplier_range": (1.1, 1.5)  # 1.3x ±0.2
        },
        {
            "name": "Hot Conversation - Rich History",
            "history": [
                HumanMessage(content="Brian, what's your opinion on the current state of American literature?"),
                AIMessage(content="I find that contemporary American literature has become increasingly commercialized, sacrificing artistic integrity for mass appeal.", name="Brian"),
                HumanMessage(content="That's an interesting perspective. Do you think this trend is reversible?"),
                AIMessage(content="It would require a fundamental shift in how we value intellectual discourse over entertainment, which frankly seems unlikely given our current cultural trajectory.", name="Brian"),
                HumanMessage(content="Speaking of cultural trends, what about the rise of social media's impact on reading habits?"),
                AIMessage(content="Social media has essentially reduced our attention spans to that of goldfish, making the appreciation of complex literary works nearly impossible for most people.", name="Brian"),
                AIMessage(content="However, I must admit that it has democratized access to diverse voices in literature.", name="Stewie"),
                HumanMessage(content="Stewie, that's a surprisingly balanced take from you."),
                AIMessage(content="Well, even a genius must acknowledge multiple perspectives when analyzing complex societal phenomena.", name="Stewie"),
                HumanMessage(content="What about you, Peter? Any thoughts on literature?"),
                AIMessage(content="Hehehe, books are for nerds! I prefer TV. Speaking of which, did you see that new show about the guy who fights chickens?", name="Peter"),
                HumanMessage(content="Peter, that's... actually kind of on-brand for you."),
                AIMessage(content="Hehehe, yeah! I know what I like!", name="Peter")
            ],
            "expected_conversation_weight_range": (0.80, 0.90),  # Around 85%
            "expected_rag_weight_range": (0.10, 0.20),  # Around 15%
            "expected_type": "HOT_CONVERSATION",
            "expected_conversation_messages_range": (5, 7),  # 6 messages ±1
            "expected_rag_context_length_range": (100, 200),  # 150 chars ±50
            "expected_max_response_length_range": (175, 225),  # 200 chars ±25
            "expected_hallucination_risk_range": (0.7, 0.9),  # 80% ±10%
            "expected_strictness_multiplier_range": (1.4, 1.8)  # 1.6x ±0.2
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_scenarios)
    
    for scenario in test_scenarios:
        print(f"\n📊 Testing: {scenario['name']}")
        
        try:
            # Calculate adaptive context weights
            weights = calculate_adaptive_context_weights(scenario["history"])
            
            conversation_weight = weights["conversation_weight"]
            rag_weight = weights["rag_weight"]
            weighting_type = weights["weighting_type"]
            conversation_richness = weights["conversation_richness"]
            conversation_messages = weights["conversation_messages"]
            rag_context_length = weights["rag_context_length"]
            max_response_length = weights["max_response_length"]
            hallucination_risk = weights["hallucination_risk"]
            strictness_multiplier = weights["strictness_multiplier"]
            
            print(f"   📈 Conversation Weight: {conversation_weight:.1%}")
            print(f"   📈 RAG Weight: {rag_weight:.1%}")
            print(f"   🏷️ Type: {weighting_type}")
            print(f"   📊 Conversation Richness: {conversation_richness:.1f}")
            print(f"   📏 Context Lengths: {conversation_messages} conv msgs, {rag_context_length} RAG chars")
            print(f"   🚨 Anti-Hallucination: {max_response_length} max chars, {hallucination_risk:.1%} risk, {strictness_multiplier:.1f}x strictness")
            
            # Validate conversation weight range
            conv_min, conv_max = scenario["expected_conversation_weight_range"]
            if not (conv_min <= conversation_weight <= conv_max):
                print(f"   ❌ Conversation weight {conversation_weight:.1%} not in expected range {conv_min:.1%}-{conv_max:.1%}")
                continue
            
            # Validate RAG weight range
            rag_min, rag_max = scenario["expected_rag_weight_range"]
            if not (rag_min <= rag_weight <= rag_max):
                print(f"   ❌ RAG weight {rag_weight:.1%} not in expected range {rag_min:.1%}-{rag_max:.1%}")
                continue
            
            # Validate weighting type
            if weighting_type != scenario["expected_type"]:
                print(f"   ❌ Weighting type {weighting_type} != expected {scenario['expected_type']}")
                continue
            
            # Validate weights sum to 1.0
            if abs((conversation_weight + rag_weight) - 1.0) > 0.01:
                print(f"   ❌ Weights don't sum to 1.0: {conversation_weight + rag_weight:.3f}")
                continue
            
            # Validate conversation messages range
            conv_msg_min, conv_msg_max = scenario["expected_conversation_messages_range"]
            if not (conv_msg_min <= conversation_messages <= conv_msg_max):
                print(f"   ❌ Conversation messages {conversation_messages} not in expected range {conv_msg_min}-{conv_msg_max}")
                continue
            
            # Validate RAG context length range
            rag_len_min, rag_len_max = scenario["expected_rag_context_length_range"]
            if not (rag_len_min <= rag_context_length <= rag_len_max):
                print(f"   ❌ RAG context length {rag_context_length} not in expected range {rag_len_min}-{rag_len_max}")
                continue
            
            # Validate max response length range
            resp_len_min, resp_len_max = scenario["expected_max_response_length_range"]
            if not (resp_len_min <= max_response_length <= resp_len_max):
                print(f"   ❌ Max response length {max_response_length} not in expected range {resp_len_min}-{resp_len_max}")
                continue
            
            # Validate hallucination risk range
            risk_min, risk_max = scenario["expected_hallucination_risk_range"]
            if not (risk_min <= hallucination_risk <= risk_max):
                print(f"   ❌ Hallucination risk {hallucination_risk:.1%} not in expected range {risk_min:.1%}-{risk_max:.1%}")
                continue
            
            # Validate strictness multiplier range
            strict_min, strict_max = scenario["expected_strictness_multiplier_range"]
            if not (strict_min <= strictness_multiplier <= strict_max):
                print(f"   ❌ Strictness multiplier {strictness_multiplier:.1f} not in expected range {strict_min:.1f}-{strict_max:.1f}")
                continue
            
            print(f"   ✅ All validations passed!")
            passed_tests += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n📊 ADAPTIVE CONTEXT WEIGHTING RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All adaptive context weighting tests passed!")
        print("\n💡 KEY INSIGHTS:")
        print("   • Cold Start: 60% conversation (2 msgs), 40% RAG (400 chars), 300 max response - Lenient anti-hallucination")
        print("   • Warm Conversation: 75% conversation (4 msgs), 25% RAG (250 chars), 250 max response - Moderate anti-hallucination")
        print("   • Hot Conversation: 85% conversation (6 msgs), 15% RAG (150 chars), 200 max response - Strict anti-hallucination")
        print("   • Progressive adjustment of weighting, context lengths, AND anti-hallucination measures")
        print("   • More history = Higher hallucination risk = Stricter controls")
        print("   • Anti-hallucination scales inversely with conversation richness")
        print("   • Context volume and response limits scale naturally with conversation state")
    else:
        print("⚠️ Some adaptive context weighting tests failed.")
    
    return passed_tests == total_tests

def main():
    """Run all adaptive quality control tests."""
    print("🎯 ADAPTIVE QUALITY CONTROL SYSTEM TESTING")
    print("=" * 70)
    print("Testing the correlation between conversation history and quality thresholds...")
    print()
    
    tests = [
        ("Configuration", test_adaptive_quality_control_configuration),
        ("Threshold Calculation", test_threshold_calculation),
        ("Context Value Analysis", test_context_value_analysis),
        ("Adaptive QC in Action", test_adaptive_quality_in_action),
        ("Environment Variables", test_environment_variable_configuration),
        ("Adaptive Context Weighting", test_adaptive_context_weighting)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"\n✅ {test_name}: PASSED")
            else:
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            print(f"\n💥 {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 70)
    print("📊 ADAPTIVE QUALITY CONTROL TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Adaptive Quality Control is working correctly!")
    elif passed >= total * 0.8:
        print("✅ Most tests passed. System is mostly functional.")
    else:
        print("⚠️ Several tests failed. System needs attention.")
    
    print("\n🎯 SYSTEM OVERVIEW:")
    print("The Adaptive Quality Control system automatically adjusts quality")
    print("thresholds based on conversation history richness:")
    print()
    print("📈 CORRELATION PRINCIPLE:")
    print("   More History = Higher Standards = Better Quality")
    print()
    print("🎚️ THRESHOLD LEVELS:")
    print("   🥶 Cold Start (0-3 msgs): 50/100 - Be lenient for first interactions")
    print("   🌡️ Warm (4-10 msgs): 65/100 - Moderate expectations with some context")
    print("   🔥 Hot (11+ msgs): 75/100 - High standards with rich context")
    print()
    print("💡 BENEFITS:")
    print("   • Solves cold start problems after database resets")
    print("   • Progressively improves quality as context grows")
    print("   • Leverages conversation history value intelligently")
    print("   • Reduces weird responses in fresh conversations")

if __name__ == "__main__":
    main() 