from flask import Flask, request, jsonify
import logging
import re
import json
import redis
from typing import Dict, List, Tuple, Optional
import asyncio
import aiohttp
from datetime import datetime, timedelta
import hashlib
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedQualityControlService:
    def __init__(self):
        # KeyDB connection for conversation history
        self.redis_client = self._initialize_redis()
        
        # Adaptive Quality Thresholds
        self.adaptive_thresholds = {
            'cold_start': float(os.getenv('COLD_START_THRESHOLD', '30.0')),
            'warm_conversation': float(os.getenv('WARM_CONVERSATION_THRESHOLD', '60.0')),
            'hot_conversation': float(os.getenv('HOT_CONVERSATION_THRESHOLD', '75.0'))
        }
        
        # Conversation state boundaries
        self.conversation_boundaries = {
            'cold_limit': int(os.getenv('CONVERSATION_HISTORY_COLD_LIMIT', '6')),
            'warm_limit': int(os.getenv('CONVERSATION_HISTORY_WARM_LIMIT', '20'))
        }
        
        # Character-aware anti-hallucination settings
        self.character_anti_hallucination = {
            'peter': {
                'length_multiplier': 0.7,  # Shorter responses
                'risk_multiplier': 1.2,    # Higher risk detection
                'strictness_multiplier': 1.3  # Stricter validation
            },
            'brian': {
                'length_multiplier': 1.3,  # Extended responses
                'risk_multiplier': 1.0,    # Standard risk
                'strictness_multiplier': 1.0  # Standard validation
            },
            'stewie': {
                'length_multiplier': 1.0,  # Standard length
                'risk_multiplier': 0.8,    # Lower risk tolerance
                'strictness_multiplier': 0.9  # More lenient
            }
        }
        
        # Enhanced character authenticity rules
        self.character_authenticity_rules = {
            'peter': {
                'required_elements': ['humor', 'reference', 'energy'],
                'forbidden_phrases': ['excuse me', 'pardon', 'i apologize', 'as an ai'],
                'personality_markers': ['nyehehe', 'oh my god', 'this is worse than', 'reminds me of', 'holy crap', 'awesome', 'sweet'],
                'speaking_style': 'casual',
                'intelligence_level': 'low',
                'conversation_style': 'reactive',
                'typical_reactions': ['holy crap!', 'really?', 'no way!', 'you\'re totally right!']
            },
            'brian': {
                'required_elements': ['intellect', 'sophistication', 'reference'],
                'forbidden_phrases': ['awesome', 'cool', 'rad', 'as an ai'],
                'personality_markers': ['well actually', 'it\'s interesting', 'you know', 'i read', 'fascinating', 'actually'],
                'speaking_style': 'formal',
                'intelligence_level': 'high',
                'conversation_style': 'analytical',
                'typical_reactions': ['actually...', 'well, that\'s...', 'i find that...', 'that reminds me of...']
            },
            'stewie': {
                'required_elements': ['superiority', 'complexity', 'condescension'],
                'forbidden_phrases': ['please', 'thank you', 'sorry', 'as an ai'],
                'personality_markers': ['blast', 'what the deuce', 'good lord', 'clearly', 'obviously', 'inferior'],
                'speaking_style': 'sophisticated',
                'intelligence_level': 'genius',
                'conversation_style': 'condescending',
                'typical_reactions': ['how fascinating...', 'what the deuce are you...', 'but i digress...', 'speaking of inferior minds...']
            }
        }
        
        # Conversation flow detection patterns
        self.conversation_indicators = [
            'you', 'your', 'yours', 'that', 'this', 'what you said', 'what you mean',
            'i agree', 'i disagree', 'speaking of', 'about what you', 'you\'re right',
            'you\'re wrong', 'like you said', 'as you mentioned', 'your point'
        ]
        
        self.monologue_indicators = [
            'also', 'furthermore', 'additionally', 'and another thing', 'by the way',
            'incidentally', 'speaking of which', 'on that note', 'while we\'re at it'
        ]
        
        self.self_continuation_patterns = [
            r'\b(also|and|furthermore|additionally|another thing)\b',
            r'\bby the way\b',
            r'\bincidentally\b',
            r'\bwhile (we\'re|were) at it\b',
            r'\boh yeah\b',
            r'\band you know what\b'
        ]
        
        # Topic transition patterns
        self.abrupt_topic_patterns = [
            r'\b(anyway|anyways|moving on|changing topics|different subject)\b',
            r'\b(oh|hey|so|well)\s+(?!(?:you|that|this|what))\w+'
        ]
        
        # Natural transition patterns  
        self.natural_transition_patterns = [
            r'\bthat reminds me\b',
            r'\bspeaking of\b',
            r'\bthat makes me think\b',
            r'\brelated to that\b',
            r'\bon that note\b'
        ]

    def _initialize_redis(self):
        """Initialize Redis/KeyDB connection"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://keydb:6379')
            if redis_url.startswith('redis://'):
                # Parse redis:// URL
                redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                # Fallback to host:port format
                host, port = redis_url.split(':')
                redis_client = redis.Redis(host=host, port=int(port), decode_responses=True)
            
            # Test connection
            redis_client.ping()
            logger.info("✅ Quality Control: Connected to KeyDB")
            return redis_client
        except Exception as e:
            logger.error(f"❌ Quality Control: Failed to connect to KeyDB: {e}")
            return None

    def analyze_response_quality_enhanced(self, response: str, character: str, 
                                        conversation_id: str = "default", 
                                        context: str = "", 
                                        last_speaker: str = None,
                                        message_type: str = "direct") -> Dict:
        """Enhanced comprehensive response quality analysis with adaptive thresholds and organic response support"""
        start_time = datetime.now()
        
        # Check if this is an organic response
        is_organic_response = (message_type == "organic_response")
        
        # Get conversation history for adaptive assessment
        conversation_history = self._get_conversation_history(conversation_id)
        
        # Calculate adaptive quality threshold (stricter for organic responses)
        adaptive_threshold = self._calculate_adaptive_quality_threshold(conversation_history, conversation_id)
        if is_organic_response:
            # Apply minimal threshold increase for organic responses (reduced from +5.0 to +2.0)
            adaptive_threshold = min(95.0, adaptive_threshold + 2.0)
            logger.info(f"🌱 Quality Control: Applying organic response threshold: {adaptive_threshold}")
        
        # Get character-aware anti-hallucination settings
        char_settings = self._get_character_anti_hallucination_settings(character)
        
        # Core quality metrics with character-aware adjustments
        authenticity_score = self._calculate_authenticity_score(response, character)
        hallucination_risk = self._detect_hallucination_risk_adaptive(response, context, char_settings)
        engagement_score = self._calculate_engagement_score(response, char_settings)
        toxicity_score = self._calculate_toxicity_score(response)
        
        # Enhanced conversation flow assessment for organic responses
        flow_assessment = self._assess_conversation_flow_quality(
            character, response, conversation_history, last_speaker, conversation_id, is_organic_response
        )
        
        # Character-specific validation
        character_violations = self._check_character_violations(response, character)
        
        # Additional organic-specific validations
        organic_violations = []
        if is_organic_response:
            organic_violations = self._check_organic_response_violations(response, character, last_speaker, context)
            character_violations.extend(organic_violations)
        
        # CRITICAL: Stage directions = automatic failure
        has_stage_directions = any("stage directions" in violation for violation in character_violations)
        has_third_person = any("third-person" in violation for violation in character_violations)
        has_length_violation = any("Discord length" in violation for violation in character_violations)
        has_organic_violation = any("organic" in violation.lower() for violation in organic_violations)
        
        if has_stage_directions or has_third_person or has_length_violation or has_organic_violation:
            # Automatic failure for critical violations
            overall_score = 0.0
            quality_check_passed = False
            logger.warning(f"❌ Quality Control: Critical violation detected for {character} ({message_type})")
        else:
            # Enhanced overall score calculation with flow weighting
            overall_score = self._calculate_enhanced_overall_score(
                authenticity_score, hallucination_risk, engagement_score, 
                toxicity_score, flow_assessment['flow_score']
            )
            
            # Moderate penalty for organic responses with poor flow (reduced from 20% to 10%)
            if is_organic_response and flow_assessment['flow_score'] < 2.5:
                overall_score *= 0.9  # 10% penalty for poor organic flow (reduced from 20%)
                logger.warning(f"⚠️ Quality Control: Organic flow penalty applied to {character}")
            
            # Adaptive pass/fail determination
            quality_check_passed = overall_score >= adaptive_threshold
        
        # Store conversation turn for future analysis
        self._store_conversation_turn(conversation_id, character, response, overall_score)
        
        analysis_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'overall_score': round(overall_score, 2),
            'quality_check_passed': quality_check_passed,
            'adaptive_threshold': adaptive_threshold,
            'conversation_state': self._get_conversation_state(len(conversation_history)),
            'message_type': message_type,
            'is_organic_response': is_organic_response,
            'metrics': {
                'authenticity_score': round(authenticity_score, 2),
                'hallucination_risk': round(hallucination_risk, 2),
                'engagement_score': round(engagement_score, 2),
                'toxicity_score': round(toxicity_score, 2),
                'flow_score': round(flow_assessment['flow_score'], 2)
            },
            'character_analysis': {
                'character': character,
                'violations': character_violations,
                'character_specific_score': round(authenticity_score, 2),
                'anti_hallucination_settings': char_settings
            },
            'conversation_flow': {
                'flow_score': round(flow_assessment['flow_score'], 2),
                'issues': flow_assessment['issues'],
                'strengths': flow_assessment['strengths'],
                'conversation_awareness': flow_assessment['conversation_awareness'],
                'monologue_tendency': flow_assessment['monologue_tendency'],
                'self_conversation_detected': flow_assessment.get('self_conversation_detected', False),
                'organic_flow_validation': flow_assessment.get('organic_flow_validation', {}) if is_organic_response else {}
            },
            'recommendations': self._generate_enhanced_recommendations(
                authenticity_score, hallucination_risk, engagement_score, 
                toxicity_score, flow_assessment, character, adaptive_threshold
            ),
            'analysis_metadata': {
                'analysis_time_seconds': round(analysis_time, 3),
                'timestamp': datetime.now().isoformat(),
                'response_length': len(response),
                'response_hash': hashlib.md5(response.encode()).hexdigest()[:8],
                'conversation_history_length': len(conversation_history),
                'adaptive_features_enabled': True,
                'organic_response_processing': is_organic_response
            }
        }
        
        # Log quality analysis result
        status = "✅ PASSED" if quality_check_passed else "❌ FAILED"
        logger.info(f"📊 Quality Control: {character} {message_type} - {status} (Score: {overall_score}/{adaptive_threshold})")
        
        return result

    def _calculate_adaptive_quality_threshold(self, conversation_history: List, conversation_id: str) -> float:
        """Calculate dynamic quality threshold based on conversation richness"""
        message_count = len(conversation_history)
        
        # Basic threshold based on message count
        if message_count <= self.conversation_boundaries['cold_limit']:
            base_threshold = self.adaptive_thresholds['cold_start']  # 30.0
        elif message_count <= self.conversation_boundaries['warm_limit']:
            base_threshold = self.adaptive_thresholds['warm_conversation']  # 60.0
        else:
            base_threshold = self.adaptive_thresholds['hot_conversation']  # 75.0
        
        # Adjust based on conversation quality patterns
        if len(conversation_history) >= 3:
            recent_quality = self._analyze_recent_conversation_quality(conversation_history[-5:])
            
            # If recent conversation has been high quality, slightly increase threshold
            if recent_quality > 80:
                base_threshold *= 1.1
            elif recent_quality < 50:
                base_threshold *= 0.9
        
        return min(95.0, max(25.0, base_threshold))  # Cap between 25-95

    def _get_character_anti_hallucination_settings(self, character: str) -> Dict:
        """Get character-specific anti-hallucination settings"""
        return self.character_anti_hallucination.get(character, self.character_anti_hallucination['brian'])

    def _assess_conversation_flow_quality(self, character_name: str, response_text: str, 
                                        conversation_history: List, last_speaker: str = None,
                                        conversation_id: str = "default", is_organic_response: bool = False) -> Dict:
        """Comprehensive conversation flow quality assessment"""
        score = 3.0  # Base score out of 5.0
        issues = []
        strengths = []
        organic_flow_validation = {}
        
        # Enhanced validation for organic responses
        if is_organic_response:
            organic_flow_validation = self._validate_organic_flow(
                response_text, character_name, last_speaker, conversation_history
            )
            
            # Apply organic-specific scoring adjustments
            if organic_flow_validation['natural_follow_up']:
                score += 0.5
                strengths.append("Natural organic follow-up")
            else:
                score -= 0.8
                issues.append("Unnatural organic interruption")
            
            if organic_flow_validation['context_responsive']:
                score += 0.3
                strengths.append("Responsive to conversation context")
            else:
                score -= 0.6
                issues.append("Ignores conversation context")
            
            if organic_flow_validation['appropriate_timing']:
                score += 0.2
                strengths.append("Good timing for organic response")
            else:
                score -= 0.4
                issues.append("Poor timing for intervention")
        
        # 1. Self-Conversation Detection
        self_conversation_detected = False
        if last_speaker == character_name:
            if self._has_self_continuation_indicators(response_text):
                score -= 2.0
                issues.append("Continuing own previous thought without natural break")
                self_conversation_detected = True
        
        # 2. Conversation Coherence and Context Acknowledgment
        if len(conversation_history) > 0:
            last_message_context = conversation_history[-1] if conversation_history else {}
            
            if not self._acknowledges_conversation_context(response_text, last_message_context):
                # Check if it's an abrupt topic change
                if self._has_abrupt_topic_change(response_text):
                    score -= 0.8
                    issues.append("Abrupt topic change without acknowledgment")
                else:
                    score -= 0.4
                    issues.append("Weak context acknowledgment")
            else:
                strengths.append("Good conversation context awareness")
        
        # 3. Conversation Awareness vs Monologue Tendency
        awareness_score = self._count_conversation_indicators(response_text)
        monologue_score = self._count_monologue_indicators(response_text)
        
        if awareness_score > monologue_score:
            score += 0.5
            strengths.append("Shows conversation awareness")
        elif monologue_score > awareness_score * 2:
            score -= 0.7
            issues.append("Sounds like talking to self rather than engaging")
        
        # 4. Character-Specific Flow Validation
        char_flow_score = self._character_specific_flow_check(character_name, response_text)
        score += char_flow_score
        
        if char_flow_score > 0:
            strengths.append(f"Good {character_name}-appropriate conversation style")
        elif char_flow_score < -0.2:
            issues.append(f"Poor {character_name} conversation engagement style")
        
        # 5. Natural Flow Promotion
        if self._promotes_conversation_flow(response_text):
            score += 0.4
            strengths.append("Promotes natural conversation flow")
        
        # 6. Question Responsiveness (if applicable)
        if len(conversation_history) > 0:
            last_message = conversation_history[-1].get('text', '')
            if '?' in last_message and not self._responds_to_question(response_text, last_message):
                score -= 0.6
                issues.append("Ignores direct question")
        
        final_score = max(1.0, min(5.0, score))
        
        return {
            "flow_score": final_score,
            "issues": issues,
            "strengths": strengths,
            "conversation_awareness": awareness_score > 0,
            "monologue_tendency": monologue_score > awareness_score,
            "self_conversation_detected": self_conversation_detected,
            "awareness_indicators": awareness_score,
            "monologue_indicators": monologue_score,
            "organic_flow_validation": organic_flow_validation if is_organic_response else {}
        }

    def _validate_organic_flow(self, response_text: str, character_name: str, 
                              last_speaker: str, conversation_history: List) -> Dict:
        """Validate organic response flow patterns"""
        validation = {
            'natural_follow_up': False,
            'context_responsive': False,
            'appropriate_timing': False,
            'flow_issues': [],
            'flow_strengths': []
        }
        
        # 1. Check for natural follow-up patterns
        natural_follow_patterns = [
            # Reactions
            r'\b(yeah|yep|nah|nope|oh|wow|really|seriously|exactly)\b',
            # Questions/clarifications
            r'\b(what|why|how|when|where|who)\b.*\?',
            # Agreements/disagreements
            r'\b(i agree|i disagree|that\'s right|that\'s wrong|totally|absolutely)\b',
            # Building on ideas
            r'\b(and also|plus|besides|furthermore|on top of that)\b',
            # Character-specific reactions
            r'\b(sweet|awesome|dude|freakin\'|holy crap)\b',  # Peter
            r'\b(indeed|precisely|actually|however|quite)\b',  # Brian
            r'\b(blast|fool|peasant|excellent|fascinating)\b'  # Stewie
        ]
        
        if any(re.search(pattern, response_text, re.IGNORECASE) for pattern in natural_follow_patterns):
            validation['natural_follow_up'] = True
            validation['flow_strengths'].append("Uses natural conversation connectors")
        else:
            validation['flow_issues'].append("Lacks natural follow-up language")
        
        # 2. Check context responsiveness
        if conversation_history:
            last_message = conversation_history[-1].get('text', '') if conversation_history else ''
            
            # Look for direct references to previous content
            if last_message:
                # Extract key words from last message
                last_words = set(last_message.lower().split()) - {
                    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'
                }
                response_words = set(response_text.lower().split())
                
                # Check for word overlap or clear response indicators
                if last_words & response_words or any(
                    indicator in response_text.lower() 
                    for indicator in ['that', 'this', 'it', 'you said', 'you mentioned']
                ):
                    validation['context_responsive'] = True
                    validation['flow_strengths'].append("Responds to previous message content")
                else:
                    validation['flow_issues'].append("No clear response to previous message")
        
        # 3. Check timing appropriateness
        # Organic responses should feel like natural interruptions, not forced entries
        forced_entry_patterns = [
            r'^(hey|hi|hello|so|anyway|by the way)',
            r'\b(let me tell you|speaking of|that reminds me)\b'
        ]
        
        if not any(re.search(pattern, response_text, re.IGNORECASE) for pattern in forced_entry_patterns):
            validation['appropriate_timing'] = True
            validation['flow_strengths'].append("Natural entry without forced conversation starters")
        else:
            validation['flow_issues'].append("Uses forced conversation entry patterns")
        
        return validation

    def _has_self_continuation_indicators(self, response: str) -> bool:
        """Detect if response appears to continue previous thought without break"""
        response_lower = response.lower()
        
        # Check for self-continuation patterns
        for pattern in self.self_continuation_patterns:
            if re.search(pattern, response_lower):
                return True
        
        # Check for stream-of-consciousness indicators
        if response.startswith(('And ', 'Also ', 'Plus ', 'Oh yeah ', 'Oh, and ')):
            return True
        
        return False

    def _acknowledges_conversation_context(self, response: str, last_message_context: Dict) -> bool:
        """Check if response acknowledges conversation context"""
        response_lower = response.lower()
        
        # Strong context acknowledgment indicators
        strong_indicators = [
            'you', 'your', 'that', 'this', 'what you said', 'you\'re right',
            'i agree', 'i disagree', 'about that', 'speaking of that'
        ]
        
        # Weak but acceptable indicators
        weak_indicators = [
            'yeah', 'well', 'actually', 'but', 'however', 'though'
        ]
        
        strong_count = sum(1 for indicator in strong_indicators if indicator in response_lower)
        weak_count = sum(1 for indicator in weak_indicators if indicator in response_lower)
        
        return strong_count > 0 or weak_count >= 2

    def _has_abrupt_topic_change(self, response: str) -> bool:
        """Detect abrupt topic changes without natural transitions"""
        response_lower = response.lower()
        
        # Check for abrupt change patterns
        for pattern in self.abrupt_topic_patterns:
            if re.search(pattern, response_lower):
                return True
        
        # Check if there are natural transition patterns that make it acceptable
        for pattern in self.natural_transition_patterns:
            if re.search(pattern, response_lower):
                return False  # Natural transition found
        
        return False

    def _count_conversation_indicators(self, response: str) -> int:
        """Count indicators of conversation awareness"""
        response_lower = response.lower()
        count = 0
        
        for indicator in self.conversation_indicators:
            count += response_lower.count(indicator)
        
        return count

    def _count_monologue_indicators(self, response: str) -> int:
        """Count indicators of monologue/self-talk tendency"""
        response_lower = response.lower()
        count = 0
        
        for indicator in self.monologue_indicators:
            count += response_lower.count(indicator)
        
        return count

    def _character_specific_flow_check(self, character: str, response: str) -> float:
        """Character-specific conversation flow validation"""
        if character not in self.character_authenticity_rules:
            return 0.0
        
        rules = self.character_authenticity_rules[character]
        score_adjustment = 0.0
        
        # Check for character-appropriate reactions
        typical_reactions = rules.get('typical_reactions', [])
        for reaction in typical_reactions:
            if reaction.lower() in response.lower():
                score_adjustment += 0.2
                break
        
        # Conversation style appropriateness
        conversation_style = rules.get('conversation_style', 'neutral')
        
        if conversation_style == 'reactive' and character == 'peter':
            # Peter should be reactive and enthusiastic
            if any(word in response.lower() for word in ['holy', 'awesome', 'sweet', 'cool']):
                score_adjustment += 0.3
        elif conversation_style == 'analytical' and character == 'brian':
            # Brian should analyze and expand on points
            if any(phrase in response.lower() for phrase in ['actually', 'interesting', 'think', 'believe']):
                score_adjustment += 0.3
        elif conversation_style == 'condescending' and character == 'stewie':
            # Stewie should show superiority while engaging
            if any(phrase in response.lower() for phrase in ['clearly', 'obviously', 'fascinating', 'inferior']):
                score_adjustment += 0.3
        
        return min(0.5, score_adjustment)

    def _promotes_conversation_flow(self, response: str) -> bool:
        """Check if response promotes continued conversation"""
        # Questions promote flow
        if '?' in response:
            return True
        
        # Conversation starters
        flow_promoters = [
            'what do you think', 'don\'t you think', 'right?', 'you know?',
            'what about', 'have you', 'did you', 'will you', 'can you'
        ]
        
        response_lower = response.lower()
        return any(promoter in response_lower for promoter in flow_promoters)

    def _responds_to_question(self, response: str, question: str) -> bool:
        """Check if response appropriately addresses a question"""
        # Simple heuristic: response should acknowledge the question topic
        # This is a basic implementation - could be enhanced with NLP
        
        response_lower = response.lower()
        question_lower = question.lower()
        
        # Extract key words from question (simple approach)
        question_words = set(re.findall(r'\b\w{4,}\b', question_lower))
        response_words = set(re.findall(r'\b\w{4,}\b', response_lower))
        
        # Check for word overlap or direct acknowledgment
        overlap = len(question_words & response_words)
        acknowledgment_phrases = ['yes', 'no', 'well', 'actually', 'i think', 'probably']
        
        has_acknowledgment = any(phrase in response_lower for phrase in acknowledgment_phrases)
        
        return overlap > 0 or has_acknowledgment

    def _detect_hallucination_risk_adaptive(self, response: str, context: str, char_settings: Dict) -> float:
        """Enhanced hallucination detection with character-aware adjustments"""
        base_risk = self._detect_hallucination_risk(response, context)
        
        # Apply character-specific risk multiplier
        adjusted_risk = base_risk * char_settings['risk_multiplier']
        
        # Apply character-specific strictness
        strictness = char_settings['strictness_multiplier']
        final_risk = adjusted_risk * strictness
        
        return max(0.0, min(10.0, final_risk))

    def _calculate_engagement_score(self, response: str, char_settings: Dict) -> float:
        """Enhanced engagement scoring with character-aware length validation"""
        base_score = 5.0
        
        # Character-aware length validation
        length = len(response)
        optimal_length = 200 * char_settings['length_multiplier']
        
        if optimal_length * 0.25 <= length <= optimal_length * 1.5:
            base_score += 2.0
        elif length < optimal_length * 0.1 or length > optimal_length * 2.0:
            base_score -= 2.0
        
        # Rest of engagement calculation (existing logic)
        question_count = response.count('?')
        base_score += min(question_count * 1.0, 2.0)
        
        humor_indicators = ['haha', 'lol', 'funny', 'joke', 'laugh', 'hilarious']
        humor_count = sum(1 for indicator in humor_indicators if indicator in response.lower())
        base_score += min(humor_count * 0.5, 2.0)
        
        if re.search(r'\b(remember|like that time|reminds me|this is worse than)\b', response.lower()):
            base_score += 1.5
        
        return max(0.0, min(10.0, base_score))

    def _calculate_enhanced_overall_score(self, authenticity: float, hallucination: float,
                                        engagement: float, toxicity: float, flow_score: float) -> float:
        """Enhanced overall scoring with conversation flow weighting"""
        # Updated weights to include flow assessment
        weights = {
            'authenticity': 0.25,
            'flow': 0.30,           # NEW: Flow is most important
            'engagement': 0.20,
            'anti_hallucination': 0.20,
            'anti_toxicity': 0.05
        }
        
        # Convert all scores to 100-point scale
        authenticity_scaled = authenticity * 10  # 1-10 -> 10-100
        flow_score_scaled = flow_score * 20      # 1-5 -> 20-100
        engagement_scaled = engagement * 10      # 1-10 -> 10-100
        
        anti_hallucination_score = (10.0 - hallucination) * 10  # Invert and scale to 100
        anti_toxicity_score = (10.0 - toxicity) * 10           # Invert and scale to 100
        
        overall = (
            authenticity_scaled * weights['authenticity'] +
            flow_score_scaled * weights['flow'] +
            engagement_scaled * weights['engagement'] +
            anti_hallucination_score * weights['anti_hallucination'] +
            anti_toxicity_score * weights['anti_toxicity']
        )
        
        return max(0.0, min(100.0, overall))

    def _get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Retrieve conversation history from KeyDB with format compatibility"""
        if not self.redis_client:
            return []
        
        try:
            # Get conversation history from KeyDB
            history_key = f"conversation_history:{conversation_id}"
            history_data = self.redis_client.lrange(history_key, -50, -1)  # Last 50 messages
            
            conversation_history = []
            for item in history_data:
                try:
                    message_data = json.loads(item)
                    
                    # Handle both old Quality Control format and new Discord bot format
                    if 'character' in message_data and 'text' in message_data:
                        # Old Quality Control format - convert to standard
                        standardized_message = {
                            'timestamp': message_data.get('timestamp'),
                            'character': message_data.get('character'),
                            'text': message_data.get('text'),
                            'quality_score': message_data.get('quality_score', 50.0)
                        }
                    elif 'message_type' in message_data and 'content' in message_data:
                        # New Discord bot format - convert to standard
                        standardized_message = {
                            'timestamp': message_data.get('timestamp'),
                            'character': message_data.get('message_type'),
                            'text': message_data.get('content'),
                            'quality_score': message_data.get('quality_score', 50.0)
                        }
                    else:
                        # Skip malformed messages
                        logger.warning(f"Quality Control: Skipping malformed history entry: {message_data}")
                        continue
                    
                    conversation_history.append(standardized_message)
                    
                except json.JSONDecodeError:
                    continue
            
            return conversation_history
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []

    def _store_conversation_turn(self, conversation_id: str, character: str, 
                                response: str, quality_score: float):
        """Store conversation turn in KeyDB using Discord-compatible format"""
        if not self.redis_client:
            return
        
        try:
            # Use Discord bot compatible format
            conversation_turn = {
                'timestamp': datetime.now().isoformat(),
                'author': f"{character.title()} Griffin",  # Convert to proper name
                'content': response,
                'message_type': character,
                'channel_id': conversation_id,
                'quality_score': quality_score  # Keep for quality tracking
            }
            
            history_key = f"conversation_history:{conversation_id}"
            self.redis_client.lpush(history_key, json.dumps(conversation_turn))
            
            # Keep only last 100 messages per conversation
            self.redis_client.ltrim(history_key, -100, -1)
            
            # Set expiry for conversation history (24 hours)
            self.redis_client.expire(history_key, 86400)
            
        except Exception as e:
            logger.error(f"Error storing conversation turn: {e}")

    def _analyze_recent_conversation_quality(self, recent_history: List[Dict]) -> float:
        """Analyze quality of recent conversation history"""
        if not recent_history:
            return 50.0  # Neutral baseline
        
        quality_scores = [turn.get('quality_score', 50.0) for turn in recent_history]
        return sum(quality_scores) / len(quality_scores)

    def _get_conversation_state(self, message_count: int) -> str:
        """Get conversation state description"""
        if message_count <= self.conversation_boundaries['cold_limit']:
            return 'cold_start'
        elif message_count <= self.conversation_boundaries['warm_limit']:
            return 'warm_conversation'
        else:
            return 'hot_conversation'

    def _generate_enhanced_recommendations(self, authenticity: float, hallucination: float,
                                         engagement: float, toxicity: float, 
                                         flow_assessment: Dict, character: str,
                                         adaptive_threshold: float) -> List[str]:
        """Generate enhanced recommendations including flow improvements"""
        recommendations = []
        
        # Flow-specific recommendations
        if flow_assessment['flow_score'] < 3.0:
            recommendations.append("Improve conversation flow and context awareness")
            
            if flow_assessment.get('self_conversation_detected'):
                recommendations.append("Avoid continuing previous thoughts - engage with conversation")
            
            if flow_assessment['monologue_tendency']:
                recommendations.append("Use more conversation-aware language (you, that, this)")
            
            for issue in flow_assessment['issues']:
                if 'abrupt topic change' in issue:
                    recommendations.append("Use natural transitions when changing topics")
                elif 'ignores direct question' in issue:
                    recommendations.append("Respond appropriately to direct questions")
        
        # Character-specific flow recommendations
        if character == 'peter' and flow_assessment['flow_score'] < 3.5:
            recommendations.append("Be more reactive and enthusiastic in responses")
        elif character == 'brian' and flow_assessment['flow_score'] < 3.5:
            recommendations.append("Provide more analytical and thoughtful engagement")
        elif character == 'stewie' and flow_assessment['flow_score'] < 3.5:
            recommendations.append("Show intellectual superiority while staying engaged")
        
        # Traditional quality recommendations
        if authenticity < 7.0:
            recommendations.append(f"Improve character authenticity for {character}")
        
        if hallucination > 3.0:
            recommendations.append("Reduce overconfident claims, add hedging language")
        
        if engagement < 6.0:
            recommendations.append("Make response more engaging with questions or humor")
        
        if toxicity > 2.0:
            recommendations.append("Reduce toxic or offensive language")
        
        # Adaptive threshold context
        if len(recommendations) == 0:
            recommendations.append(f"Response meets {adaptive_threshold:.1f}/100 adaptive quality standard")
        
        return recommendations

    # Keep existing methods with minimal changes
    def _calculate_authenticity_score(self, response: str, character: str) -> float:
        """Calculate how authentic the response is to the character"""
        if character not in self.character_authenticity_rules:
            return 5.0
        
        rules = self.character_authenticity_rules[character]
        score = 10.0
        
        # Check for forbidden phrases (enhanced)
        for phrase in rules['forbidden_phrases']:
            if phrase.lower() in response.lower():
                score -= 2.0
        
        # Check for personality markers (positive points)
        marker_count = 0
        for marker in rules['personality_markers']:
            if marker.lower() in response.lower():
                marker_count += 1
        
        score += min(marker_count * 1.5, 4.0)
        
        # Check speaking style
        if rules['speaking_style'] == 'formal':
            if len([word for word in response.split() if len(word) > 6]) / len(response.split()) > 0.3:
                score += 1.0
        elif rules['speaking_style'] == 'casual':
            if any(word in response.lower() for word in ['hey', 'yeah', 'cool', 'awesome']):
                score += 1.0
        
        return max(0.0, min(10.0, score))

    def _detect_hallucination_risk(self, response: str, context: str = "") -> float:
        """Detect potential hallucination or made-up information"""
        risk_score = 0.0
        
        # AI self-reference patterns (enhanced)
        ai_patterns = [
            r'\b(sorry|apologize|apolog|my apologies)\b',
            r'\bas an ai\b',
            r'\bi am an? (ai|assistant|bot|language model)\b',
            r'\bi cannot\b',
            r'\bi don\'t have\b',
            r'\bi\'m not able to\b'
        ]
        
        for pattern in ai_patterns:
            if re.search(pattern, response.lower()):
                risk_score += 2.0
        
        # Overly specific claims
        if re.search(r'\b\d{4}\b.*\b(year|date|time)\b', response):
            risk_score += 1.0
        
        if re.search(r'\bexactly \d+\b', response):
            risk_score += 1.5
        
        # Hedging vs overconfidence
        hedge_words = ['might', 'could', 'probably', 'seems', 'appears', 'likely']
        overconfident_words = ['definitely', 'absolutely', 'certainly', 'guaranteed']
        
        hedge_count = sum(1 for word in hedge_words if word in response.lower())
        overconfident_count = sum(1 for word in overconfident_words if word in response.lower())
        
        risk_score += overconfident_count * 1.0
        risk_score -= min(hedge_count * 0.5, 2.0)
        
        return max(0.0, min(10.0, risk_score))

    def _calculate_toxicity_score(self, response: str) -> float:
        """Calculate toxicity level (lower is better)"""
        score = 0.0
        
        toxic_keywords = [
            'hate', 'stupid', 'idiot', 'shut up', 'kill', 'die', 'death',
            'racist', 'sexist', 'offensive', 'gross', 'disgusting'
        ]
        
        for keyword in toxic_keywords:
            if keyword in response.lower():
                score += 2.0
        
        profanity_count = len(re.findall(r'\b(damn|hell|crap|ass)\b', response.lower()))
        if profanity_count > 3:
            score += 1.0
        
        if re.search(r'[A-Z]{3,}', response):
            score += 1.0
        
        if response.count('!') > 3:
            score += 0.5
        
        return max(0.0, min(10.0, score))

    def _check_character_violations(self, response: str, character: str) -> List[str]:
        """Check for character-specific violations"""
        violations = []
        
        # Check Discord message length limit (CRITICAL for Discord compatibility)
        if len(response) > 1900:
            violations.append(f"Discord length violation: {len(response)} characters (max 1900)")
        
        # Check for stage directions - CRITICAL for Family Guy authenticity
        stage_direction_patterns = [
            r'\([^)]*(?:laugh|chuckle|sigh|sneer|smirk|roll|grin|frown|nod|shake|gesture|lean|dramatic|condescending|heavily|loudly|quietly)[^)]*\)',
            r'\[[^\]]*(?:laugh|chuckle|sigh|sneer|smirk|roll|grin|frown|nod|shake|gesture|lean|dramatic|condescending|heavily|loudly|quietly)[^\]]*\]',
            r'\*[^*]*(?:laugh|chuckle|sigh|sneer|smirk|roll|grin|frown|nod|shake|gesture|lean|dramatic|condescending|heavily|loudly|quietly)[^*]*\*',
            # Specific patterns from the screenshots
            r'\(sighing\s+heavily\)',
            r'\[sneering\]',
            r'\(chuckles\)',
            r'\(laughs\s+loudly\)',
            r'\(scoffing\)',
            r'\([^)]*\s+in\s+a\s+[^)]*\s+tone\)',
            r'\[[^\]]*\s+condescendingly\s*\]',
            r'\*[^*]*\s+dramatically\s*\*'
        ]
        
        for pattern in stage_direction_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                violations.append("Contains stage directions/narrative elements")
                break  # Only report once
        
        # Check for third-person self-reference
        character_lower = character.lower()
        third_person_patterns = [
            rf'\b{character_lower}\s+(?:says|thinks|feels|looks|does|goes|gets|has|is|was)\b',
            rf'\bthe\s+{character_lower}\b',
            rf'\b{character_lower}\'s\s+(?:face|voice|eyes|expression)\b'
        ]
        
        for pattern in third_person_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                violations.append("Uses third-person self-reference")
                break  # Only report once
        
        if character not in self.character_authenticity_rules:
            return violations
        
        rules = self.character_authenticity_rules[character]
        
        for phrase in rules['forbidden_phrases']:
            if phrase.lower() in response.lower():
                violations.append(f"Used forbidden phrase: '{phrase}'")
        
        marker_found = any(marker.lower() in response.lower() for marker in rules['personality_markers'])
        if not marker_found and len(response) > 50:
            violations.append("Lacks character-specific personality markers")
        
        return violations

    def _check_organic_response_violations(self, response: str, character: str, last_speaker: str, context: str) -> List[str]:
        """Check for organic response specific violations (relaxed for better flow)"""
        violations = []
        
        # 1. Check if character is responding to themselves (major violation)
        if last_speaker and last_speaker.lower() == character.lower():
            violations.append("Organic violation: Character responding to their own message")
        
        # 2. Relaxed context relevance check - be more permissive for organic responses
        if context and len(context.strip()) > 10:  # Only check for longer contexts
            context_lower = context.lower()
            response_lower = response.lower()
            
            # Check for conversational connectors that show engagement (expanded list)
            engagement_indicators = [
                "yeah", "totally", "agree", "disagree", "that", "this", "it", "right", "true", 
                "exactly", "absolutely", "well", "but", "however", "also", "too", "so", 
                "anyway", "actually", "really", "oh", "hey", "wait", "what", "why", "how",
                "peter", "brian", "stewie", "lois", "meg", "chris"  # Character names show engagement
            ]
            has_engagement = any(indicator in response_lower for indicator in engagement_indicators)
            
            # Basic context relevance check (more lenient)
            context_words = set(context_lower.split())
            response_words = set(response_lower.split())
            
            # Remove common words
            common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "i", "you", "he", "she", "it", "they", "we"}
            context_words = context_words - common_words
            response_words = response_words - common_words
            
            # Check for some shared words (basic relevance)
            shared_words = context_words & response_words
            
            # Only flag as violation if there's NO shared content AND no engagement indicators AND it's clearly off-topic
            if (len(context_words) > 5 and len(shared_words) == 0 and not has_engagement and 
                len(response) > 50):  # Only check longer responses
                
                # Additional leniency: Allow character-specific typical responses
                character_typical_responses = {
                    "peter": ["holy crap", "sweet", "awesome", "freakin", "nyeheheh", "beer", "food"],
                    "brian": ["indeed", "actually", "however", "sophisticated", "intellectual", "wine"],
                    "stewie": ["blast", "fool", "inferior", "genius", "brilliant", "mother"]
                }
                
                typical_phrases = character_typical_responses.get(character.lower(), [])
                has_typical_response = any(phrase in response_lower for phrase in typical_phrases)
                
                # Only flag if it's truly irrelevant AND doesn't use typical character language
                if not has_typical_response:
                    violations.append("Organic violation: Response appears unrelated to conversation context")
        
        # 3. Very relaxed check for conversation starters - only flag obvious ones
        organic_bad_starters = [
            "hello everyone", "hi there", "good morning", "good evening", 
            "let me start by saying", "i would like to begin"
        ]
        
        response_start = response.lower().strip()[:20]  # Only check first 20 characters
        if any(starter in response_start for starter in organic_bad_starters):
            violations.append("Organic violation: Using formal conversation starter in organic follow-up")
        
        # 4. Increased length limit for organic responses (was 300, now 500)
        if len(response) > 500:
            violations.append("Organic violation: Response too long for natural follow-up")
        
        # 5. Relaxed repetitive content check
        if context and response and len(response) > 30:
            context_words = context.lower().split()
            response_words = response.lower().split()
            
            # Check if response repeats too many words from context (more lenient)
            if len(context_words) > 5 and len(response_words) > 5:
                repeated_words = set(context_words) & set(response_words)
                repeat_ratio = len(repeated_words) / len(set(response_words))
                
                if repeat_ratio > 0.8:  # Raised from 60% to 80%
                    violations.append("Organic violation: Response repeats excessive content from previous message")
        
        # 6. Relaxed character-specific organic violations
        character_lower = character.lower()
        
        if character_lower == "brian":
            # Brian can use intellectual language if it fits the conversation
            intellectual_tangent_indicators = ["furthermore", "consequently", "nevertheless", "notwithstanding"]
            if any(indicator in response.lower() for indicator in intellectual_tangent_indicators):
                # Only flag if using multiple overly formal words in short response
                formal_count = sum(1 for indicator in intellectual_tangent_indicators if indicator in response.lower())
                if formal_count >= 2 and len(response) < 100:
                    violations.append("Organic violation: Brian using excessive formal language in brief response")
        
        elif character_lower == "stewie":
            # Stewie can be dramatic, only flag truly excessive monologues
            domination_indicators = ["plan", "scheme", "world domination", "fool", "inferior beings", "conquest"]
            domination_count = sum(1 for ind in domination_indicators if ind in response.lower())
            if domination_count >= 3 and len(response) > 200:  # Multiple indicators in long response
                violations.append("Organic violation: Stewie launching excessive domination monologue")
        
        elif character_lower == "peter":
            # Peter can bring up random topics, only flag if completely absurd
            if len(response) > 300:  # Only check longer responses
                peter_random_topics = ["chicken fight", "pawtucket brewery", "diarrhea", "giant chicken"]
                unrelated_count = sum(1 for topic in peter_random_topics if topic in response.lower())
                if unrelated_count >= 2:  # Multiple very specific unrelated topics
                    violations.append("Organic violation: Peter introducing excessive unrelated specific topics")
        
        return violations

    # Legacy method for backwards compatibility
    def analyze_response_quality(self, response: str, character: str, context: str = "") -> Dict:
        """Legacy method - redirects to enhanced analysis"""
        return self.analyze_response_quality_enhanced(response, character, "default", context)

