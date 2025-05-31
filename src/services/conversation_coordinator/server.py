from flask import Flask, request, jsonify
import logging
import json
import random
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import hashlib
from collections import defaultdict, deque
import re
import os
import requests
import traceback
from dotenv import load_dotenv

# Import retry manager for standardized quality control retries
from utils.retry_manager import retry_sync, RetryConfig

# Load environment variables
load_dotenv()

# Service URLs
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://llm-service:6001")
CHARACTER_CONFIG_URL = os.getenv("CHARACTER_CONFIG_API_URL", "http://character-config:6006")
QUALITY_CONTROL_URL = os.getenv("QUALITY_CONTROL_URL", "http://quality-control:6003")
FINE_TUNING_URL = os.getenv("FINE_TUNING_URL", "http://fine-tuning:6004")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationCoordinator:
    def __init__(self):
        self.character_personalities = {
            'peter': {
                'response_probability': 0.4,
                'interruption_tendency': 0.7,
                'topic_interests': ['food', 'tv', 'work', 'family', 'beer', 'friends'],
                'speaking_style': 'energetic',
                'conflict_style': 'direct',
                'humor_level': 0.8,
                'intelligence_level': 0.3,
                'attention_span': 'short'
            },
            'brian': {
                'response_probability': 0.3,
                'interruption_tendency': 0.4,
                'topic_interests': ['politics', 'literature', 'philosophy', 'culture', 'writing'],
                'speaking_style': 'intellectual',
                'conflict_style': 'analytical',
                'humor_level': 0.6,
                'intelligence_level': 0.9,
                'attention_span': 'long'
            },
            'stewie': {
                'response_probability': 0.3,
                'interruption_tendency': 0.8,
                'topic_interests': ['science', 'plans', 'superiority', 'technology', 'control'],
                'speaking_style': 'sophisticated',
                'conflict_style': 'condescending',
                'humor_level': 0.7,
                'intelligence_level': 1.0,
                'attention_span': 'medium'
            }
        }
        
        # Conversation flow tracking
        self.conversation_history = defaultdict(lambda: deque(maxlen=50))
        self.character_last_spoke = defaultdict(lambda: None)
        self.conversation_topics = defaultdict(list)
        self.character_interactions = defaultdict(lambda: defaultdict(int))
        
        # Organic conversation rules
        self.flow_rules = {
            'max_consecutive_turns': 3,
            'topic_change_threshold': 5,
            'interruption_cooldown': 2,
            'character_rotation_weight': 0.3,
            'topic_relevance_weight': 0.4,
            'personality_weight': 0.3
        }

    def select_responding_character(self, message: str, conversation_id: str, 
                                   available_characters: List[str] = None,
                                   force_character: str = None) -> Dict:
        """Select which character should respond based on conversation context"""
        
        if force_character:
            return self._create_selection_result(force_character, 1.0, 
                                                "Forced character selection", conversation_id)
        
        if available_characters is None:
            available_characters = list(self.character_personalities.keys())
        
        # Analyze message for topic and context
        message_analysis = self._analyze_message(message)
        conversation_context = self._get_conversation_context(conversation_id)
        
        # Calculate selection scores for each character
        character_scores = {}
        for character in available_characters:
            score = self._calculate_character_score(
                character, message_analysis, conversation_context, conversation_id
            )
            character_scores[character] = score
        
        # Select character with highest score (with some randomization)
        selected_character = self._weighted_character_selection(character_scores)
        selection_confidence = character_scores[selected_character]
        
        # Update conversation tracking
        self._update_conversation_tracking(conversation_id, selected_character, message_analysis)
        
        reasoning = self._generate_selection_reasoning(
            selected_character, character_scores, message_analysis, conversation_context
        )
        
        return self._create_selection_result(
            selected_character, selection_confidence, reasoning, conversation_id, character_scores
        )

    def get_conversation_flow_analysis(self, conversation_id: str) -> Dict:
        """Get detailed analysis of conversation flow and patterns"""
        history = list(self.conversation_history[conversation_id])
        
        if not history:
            return {'error': 'No conversation history found'}
        
        # Character participation analysis
        character_participation = defaultdict(int)
        character_recent_activity = defaultdict(int)
        
        for i, entry in enumerate(history):
            character = entry.get('character')
            if character:
                character_participation[character] += 1
                # Weight recent messages more heavily
                if i >= len(history) - 10:
                    character_recent_activity[character] += 1
        
        # Topic analysis
        topics = self.conversation_topics[conversation_id]
        topic_distribution = defaultdict(int)
        for topic in topics[-20:]:  # Last 20 topics
            topic_distribution[topic] += 1
        
        # Conversation quality metrics
        avg_response_time = self._calculate_avg_response_time(history)
        topic_coherence = self._calculate_topic_coherence(topics)
        character_balance = self._calculate_character_balance(character_participation)
        
        return {
            'conversation_id': conversation_id,
            'total_messages': len(history),
            'character_participation': dict(character_participation),
            'character_recent_activity': dict(character_recent_activity),
            'topic_distribution': dict(topic_distribution),
            'conversation_quality': {
                'avg_response_time_seconds': avg_response_time,
                'topic_coherence_score': topic_coherence,
                'character_balance_score': character_balance
            },
            'last_speaker': history[-1].get('character') if history else None,
            'conversation_age_minutes': self._get_conversation_age(conversation_id)
        }

    def suggest_conversation_enhancement(self, conversation_id: str) -> Dict:
        """Suggest ways to enhance conversation flow and engagement"""
        analysis = self.get_conversation_flow_analysis(conversation_id)
        
        if 'error' in analysis:
            return analysis
        
        suggestions = []
        
        # Check character balance
        participation = analysis['character_participation']
        if participation:
            max_participation = max(participation.values())
            min_participation = min(participation.values())
            
            if max_participation > min_participation * 3:
                underrepresented = [char for char, count in participation.items() 
                                 if count == min_participation]
                suggestions.append({
                    'type': 'character_balance',
                    'priority': 'high',
                    'suggestion': f"Include {', '.join(underrepresented)} more in conversation",
                    'reason': 'Character participation is unbalanced'
                })
        
        # Check topic diversity
        topics = analysis['topic_distribution']
        if len(topics) < 3 and analysis['total_messages'] > 10:
            suggestions.append({
                'type': 'topic_diversity',
                'priority': 'medium',
                'suggestion': 'Introduce new topics to maintain engagement',
                'reason': 'Conversation topics lack diversity'
            })
        
        # Check conversation quality
        quality = analysis['conversation_quality']
        if quality['character_balance_score'] < 0.6:
            suggestions.append({
                'type': 'flow_improvement',
                'priority': 'medium',
                'suggestion': 'Encourage different characters to contribute',
                'reason': 'Conversation flow could be more balanced'
            })
        
        return {
            'conversation_id': conversation_id,
            'suggestions': suggestions,
            'overall_health': self._assess_conversation_health(analysis)
        }

    def _analyze_message(self, message: str) -> Dict:
        """Analyze message content for topic, sentiment, and context cues"""
        message_lower = message.lower()
        
        # Topic detection
        topic_keywords = {
            'food': ['eat', 'food', 'hungry', 'restaurant', 'cook', 'meal', 'dinner'],
            'family': ['family', 'wife', 'kid', 'child', 'parent', 'mom', 'dad'],
            'work': ['work', 'job', 'boss', 'office', 'money', 'career'],
            'politics': ['politics', 'government', 'president', 'election', 'vote'],
            'science': ['science', 'research', 'experiment', 'theory', 'technology'],
            'entertainment': ['tv', 'movie', 'show', 'watch', 'film', 'episode']
        }
        
        detected_topics = []
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_topics.append(topic)
        
        # Sentiment analysis (basic)
        positive_words = ['good', 'great', 'awesome', 'love', 'like', 'happy', 'fun']
        negative_words = ['bad', 'hate', 'stupid', 'awful', 'terrible', 'angry', 'mad']
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            sentiment = 'positive'
        elif negative_count > positive_count:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Question detection
        is_question = '?' in message or any(
            message_lower.startswith(q) for q in ['what', 'why', 'how', 'when', 'where', 'who']
        )
        
        return {
            'topics': detected_topics,
            'sentiment': sentiment,
            'is_question': is_question,
            'length': len(message),
            'urgency': self._detect_urgency(message_lower)
        }

    def _detect_urgency(self, message: str) -> str:
        """Detect message urgency level"""
        urgent_indicators = ['urgent', 'emergency', 'help', 'now', 'immediately']
        caps_ratio = sum(1 for c in message if c.isupper()) / max(len(message), 1)
        exclamation_count = message.count('!')
        
        if any(indicator in message for indicator in urgent_indicators) or caps_ratio > 0.3:
            return 'high'
        elif exclamation_count > 1:
            return 'medium'
        else:
            return 'low'

    def _get_conversation_context(self, conversation_id: str) -> Dict:
        """Get current conversation context and patterns"""
        history = list(self.conversation_history[conversation_id])
        
        if not history:
            return {'recent_characters': [], 'recent_topics': [], 'last_speaker': None, 'consecutive_turns': 0}
        
        # Recent character activity (last 5 messages)
        recent_characters = [entry.get('character') for entry in history[-5:] if entry.get('character')]
        
        # Recent topics
        recent_topics = self.conversation_topics[conversation_id][-5:] if self.conversation_topics[conversation_id] else []
        
        # Last speaker info
        last_speaker = recent_characters[-1] if recent_characters else None
        consecutive_turns = 0
        if last_speaker:
            for char in reversed(recent_characters):
                if char == last_speaker:
                    consecutive_turns += 1
                else:
                    break
        
        return {
            'recent_characters': recent_characters,
            'recent_topics': recent_topics,
            'last_speaker': last_speaker,
            'consecutive_turns': consecutive_turns
        }

    def _calculate_character_score(self, character: str, message_analysis: Dict, 
                                 conversation_context: Dict, conversation_id: str) -> float:
        """Calculate selection score for a character"""
        personality = self.character_personalities[character]
        score = personality['response_probability']
        
        # Topic relevance
        character_interests = personality['topic_interests']
        topic_relevance = 0
        for topic in message_analysis['topics']:
            if topic in character_interests:
                topic_relevance += 1
        topic_score = min(topic_relevance * 0.2, 0.6)
        
        # Character rotation (avoid same character speaking too much)
        last_speaker = conversation_context['last_speaker']
        consecutive_turns = conversation_context['consecutive_turns']
        
        rotation_penalty = 0
        if character == last_speaker:
            rotation_penalty = consecutive_turns * 0.2
        
        # Question handling (some characters are better at answering)
        question_bonus = 0
        if message_analysis['is_question']:
            if personality['intelligence_level'] > 0.7:
                question_bonus = 0.2
            elif personality['humor_level'] > 0.7:
                question_bonus = 0.1
        
        # Urgency handling
        urgency_modifier = 0
        if message_analysis['urgency'] == 'high':
            if personality['interruption_tendency'] > 0.6:
                urgency_modifier = 0.3
        
        # Calculate final score
        final_score = (
            score + 
            topic_score + 
            question_bonus + 
            urgency_modifier - 
            rotation_penalty
        )
        
        return max(0.0, min(1.0, final_score))

    def _weighted_character_selection(self, character_scores: Dict[str, float]) -> str:
        """Select character with weighted randomization"""
        if not character_scores:
            return 'peter'  # Default fallback
        
        # Add some randomization to prevent predictability
        adjusted_scores = {}
        for character, score in character_scores.items():
            randomization = random.uniform(0.9, 1.1)
            adjusted_scores[character] = score * randomization
        
        # Select character with highest adjusted score
        return max(adjusted_scores, key=adjusted_scores.get)

    def _update_conversation_tracking(self, conversation_id: str, character: str, message_analysis: Dict):
        """Update conversation tracking data"""
        timestamp = datetime.now()
        
        # Add to conversation history
        self.conversation_history[conversation_id].append({
            'character': character,
            'timestamp': timestamp,
            'topics': message_analysis['topics'],
            'sentiment': message_analysis['sentiment']
        })
        
        # Update character last spoke
        self.character_last_spoke[conversation_id] = character
        
        # Update topics
        for topic in message_analysis['topics']:
            self.conversation_topics[conversation_id].append(topic)

    def _generate_selection_reasoning(self, selected_character: str, all_scores: Dict,
                                    message_analysis: Dict, conversation_context: Dict) -> str:
        """Generate human-readable reasoning for character selection"""
        reasons = []
        
        # Primary reason (highest scoring factor)
        personality = self.character_personalities[selected_character]
        
        if message_analysis['topics']:
            matching_interests = set(message_analysis['topics']) & set(personality['topic_interests'])
            if matching_interests:
                reasons.append(f"Interested in {', '.join(matching_interests)}")
        
        if message_analysis['is_question'] and personality['intelligence_level'] > 0.7:
            reasons.append("Good at answering questions")
        
        if conversation_context['consecutive_turns'] > 2 and selected_character != conversation_context['last_speaker']:
            reasons.append("Conversation flow rotation")
        
        if personality['interruption_tendency'] > 0.6 and message_analysis['urgency'] == 'high':
            reasons.append("Likely to interrupt for urgent matters")
        
        if not reasons:
            reasons.append("Natural personality fit")
        
        return f"{selected_character.title()} selected: {', '.join(reasons)}"

    def _create_selection_result(self, character: str, confidence: float, reasoning: str,
                               conversation_id: str, all_scores: Dict = None) -> Dict:
        """Create standardized selection result"""
        return {
            'selected_character': character,
            'confidence': round(confidence, 3),
            'reasoning': reasoning,
            'conversation_id': conversation_id,
            'timestamp': datetime.now().isoformat(),
            'all_character_scores': {k: round(v, 3) for k, v in (all_scores or {}).items()},
            'metadata': {
                'selection_method': 'intelligent_coordination',
                'version': '1.0.0'
            }
        }

    def _calculate_avg_response_time(self, history: List[Dict]) -> float:
        """Calculate average response time (placeholder - would need real timestamps)"""
        return 2.5  # Placeholder value

    def _calculate_topic_coherence(self, topics: List[str]) -> float:
        """Calculate how coherent topic flow is"""
        if len(topics) < 2:
            return 1.0
        
        # Simple coherence based on topic transitions
        coherent_transitions = 0
        for i in range(1, len(topics)):
            if topics[i] == topics[i-1]:  # Same topic
                coherent_transitions += 1
            elif self._topics_related(topics[i], topics[i-1]):  # Related topics
                coherent_transitions += 0.5
        
        return coherent_transitions / (len(topics) - 1)

    def _topics_related(self, topic1: str, topic2: str) -> bool:
        """Check if two topics are related"""
        related_groups = [
            {'food', 'family', 'work'},
            {'politics', 'science', 'technology'},
            {'entertainment', 'family'}
        ]
        
        for group in related_groups:
            if topic1 in group and topic2 in group:
                return True
        return False

    def _calculate_character_balance(self, participation: Dict[str, int]) -> float:
        """Calculate how balanced character participation is"""
        if not participation:
            return 1.0
        
        values = list(participation.values())
        avg_participation = sum(values) / len(values)
        variance = sum((v - avg_participation) ** 2 for v in values) / len(values)
        
        # Lower variance = better balance
        return max(0.0, 1.0 - (variance / avg_participation))

    def _get_conversation_age(self, conversation_id: str) -> float:
        """Get conversation age in minutes"""
        history = self.conversation_history[conversation_id]
        if not history:
            return 0.0
        
        first_message = history[0]
        if 'timestamp' in first_message:
            age = datetime.now() - first_message['timestamp']
            return age.total_seconds() / 60
        return 0.0

    def _assess_conversation_health(self, analysis: Dict) -> str:
        """Assess overall conversation health"""
        quality = analysis['conversation_quality']
        
        health_score = (
            quality['topic_coherence_score'] * 0.4 +
            quality['character_balance_score'] * 0.6
        )
        
        if health_score >= 0.8:
            return 'excellent'
        elif health_score >= 0.6:
            return 'good'
        elif health_score >= 0.4:
            return 'fair'
        else:
            return 'poor'

    def analyze_organic_conversation_opportunity(self, 
                                           current_message: str, 
                                           current_character: str,
                                           conversation_id: str,
                                           available_characters: List[str] = None) -> Dict:
        """Use LLM to intelligently analyze if an organic follow-up is appropriate and who should respond."""
        
        if available_characters is None:
            available_characters = [char for char in self.character_personalities.keys() 
                                  if char != current_character.lower()]
        
        try:
            # Get conversation context
            context = self._get_conversation_context(conversation_id)
            recent_history = list(self.conversation_history[conversation_id])[-5:]  # Last 5 messages
            
            # Build analysis prompt for the LLM
            analysis_prompt = self._build_organic_analysis_prompt(
                current_message, current_character, available_characters, recent_history, context
            )
            
            # Call LLM service for analysis
            response = requests.post(
                f"{LLM_SERVICE_URL}/generate",
                json={
                    "prompt": analysis_prompt,
                    "settings": {
                        "temperature": 0.3,  # Lower temperature for more consistent analysis
                        "max_tokens": 300
                    }
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if "response" in data:
                    return self._parse_organic_analysis_response(
                        data["response"], current_character, available_characters, conversation_id
                    )
            
            # Fallback to rule-based logic if LLM fails
            logger.warning(f"LLM analysis failed, falling back to rule-based logic")
            return self._fallback_organic_analysis(current_message, current_character, available_characters)
            
        except Exception as e:
            logger.error(f"Error in organic conversation analysis: {e}")
            return self._fallback_organic_analysis(current_message, current_character, available_characters)

    def _build_organic_analysis_prompt(self, current_message: str, current_character: str, 
                                     available_characters: List[str], recent_history: List[Dict], 
                                     context: Dict) -> str:
        """Build the prompt for LLM organic conversation analysis."""
        
        # Character personalities for context
        char_descriptions = {
            'peter': "Peter Griffin - impulsive, childish, loves food/TV/beer, interrupts a lot, makes random observations",
            'brian': "Brian Griffin - intellectual dog, pretentious, likes culture/politics, often corrects others",
            'stewie': "Stewie Griffin - evil genius baby, condescending, sophisticated vocabulary, dramatic reactions"
        }
        
        # Build conversation history context
        history_context = ""
        if recent_history:
            history_context = "\n".join([
                f"{msg.get('character', 'unknown')}: {msg.get('content', '')}" 
                for msg in recent_history[-3:] if msg.get('content')
            ])
        
        available_chars_desc = "\n".join([
            f"- {char}: {char_descriptions.get(char, 'Unknown character')}"
            for char in available_characters
        ])
        
        prompt = f"""Analyze this Family Guy conversation to determine if an organic follow-up response is appropriate.

CURRENT MESSAGE:
{current_character}: "{current_message}"

RECENT CONVERSATION HISTORY:
{history_context if history_context else "No recent history"}

AVAILABLE CHARACTERS FOR FOLLOW-UP:
{available_chars_desc}

ANALYSIS CRITERIA:
1. Would any of these characters naturally want to respond to what {current_character} just said?
2. Does the message contain topics, opinions, or statements that would trigger reactions?
3. Is the conversation at a natural pause, or would a follow-up feel forced?
4. Which character would be most likely to respond based on their personality and the content?

Provide your analysis in this EXACT format:
SHOULD_RESPOND: [yes/no]
BEST_CHARACTER: [character_name or none]
CONFIDENCE: [0.0-1.0]
REASON: [brief explanation of why this character would respond or why no response is needed]

Focus on natural conversation flow. Not every message needs a follow-up."""

        return prompt

    def _parse_organic_analysis_response(self, llm_response: str, current_character: str, 
                                       available_characters: List[str], conversation_id: str) -> Dict:
        """Parse the LLM's organic conversation analysis response."""
        try:
            # Extract structured data from response
            should_respond = False
            best_character = None
            confidence = 0.0
            reason = "LLM analysis failed to parse"
            
            lines = llm_response.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('SHOULD_RESPOND:'):
                    should_respond = 'yes' in line.lower()
                elif line.startswith('BEST_CHARACTER:'):
                    char = line.split(':', 1)[1].strip().lower()
                    if char in available_characters and char != 'none':
                        best_character = char
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.split(':', 1)[1].strip())
                    except (ValueError, IndexError):
                        confidence = 0.5
                elif line.startswith('REASON:'):
                    reason = line.split(':', 1)[1].strip()
            
            # Update conversation tracking if we're proceeding
            if should_respond and best_character:
                self._update_conversation_tracking(conversation_id, best_character, 
                                                 {'topics': ['organic_followup'], 'sentiment': 'neutral'})
            
            return {
                'should_respond': should_respond,
                'selected_character': best_character,
                'confidence': confidence,
                'reasoning': reason,
                'analysis_type': 'llm_intelligent',
                'fallback_used': False,
                'conversation_id': conversation_id,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing LLM organic analysis: {e}")
            return self._fallback_organic_analysis(llm_response, current_character, available_characters)

    def _fallback_organic_analysis(self, current_message: str, current_character: str, 
                                  available_characters: List[str]) -> Dict:
        """Fallback rule-based organic conversation analysis."""
        
        # Simple keyword-based analysis
        message_lower = current_message.lower()
        
        # Topics that typically get responses
        response_triggers = {
            'peter': ['food', 'beer', 'tv', 'work', 'holy crap', 'freakin', 'chicken'],
            'brian': ['smart', 'book', 'political', 'actually', 'intellectual', 'wine', 'martini'],
            'stewie': ['genius', 'plan', 'stupid', 'inferior', 'invention', 'world domination']
        }
        
        # Score each character's likelihood to respond
        character_scores = {}
        for char in available_characters:
            score = 0.0
            
            # Check if message contains their trigger words
            triggers = response_triggers.get(char, [])
            for trigger in triggers:
                if trigger in message_lower:
                    score += 0.3
            
            # Check personality-based response probability
            char_personality = self.character_personalities.get(char, {})
            base_prob = char_personality.get('response_probability', 0.3)
            interruption = char_personality.get('interruption_tendency', 0.5)
            
            score += (base_prob * 0.4) + (interruption * 0.3)
            
            character_scores[char] = min(score, 1.0)
        
        # Select best character if any have decent scores
        best_character = None
        best_score = 0.0
        
        for char, score in character_scores.items():
            if score > best_score and score > 0.4:  # Threshold for response
                best_character = char
                best_score = score
        
        should_respond = best_character is not None and best_score > 0.4
        
        return {
            'should_respond': should_respond,
            'selected_character': best_character,
            'confidence': best_score,
            'reasoning': f"Rule-based analysis: {best_character} scored {best_score:.2f}" if best_character else "No character met response threshold",
            'analysis_type': 'rule_based_fallback',
            'fallback_used': True,
            'character_scores': character_scores,
            'timestamp': datetime.now().isoformat()
        }

    def analyze_conversation_continuation(self, conversation_history: List[Dict[str, Any]], 
                                        responding_character: str, response_text: str, 
                                        channel_id: str) -> Dict[str, Any]:
        """
        Use LLM to intelligently determine if the conversation should continue or end naturally.
        Returns: {"continue": bool, "reason": str, "suggested_character": str}
        """
        try:
            # Get recent conversation context (last 10 messages)
            recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            # Format conversation for analysis
            conversation_context = ""
            for msg in recent_messages:
                character = msg.get("character", "user")
                content = msg.get("content", "")
                if character == "user":
                    conversation_context += f"User: {content}\n"
                else:
                    conversation_context += f"{character.title()}: {content}\n"
            
            # Add the current response
            conversation_context += f"{responding_character.title()}: {response_text}\n"
            
            # Available characters (exclude the one who just responded)
            all_characters = ["peter", "brian", "stewie"]
            available_characters = [char for char in all_characters if char != responding_character.lower()]
            
            # Create analysis prompt
            analysis_prompt = f"""
Analyze this Family Guy conversation to determine if it should continue organically.

CONVERSATION:
{conversation_context}

ANALYSIS CRITERIA (BE PERMISSIVE - Family Guy conversations are naturally chaotic and ongoing):
- Does the conversation have natural momentum? (favor YES unless clearly ended)
- Would other characters naturally react to what was just said?
- Is there comedic potential for more back-and-forth?
- Are characters likely to have opinions on this topic?
- Has the conversation truly reached a definitive conclusion?

BIAS TOWARD CONTINUATION: Only say NO if the conversation has CLEARLY ended (like "goodbye", "end of discussion", or everyone has thoroughly exhausted the topic).

CHARACTERS AVAILABLE: {', '.join([char.title() for char in available_characters])} (excluding {responding_character.title()})

DECISION: Should another character organically join this conversation?

Respond with EXACTLY this format:
CONTINUE: [YES/NO]
REASON: [Brief explanation - be generous with YES decisions]
CHARACTER: [If YES, suggest which character might naturally respond, or NONE if NO]

Examples of when to CONTINUE YES:
- Someone made a controversial statement
- A topic was mentioned that others would have opinions on
- There's comedic potential for reactions
- Characters would naturally banter about this
- The conversation feels like it has momentum

Examples of when to CONTINUE NO:
- Someone explicitly ended the conversation ("I'm done", "whatever", "goodbye")
- The topic has been completely exhausted with multiple back-and-forth exchanges
- Characters have clearly moved on to other activities
"""

            # Get LLM analysis
            response = requests.post(
                f"{LLM_SERVICE_URL}/generate",
                json={
                    "prompt": analysis_prompt,
                    "user_message": response_text,
                    "chat_history": recent_messages,
                    "settings": {
                        "temperature": 0.3,  # Lower temperature for more consistent analysis
                        "max_tokens": 200
                    }
                },
                timeout=15
            )
            
            if response.status_code != 200:
                logger.warning(f"LLM request failed with status {response.status_code}")
                return {"continue": False, "reason": "LLM analysis failed", "suggested_character": None}
            
            analysis_text = response.json().get("response", "").strip()
            logger.info(f"🧠 Conversation Analysis: {analysis_text}")
            
            # Parse the response with fallback to continue if unclear
            continue_decision = True  # Default to continue (more permissive)
            reason = "Default: favoring conversation continuation"
            suggested_character = None
            
            lines = analysis_text.split('\n')
            continue_found = False
            
            for line in lines:
                line = line.strip()
                if line.startswith("CONTINUE:"):
                    continue_found = True
                    # Only set to False if explicitly NO, otherwise default to True
                    continue_decision = "NO" not in line.upper()
                elif line.startswith("REASON:"):
                    reason = line.replace("REASON:", "").strip()
                elif line.startswith("CHARACTER:"):
                    char_text = line.replace("CHARACTER:", "").strip().lower()
                    if char_text != "none" and char_text in available_characters:
                        suggested_character = char_text
            
            # If we didn't find a clear CONTINUE directive, default to True
            if not continue_found:
                continue_decision = True
                reason = "No clear directive found, defaulting to continue conversation"
                logger.info(f"⚠️ No CONTINUE directive found in LLM response, defaulting to continue")
            
            # If continuing but no character suggested, pick a random available one
            if continue_decision and not suggested_character and available_characters:
                suggested_character = random.choice(available_characters)
                logger.info(f"🎲 No character suggested, randomly selected: {suggested_character}")
            
            logger.info(f"📊 Conversation Decision: CONTINUE={continue_decision}, CHARACTER={suggested_character}, REASON={reason}")
            
            return {
                "continue": continue_decision,
                "reason": reason,
                "suggested_character": suggested_character,
                "analysis_type": "llm_intelligent",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in conversation continuation analysis: {e}")
            return {"continue": False, "reason": f"Analysis error: {str(e)}", "suggested_character": None}

    def generate_organic_response(self, responding_character: str, previous_speaker: str, 
                                previous_message: str, original_input: str, 
                                conversation_history: List[Dict[str, Any]], channel_id: str) -> Optional[str]:
        """Generate a proper organic response with context and quality validation."""
        
        def generate_response_with_quality_control() -> Optional[str]:
            """Enhanced single attempt with fine-tuning integration and quality feedback loop."""
            failed_attempts = []  # Track failed attempts for fine-tuning
            
            try:
                # Step 1: Get base character configuration
                response = requests.get(f"{CHARACTER_CONFIG_URL}/llm_prompt/{responding_character}", timeout=10)
                if response.status_code != 200:
                    logger.error(f"Failed to get character config: {response.status_code}")
                    return None
                
                character_config = response.json()
                base_prompt = character_config.get("llm_prompt", f"You are {responding_character} from Family Guy.")
                
                # Step 2: Get optimized prompt from fine-tuning service with retry context
                optimized_prompt = base_prompt
                fine_tuning_context = {
                    "topic": "organic_follow_up",
                    "conversation_context": {
                        "previous_speaker": previous_speaker,
                        "previous_message": previous_message,
                        "recent_topics": [],
                        "last_speaker": previous_speaker,
                        "failed_attempts": failed_attempts  # Include failed attempts for learning
                    },
                    "retry_optimization": True  # Flag to indicate this is for retry optimization
                }
                
                try:
                    fine_tuning_response = requests.post(
                        f"{FINE_TUNING_URL}/optimize-prompt",
                        json={
                            "character": responding_character,
                            "context": fine_tuning_context
                        },
                        timeout=10
                    )
                    
                    if fine_tuning_response.status_code == 200:
                        ft_data = fine_tuning_response.json()
                        if "optimized_prompt" in ft_data:
                            optimized_prompt = ft_data["optimized_prompt"]
                            logger.info(f"🔧 Using fine-tuned prompt for {responding_character} organic response")
                        else:
                            logger.warning(f"⚠️ Fine-tuning response missing optimized_prompt")
                    else:
                        logger.warning(f"⚠️ Fine-tuning service unavailable: {fine_tuning_response.status_code}")
                except Exception as e:
                    logger.warning(f"⚠️ Fine-tuning service error: {e}")
                
                # Step 3: Generate response with LLM service
                conversation_context = "\n".join([
                    f"{msg.get('character', 'unknown')}: {msg.get('content', '')}" 
                    for msg in conversation_history[-3:] if msg.get('content')
                ])
                
                organic_input = f"""ORGANIC FOLLOW-UP OPPORTUNITY:
Previous Speaker: {previous_speaker}
Previous Message: "{previous_message}"
Recent Context: {conversation_context}

Generate a natural {responding_character} response that feels like a spontaneous interruption or follow-up."""
                
                llm_response = requests.post(
                    f"{LLM_SERVICE_URL}/generate",
                    json={
                        "prompt": optimized_prompt,
                        "user_message": organic_input,
                        "chat_history": conversation_history[-5:],  # Include recent history
                        "settings": character_config.get("llm_settings", {})
                    },
                    timeout=25
                )
                
                if llm_response.status_code != 200:
                    logger.error(f"LLM service error: {llm_response.status_code}")
                    return None
                
                generated_response = llm_response.json()["response"]
                
                # Step 4: Quality control validation
                quality_response = requests.post(
                    f"{QUALITY_CONTROL_URL}/analyze",
                    json={
                        "response": generated_response,
                        "character": responding_character,
                        "conversation_id": channel_id,
                        "context": previous_message,
                        "last_speaker": previous_speaker,
                        "message_type": "organic_response"  # Flag as organic for appropriate thresholds
                    },
                    timeout=15
                )
                
                if quality_response.status_code == 200:
                    quality_data = quality_response.json()
                    quality_passed = quality_data.get("quality_check_passed", True)
                    quality_score = quality_data.get("overall_score", 85)
                    
                    # Step 5: Record performance in fine-tuning service
                    response_id = f"organic_{channel_id}_{responding_character}_{int(datetime.now().timestamp())}"
                    
                    try:
                        # Always record performance data for learning (both pass and fail)
                        performance_metrics = {
                            "quality_score": quality_score,
                            "message_type": "organic_response",
                            "previous_speaker": previous_speaker,
                            "conversation_length": len(conversation_history),
                            "quality_passed": quality_passed,
                            "character_used": responding_character,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Record performance for learning
                        requests.post(
                            f"{FINE_TUNING_URL}/record-performance",
                            json={
                                "response_id": response_id,
                                "character": responding_character,
                                "metrics": performance_metrics,
                                "user_feedback": "quality_pass" if quality_passed else "quality_fail"
                            },
                            timeout=5  # Non-blocking
                        )
                        
                        if quality_passed:
                            logger.info(f"✅ Organic response quality: {quality_score} - PASSED")
                            return generated_response
                        else:
                            # Record failure for fine-tuning improvement
                            failed_attempts.append({
                                "response": generated_response,
                                "quality_score": quality_score,
                                "issues": quality_data.get("conversation_flow", {}).get("issues", []),
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            logger.warning(f"❌ Organic response quality: {quality_score} - FAILED")
                            
                            # Send failure feedback to fine-tuning for learning
                            requests.post(
                                f"{FINE_TUNING_URL}/record-performance",
                                json={
                                    "response_id": f"{response_id}_failed",
                                    "character": responding_character,
                                    "metrics": {**performance_metrics, "failure_reason": "quality_control"},
                                    "user_feedback": "quality_control_rejection",
                                    "failed_response_text": generated_response,
                                    "quality_issues": quality_data.get("conversation_flow", {}).get("issues", [])
                                },
                                timeout=5
                            )
                            return None
                    
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to record performance: {e}")
                        # Still return the response if quality passed, even if recording failed
                        if quality_passed:
                            return generated_response
                        return None
                
                else:
                    logger.error(f"Quality control service error: {quality_response.status_code}")
                    # Without quality control, we can't be sure of quality, so return None
                    return None
                
            except Exception as e:
                logger.error(f"Error in organic response generation: {e}")
                return None
        
        # Use the retry manager for the entire quality-controlled generation process
        try:
            return retry_sync(
                operation=generate_response_with_quality_control,
                service_name="Conversation Coordinator Organic",
                **RetryConfig.DISCORD_MESSAGE  # Use 10 attempts with exponential backoff
            )
        except Exception as e:
            logger.error(f"All organic response generation attempts failed: {e}")
            return None

    def handle_organic_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle organic conversation notification - the main entry point for intelligent conversation flow.
        This replaces the logic that was previously in the message router.
        """
        try:
            event_type = notification_data.get("event_type")
            if event_type != "direct_response_sent":
                return {
                    "success": False,
                    "error": f"Unsupported event type: {event_type}"
                }
            
            responding_character = notification_data.get("responding_character")
            response_text = notification_data.get("response_text")
            original_input = notification_data.get("original_input")
            channel_id = notification_data.get("channel_id")
            conversation_history = notification_data.get("conversation_history", [])
            
            if not all([responding_character, response_text, channel_id]):
                return {
                    "success": False,
                    "error": "Missing required fields: responding_character, response_text, channel_id"
                }
            
            logger.info(f"🔔 Conversation Coordinator: Received organic notification from {responding_character} in channel {channel_id}")
            
            # Analyze if conversation should continue using LLM intelligence
            conversation_analysis = self.analyze_conversation_continuation(
                conversation_history=conversation_history,
                responding_character=responding_character,
                response_text=response_text,
                channel_id=channel_id
            )
            
            if not conversation_analysis["continue"]:
                logger.info(f"🌱 Ending conversation naturally - {conversation_analysis['reason']}")
                return {
                    "success": True,
                    "action": "conversation_ended",
                    "reason": conversation_analysis["reason"]
                }
            
            logger.info(f"🌱 Conversation should continue - {conversation_analysis['reason']}")
            
            # Use suggested character from analysis
            suggested_character = conversation_analysis.get("suggested_character")
            
            if not suggested_character:
                # Fall back to our existing organic analysis if no character suggested
                all_characters = ["peter", "brian", "stewie"]
                available_characters = [char for char in all_characters if char != responding_character.lower()]
                
                organic_analysis = self.analyze_organic_conversation_opportunity(
                    current_message=response_text,
                    current_character=responding_character,
                    conversation_id=channel_id,
                    available_characters=available_characters
                )
                
                if not organic_analysis.get("should_respond"):
                    logger.info(f"🌱 No character selected for organic follow-up")
                    return {
                        "success": True,
                        "action": "no_followup",
                        "reason": organic_analysis.get("reasoning", "No suitable character found")
                    }
                
                suggested_character = organic_analysis.get("selected_character")
            
            if not suggested_character:
                return {
                    "success": True,
                    "action": "no_followup",
                    "reason": "No suitable character identified for organic response"
                }
            
            # Generate organic response with full context
            organic_response = self.generate_organic_response(
                responding_character=suggested_character,
                previous_speaker=responding_character,
                previous_message=response_text,
                original_input=original_input or response_text,
                conversation_history=conversation_history,
                channel_id=channel_id
            )
            
            if not organic_response:
                return {
                    "success": False,
                    "error": f"Failed to generate organic response for {suggested_character}"
                }
            
            # Return the generated response for the message router to send
            return {
                "success": True,
                "action": "organic_response_generated",
                "character": suggested_character,
                "response": organic_response,
                "reasoning": conversation_analysis["reason"],
                "confidence": conversation_analysis.get("confidence", 0.8)
            }
            
        except Exception as e:
            logger.error(f"Error in organic notification handler: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Initialize service
coordinator = ConversationCoordinator()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'conversation-coordinator',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/select-character', methods=['POST'])
def select_character():
    """Select which character should respond"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Missing message field'}), 400
        
        message = data['message']
        conversation_id = data.get('conversation_id', 'default')
        available_characters = data.get('available_characters')
        force_character = data.get('force_character')
        
        result = coordinator.select_responding_character(
            message, conversation_id, available_characters, force_character
        )
        
        logger.info(f"Character selected for conversation {conversation_id}: {result['selected_character']}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error selecting character: {str(e)}")
        return jsonify({'error': f'Character selection failed: {str(e)}'}), 500

@app.route('/conversation-analysis', methods=['GET'])
def conversation_analysis():
    """Get conversation flow analysis"""
    try:
        conversation_id = request.args.get('conversation_id', 'default')
        analysis = coordinator.get_conversation_flow_analysis(conversation_id)
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error analyzing conversation: {str(e)}")
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/conversation-suggestions', methods=['GET'])
def conversation_suggestions():
    """Get suggestions for improving conversation flow"""
    try:
        conversation_id = request.args.get('conversation_id', 'default')
        suggestions = coordinator.suggest_conversation_enhancement(conversation_id)
        return jsonify(suggestions)
        
    except Exception as e:
        logger.error(f"Error generating suggestions: {str(e)}")
        return jsonify({'error': f'Suggestion generation failed: {str(e)}'}), 500

@app.route('/conversation-reset', methods=['POST'])
def reset_conversation():
    """Reset conversation tracking for a specific conversation"""
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id', 'default')
        
        # Clear conversation data
        if conversation_id in coordinator.conversation_history:
            del coordinator.conversation_history[conversation_id]
        if conversation_id in coordinator.character_last_spoke:
            del coordinator.character_last_spoke[conversation_id]
        if conversation_id in coordinator.conversation_topics:
            del coordinator.conversation_topics[conversation_id]
        
        return jsonify({
            'message': f'Conversation {conversation_id} reset successfully',
            'conversation_id': conversation_id
        })
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        return jsonify({'error': f'Reset failed: {str(e)}'}), 500

@app.route('/character-config', methods=['GET'])
def get_character_config():
    """Get character personality configuration"""
    return jsonify({
        'characters': coordinator.character_personalities,
        'flow_rules': coordinator.flow_rules
    })

@app.route('/analyze-organic-opportunity', methods=['POST'])
def analyze_organic_opportunity():
    """Analyze if an organic follow-up conversation is appropriate using LLM intelligence."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Required fields
        current_message = data.get('current_message', '').strip()
        current_character = data.get('current_character', '').strip()
        conversation_id = data.get('conversation_id', 'default')
        
        if not current_message or not current_character:
            return jsonify({
                'error': 'Missing required fields: current_message, current_character'
            }), 400
        
        # Optional fields
        available_characters = data.get('available_characters', None)
        
        # Perform intelligent analysis
        analysis_result = coordinator.analyze_organic_conversation_opportunity(
            current_message=current_message,
            current_character=current_character,
            conversation_id=conversation_id,
            available_characters=available_characters
        )
        
        return jsonify({
            'success': True,
            'analysis': analysis_result
        }), 200
        
    except Exception as e:
        logger.error(f"Error in organic opportunity analysis: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/analyze-conversation-continuation', methods=['POST'])
def analyze_conversation_continuation():
    """Analyze if a conversation should continue or end naturally using LLM intelligence."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Required fields
        conversation_history = data.get('conversation_history', [])
        responding_character = data.get('responding_character', '').strip()
        response_text = data.get('response_text', '').strip()
        channel_id = data.get('channel_id', 'default')
        
        if not conversation_history or not responding_character or not response_text or not channel_id:
            return jsonify({
                'error': 'Missing required fields: conversation_history, responding_character, response_text, channel_id'
            }), 400
        
        # Perform intelligent analysis
        analysis_result = coordinator.analyze_conversation_continuation(
            conversation_history=conversation_history,
            responding_character=responding_character,
            response_text=response_text,
            channel_id=channel_id
        )
        
        return jsonify({
            'success': True,
            'analysis': analysis_result
        }), 200
        
    except Exception as e:
        logger.error(f"Error in conversation continuation analysis: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/generate-organic-response', methods=['POST'])
def generate_organic_response():
    """Generate a proper organic response with context using LLM intelligence."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Required fields
        responding_character = data.get('responding_character', '').strip()
        previous_speaker = data.get('previous_speaker', '').strip()
        previous_message = data.get('previous_message', '').strip()
        original_input = data.get('original_input', '').strip()
        conversation_history = data.get('conversation_history', [])
        channel_id = data.get('channel_id', 'default')
        
        if not responding_character or not previous_speaker or not previous_message or not original_input or not channel_id:
            return jsonify({
                'error': 'Missing required fields: responding_character, previous_speaker, previous_message, original_input, channel_id'
            }), 400
        
        # Perform intelligent analysis
        organic_response = coordinator.generate_organic_response(
            responding_character=responding_character,
            previous_speaker=previous_speaker,
            previous_message=previous_message,
            original_input=original_input,
            conversation_history=conversation_history,
            channel_id=channel_id
        )
        
        if not organic_response:
            return jsonify({
                'error': 'Failed to generate organic response'
            }), 500
        
        return jsonify({
            'success': True,
            'response': organic_response
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating organic response: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/handle-organic-notification', methods=['POST'])
def handle_organic_notification():
    """Handle organic conversation notification using LLM intelligence."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Perform intelligent analysis
        analysis_result = coordinator.handle_organic_notification(data)
        
        return jsonify({
            'success': True,
            'analysis': analysis_result
        }), 200
        
    except Exception as e:
        logger.error(f"Error handling organic notification: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('CONVERSATION_COORDINATOR_PORT', 6002))
    app.run(host='0.0.0.0', port=port, debug=False) 