#!/usr/bin/env python3
"""
Test script for the Supervised Fine-Tuning System.
Demonstrates LLM-based automatic rating and manual rating capabilities.
"""

import requests
import json
import time

# Configuration
ORCHESTRATOR_URL = "http://localhost:5003"

def test_fine_tuning_system():
    """Test the fine-tuning system with sample data and LLM auto-assessment."""
    
    print("🎯 Testing Supervised Fine-Tuning System with LLM Auto-Assessment")
    print("=" * 60)
    
    # Test 1: Get initial stats
    print("\n📊 1. Getting initial fine-tuning statistics...")
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/fine_tuning_stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Current stats:")
            print(f"   📈 Total ratings: {stats['overview']['total_ratings']}")
            print(f"   🔧 Total optimizations: {stats['overview']['total_optimizations']}")
            for char, char_stats in stats['characters'].items():
                avg_rating = char_stats['latest_avg_rating']
                rating_text = f"{avg_rating:.1f}/5" if avg_rating else "No ratings yet"
                print(f"   🎭 {char}: {char_stats['total_ratings']} ratings, avg: {rating_text}")
        else:
            print(f"❌ Error getting stats: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    # Test 2: Show how LLM auto-assessment works
    print("\n🤖 2. LLM Auto-Assessment in Action")
    print("   ℹ️  The system now automatically rates every response using LLM evaluation!")
    print("   ℹ️  To see this in action, send a message to any bot and watch the logs.")
    print("   ℹ️  The LLM will assess character accuracy and record ratings automatically.")
    
    # Test 3: Add some manual ratings for comparison
    print("\n📝 3. Adding manual response ratings for comparison...")
    
    sample_ratings = [
        {
            "character_name": "Peter",
            "response_text": "Hehehehehe! Holy crap, that's awesome! This is worse than that time I tried to be a football player and ended up fighting the mascot!",
            "conversation_context": "User asked about playing professional football",
            "rating": 5,
            "feedback": "Perfect Peter voice - has the laugh, catchphrase, random tangent, and typical Peter behavior",
            "user_id": "human_evaluator_1"
        },
        {
            "character_name": "Peter",
            "response_text": "I find that your inquiry regarding professional athletics requires a sophisticated analysis of the physiological demands and strategic complexities involved in such endeavors.",
            "conversation_context": "User asked about playing professional football",
            "rating": 1,
            "feedback": "Completely out of character - way too intellectual and formal for Peter, sounds exactly like Brian",
            "user_id": "human_evaluator_2"
        },
        {
            "character_name": "Brian",
            "response_text": "Well, actually, the world of professional athletics is a fascinating study in human physical and psychological limits. The intersection of talent, dedication, and societal pressures creates a complex paradigm...",
            "conversation_context": "Discussion about sports capabilities",
            "rating": 5,
            "feedback": "Perfect Brian voice - condescending 'well actually', intellectual vocabulary, pretentious analysis",
            "user_id": "human_evaluator_3"
        },
        {
            "character_name": "Stewie",
            "response_text": "What the deuce? You think that oaf could play professional football? Blast, I could engineer a superior athlete in my laboratory using nothing but spare parts and sheer brilliance!",
            "conversation_context": "Commenting on Peter's athletic abilities",
            "rating": 5,
            "feedback": "Absolutely perfect Stewie - British exclamations, condescending tone, scientific confidence, calls Peter an oaf",
            "user_id": "human_evaluator_4"
        }
    ]
    
    for i, rating_data in enumerate(sample_ratings):
        print(f"   📝 Rating {i+1}/4: {rating_data['character_name']} - {rating_data['rating']}/5")
        print(f"      💬 Response: '{rating_data['response_text'][:60]}...'")
        try:
            response = requests.post(
                f"{ORCHESTRATOR_URL}/rate_response",
                json=rating_data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"      ✅ Recorded: {result['rating_id']}")
            else:
                print(f"      ❌ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"      ❌ Error rating response: {e}")
        
        time.sleep(0.5)  # Small delay between requests
    
    # Test 4: Show optimization capabilities
    print("\n🔧 4. Testing optimization capabilities...")
    
    # Add several low ratings to trigger optimization
    print("   📉 Adding some poor ratings to demonstrate optimization...")
    poor_ratings = [
        {"rating": 2, "feedback": "Missing Peter's signature laugh and speech patterns"},
        {"rating": 1, "feedback": "Way too smart and sophisticated for Peter Griffin"},
        {"rating": 2, "feedback": "Doesn't capture Peter's childlike enthusiasm"},
        {"rating": 1, "feedback": "Sounds more like Brian than Peter"},
        {"rating": 2, "feedback": "Missing key catchphrases and Peter's simple vocabulary"},
    ]
    
    for i, poor_rating in enumerate(poor_ratings):
        rating_data = {
            "character_name": "Peter",
            "response_text": f"I believe we should contemplate the philosophical implications of this discourse. The nuanced complexities require careful intellectual analysis and sophisticated reasoning. Furthermore, one must consider...",
            "conversation_context": "User asking Peter about something simple",
            "rating": poor_rating["rating"],
            "feedback": poor_rating["feedback"],
            "user_id": f"human_evaluator_{i+10}"
        }
        
        try:
            response = requests.post(
                f"{ORCHESTRATOR_URL}/rate_response",
                json=rating_data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                print(f"      ⬇️ Added poor rating: {poor_rating['rating']}/5")
            else:
                print(f"      ❌ Error: {response.text}")
        except Exception as e:
            print(f"      ❌ Error: {e}")
        
        time.sleep(0.2)
    
    # Test 5: Trigger optimization
    print("\n🎯 5. Triggering prompt optimization...")
    try:
        response = requests.post(
            f"{ORCHESTRATOR_URL}/trigger_optimization",
            json={"character_name": "Peter", "force": True},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Optimization triggered: {result['status']}")
            print(f"   📊 Ratings analyzed: {result['ratings_analyzed']}")
        else:
            print(f"❌ Error triggering optimization: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: Show updated performance
    print("\n📈 6. Performance after optimization...")
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/optimization_report")
        if response.status_code == 200:
            report = response.json()
            print(f"✅ Optimization report:")
            for char, char_data in report['report']['characters'].items():
                latest_rating = char_data['latest_rating']
                rating_text = f"{latest_rating:.1f}/5" if latest_rating else "No ratings"
                prompt_versions = char_data['prompt_versions']
                print(f"   🎭 {char}: {rating_text}, {prompt_versions} prompt versions")
                if char_data['current_issues']:
                    print(f"      ⚠️ Issues: {', '.join(char_data['current_issues'][:2])}")
                if char_data['current_strengths']:
                    print(f"      ✨ Strengths: {', '.join(char_data['current_strengths'][:2])}")
        else:
            print(f"❌ Error getting report: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 7: Final demonstration
    print("\n🎉 7. System Features Summary")
    print("=" * 60)
    print("✅ LLM AUTO-ASSESSMENT:")
    print("   🤖 Every bot response is automatically evaluated by LLM")
    print("   📊 Ratings are recorded with detailed feedback")
    print("   🔍 Assessment includes reasoning, strengths, weaknesses, suggestions")
    print("   ⚡ No manual intervention required!")
    
    print("\n✅ MANUAL RATINGS (Optional):")
    print("   👤 Users can still provide manual ratings for additional data")
    print("   🎯 Manual ratings can override or supplement auto-assessments")
    print("   📝 Detailed feedback helps improve optimization")
    
    print("\n✅ AUTOMATIC OPTIMIZATION:")
    print("   🔧 Prompts are automatically optimized when ratings drop")
    print("   🧪 A/B testing ensures new prompts actually improve quality")
    print("   📈 System learns and improves character accuracy over time")
    
    print("\n✅ REAL-TIME MONITORING:")
    print("   📊 Track performance metrics and optimization progress")
    print("   🎭 Character-specific analysis and improvement suggestions")
    print("   📈 Historical data shows improvement trends")
    
    print(f"\n🚀 The system is now fully autonomous!")
    print(f"   💬 Chat with the bots to see LLM auto-assessment in action")
    print(f"   📊 Check /fine_tuning_stats for real-time performance data")
    print(f"   🔧 Optimizations happen automatically based on quality")

def demo_llm_assessment():
    """Demonstrate how to manually test the LLM assessment system."""
    
    print("\n🧪 LLM Assessment Demo")
    print("=" * 30)
    
    # Example of testing LLM assessment directly
    test_responses = [
        {
            "character": "Peter",
            "good_response": "Hehehehehe! Holy crap, that's freakin' awesome! This is worse than that time I tried to become a professional wrestler and accidentally joined a book club instead!",
            "bad_response": "I believe we should engage in a sophisticated discourse regarding the philosophical implications of your query. The multifaceted nature of this topic requires careful intellectual consideration and analytical prowess."
        },
        {
            "character": "Brian",
            "good_response": "Well, actually, that's a fascinating question that touches on some deeper philosophical issues. You see, the intersection of canine psychology and human intellectual discourse creates a rather unique paradigm...",
            "bad_response": "Hehehehehe! That's totally awesome, dude! Bird bird bird, bird is the word! This is worse than that time I tried to be smart but couldn't stop laughing!"
        }
    ]
    
    print("ℹ️  These examples show what good vs bad character responses look like:")
    print("   The LLM auto-assessment would rate these and provide detailed feedback")
    
    for example in test_responses:
        print(f"\n🎭 {example['character']} Examples:")
        print(f"   ✅ Good: '{example['good_response'][:80]}...'")
        print(f"   ❌ Bad:  '{example['bad_response'][:80]}...'")

def test_quality_control_system():
    """Test the quality control system that ensures responses meet quality standards."""
    
    print("\n🛡️  Testing Quality Control System")
    print("=" * 40)
    
    # Test 1: Check quality control status
    print("📊 1. Checking quality control status...")
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/quality_control_status")
        if response.status_code == 200:
            status = response.json()
            config = status["configuration"]
            print(f"✅ Quality Control Status:")
            print(f"   🔧 Enabled: {config['enabled']}")
            print(f"   📏 Min Rating Threshold: {config['min_rating_threshold']}/5")
            print(f"   🔄 Max Retries: {config['max_retries']}")
            
            if isinstance(status["statistics"], dict):
                print(f"   📈 Statistics:")
                for char, stats in status["statistics"].items():
                    success_rate = stats.get("success_rate", 0) * 100
                    print(f"      🎭 {char}: {stats['quality_control_accepted']} accepted, {stats['quality_control_rejected']} rejected ({success_rate:.1f}% success)")
        else:
            print(f"❌ Error getting quality control status: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Demonstrate quality control configuration
    print("\n🔧 2. Testing quality control configuration...")
    try:
        # Temporarily lower threshold to demonstrate quality control in action
        config_update = {
            "enabled": True,
            "min_rating_threshold": 4.0,  # Higher threshold to trigger more retries
            "max_retries": 2
        }
        
        response = requests.post(
            f"{ORCHESTRATOR_URL}/quality_control_config",
            json=config_update,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Updated quality control config:")
            for setting, value in result["updated_settings"].items():
                print(f"   🔧 {setting}: {value}")
        else:
            print(f"❌ Error updating config: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Reset to reasonable defaults
    print("\n🔄 3. Resetting to recommended defaults...")
    try:
        default_config = {
            "enabled": True,
            "min_rating_threshold": 3.0,  # Reasonable threshold
            "max_retries": 3
        }
        
        response = requests.post(
            f"{ORCHESTRATOR_URL}/quality_control_config",
            json=default_config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print(f"✅ Reset to recommended defaults")
        else:
            print(f"❌ Error resetting config: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Show how it works
    print("\n🎯 4. How Quality Control Works:")
    print("   1️⃣ Bot generates response using character LLM")
    print("   2️⃣ Quality Control LLM evaluates response (1-5 rating)")
    print("   3️⃣ If rating >= threshold: Accept and send to Discord")
    print("   4️⃣ If rating < threshold: Generate new response and retry")
    print("   5️⃣ Repeat until good response or max retries reached")
    print("   6️⃣ All assessments (accepted/rejected) are recorded for learning")
    
    print("\n📝 Example Quality Control Log:")
    print("   🔍 Quality Control: Generating Peter response with quality assurance...")
    print("   🎭 Attempt 1/3: Generating Peter response...")
    print("   🤖 Quality Control: Assessing response quality...")
    print("   📊 Quality Assessment: 2.5/5")
    print("   ❌ Quality Control: Response below threshold (2.5 < 3.0)")
    print("   🔄 Retrying to improve quality...")
    print("   🎭 Attempt 2/3: Generating Peter response...")
    print("   🤖 Quality Control: Assessing response quality...")
    print("   📊 Quality Assessment: 4.2/5")
    print("   ✅ Quality Control: Response meets threshold (4.2 >= 3.0)")

if __name__ == "__main__":
    test_fine_tuning_system()
    demo_llm_assessment()
    test_quality_control_system() 