# Initialize enhanced service
quality_service = EnhancedQualityControlService()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'enhanced-quality-control',
        'features': {
            'adaptive_quality_control': True,
            'character_aware_anti_hallucination': True,
            'conversation_flow_assessment': True,
            'self_conversation_detection': True,
            'keydb_conversation_history': True
        },
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

@app.route('/analyze', methods=['POST'])
def analyze_response():
    """Enhanced response quality analysis"""
    try:
        data = request.get_json()
        
        if not data or 'response' not in data:
            return jsonify({'error': 'Missing response field'}), 400
        
        response_text = data['response']
        character = data.get('character', 'unknown')
        conversation_id = data.get('conversation_id', 'default')
        context = data.get('context', '')
        last_speaker = data.get('last_speaker')
        message_type = data.get('message_type', 'direct')  # Support organic_response type
        
        # Use enhanced analysis with message type support
        analysis = quality_service.analyze_response_quality_enhanced(
            response_text, character, conversation_id, context, last_speaker, message_type
        )
        
        # Log the analysis type for debugging
        if message_type == "organic_response":
            logger.info(f"🌱 Quality Control: Processed organic response for {character} (ID: {conversation_id})")
        else:
            logger.info(f"📝 Quality Control: Processed direct response for {character} (ID: {conversation_id})")
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error in enhanced analysis: {str(e)}")
        return jsonify({'error': f'Enhanced analysis failed: {str(e)}'}), 500

@app.route('/analyze-legacy', methods=['POST'])
def analyze_response_legacy():
    """Legacy analysis endpoint for backwards compatibility"""
    try:
        data = request.get_json()
        
        if not data or 'response' not in data:
            return jsonify({'error': 'Missing response field'}), 400
        
        response_text = data['response']
        character = data.get('character', 'unknown')
        context = data.get('context', '')
        
        analysis = quality_service.analyze_response_quality(response_text, character, context)
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error in legacy analysis: {str(e)}")
        return jsonify({'error': f'Legacy analysis failed: {str(e)}'}), 500

@app.route('/config', methods=['GET'])
def get_config():
    """Get enhanced quality control configuration"""
    return jsonify({
        'adaptive_thresholds': quality_service.adaptive_thresholds,
        'conversation_boundaries': quality_service.conversation_boundaries,
        'character_anti_hallucination': quality_service.character_anti_hallucination,
        'character_rules': quality_service.character_authenticity_rules,
        'features_enabled': {
            'adaptive_quality_control': True,
            'character_aware_anti_hallucination': True,
            'conversation_flow_assessment': True,
            'keydb_integration': quality_service.redis_client is not None
        }
    })

@app.route('/conversation-analysis', methods=['GET'])
def get_conversation_analysis():
    """Get conversation history analysis"""
    try:
        conversation_id = request.args.get('conversation_id', 'default')
        history = quality_service._get_conversation_history(conversation_id)
        
        if not history:
            return jsonify({'error': 'No conversation history found'}), 404
        
        # Analyze conversation patterns
        total_messages = len(history)
        conversation_state = quality_service._get_conversation_state(total_messages)
        adaptive_threshold = quality_service._calculate_adaptive_quality_threshold(history, conversation_id)
        recent_quality = quality_service._analyze_recent_conversation_quality(history[-5:])
        
        # Character participation
        character_participation = {}
        for turn in history:
            char = turn.get('character', 'unknown')
            character_participation[char] = character_participation.get(char, 0) + 1
        
        return jsonify({
            'conversation_id': conversation_id,
            'total_messages': total_messages,
            'conversation_state': conversation_state,
            'adaptive_threshold': adaptive_threshold,
            'recent_quality_average': recent_quality,
            'character_participation': character_participation,
            'conversation_history': history[-10:] if history else []  # Last 10 messages
        })
        
    except Exception as e:
        logger.error(f"Error in conversation analysis: {str(e)}")
        return jsonify({'error': f'Conversation analysis failed: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.getenv('QUALITY_CONTROL_PORT', 6003))
    app.run(host='0.0.0.0', port=port, debug=False) 