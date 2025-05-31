from flask import Flask, request, jsonify
import logging
import json
import random
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
import asyncio
import aiohttp
import os
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Character Config Service URL
CHARACTER_CONFIG_URL = os.getenv("CHARACTER_CONFIG_API_URL", "http://character-config:6006")
RAG_RETRIEVER_URL = os.getenv("RAG_RETRIEVER_URL", "http://rag-retriever:6007")

class FineTuningService:
    def __init__(self):
        # A/B Testing Framework
        self.active_experiments = {}
        self.experiment_results = defaultdict(list)
        self.user_feedback_history = defaultdict(list)
        
        # Response optimization tracking
        self.response_performance = defaultdict(list)
        self.prompt_variations = defaultdict(list)
        self.optimization_metrics = {
            'response_quality': [],
            'user_engagement': [],
            'character_authenticity': [],
            'response_time': []
        }
        
        # Learning system
        self.feedback_weights = {
            'thumbs_up': 1.0,
            'thumbs_down': -1.0,
            'love': 1.5,
            'laugh': 1.2,
            'wow': 0.8,
            'angry': -1.2,
            'sad': -0.5
        }
        
        # Cache for character configs to avoid repeated calls
        self.character_config_cache = {}
        self.cache_ttl = 300  # 5 minutes

    def _get_current_character_config(self, character: str) -> Dict:
        """Fetch current character configuration from character-config service"""
        cache_key = f"config_{character}"
        current_time = datetime.now().timestamp()
        
        # Check cache first
        if cache_key in self.character_config_cache:
            cached_data, cached_time = self.character_config_cache[cache_key]
            if current_time - cached_time < self.cache_ttl:
                return cached_data
        
        try:
            # Fetch from character-config service using the correct endpoint
            response = requests.get(f"{CHARACTER_CONFIG_URL}/llm_prompt/{character}", timeout=10)
            if response.status_code == 200:
                config_data = response.json()
                # Cache the result
                self.character_config_cache[cache_key] = (config_data, current_time)
                return config_data
            else:
                logger.error(f"Failed to fetch character config for {character}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching character config for {character}: {e}")
            return None

    def _get_base_prompt(self, character: str) -> str:
        """Get the current base prompt for a character from character-config service"""
        config = self._get_current_character_config(character)
        if config and 'llm_prompt' in config:
            return config['llm_prompt']
        
        # Fallback to basic prompts if service is unavailable
        fallback_prompts = {
            'peter': "You are Peter Griffin from Family Guy. Respond as Peter would:",
            'brian': "You are Brian Griffin from Family Guy. Respond as Brian would:",
            'stewie': "You are Stewie Griffin from Family Guy. Respond as Stewie would:"
        }
        
        return fallback_prompts.get(character, f"You are {character} from Family Guy. Respond as {character} would:")

    def _get_rag_context(self, character: str, query: str = None) -> str:
        """Get dynamic RAG context to add variety to prompts with enhanced reliability"""
        try:
            # Create character-specific queries for RAG retrieval
            if not query:
                query_options = {
                    'peter': [
                        "Peter Griffin funny moments", 
                        "Peter Griffin at work brewery", 
                        "Peter Griffin family interactions", 
                        "Peter Griffin eating food",
                        "Peter Griffin watching TV",
                        "Peter Griffin with friends"
                    ],
                    'brian': [
                        "Brian Griffin intellectual discussions", 
                        "Brian Griffin writing novel", 
                        "Brian Griffin culture politics", 
                        "Brian Griffin philosophy",
                        "Brian Griffin pretentious moments",
                        "Brian Griffin sophisticated conversations"
                    ], 
                    'stewie': [
                        "Stewie Griffin genius inventions", 
                        "Stewie Griffin evil plans", 
                        "Stewie Griffin British accent", 
                        "Stewie Griffin condescending remarks",
                        "Stewie Griffin sophisticated vocabulary",
                        "Stewie Griffin family dynamics"
                    ]
                }
                
                character_queries = query_options.get(character, [f"{character} Griffin family guy"])
                query = random.choice(character_queries)
            
            # Make enhanced request to RAG retriever
            rag_payload = {
                "query": query, 
                "num_results": 2,
                "min_score": 0.3  # Minimum relevance score if supported
            }
            
            # Add character filter if the RAG service supports it
            if character in ['peter', 'brian', 'stewie']:
                rag_payload["character_filter"] = character
            
            response = requests.post(
                f"{RAG_RETRIEVER_URL}/retrieve",
                json=rag_payload,
                timeout=6,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": f"FineTuning-{character}"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                rag_context = data.get("context", "")
                
                if rag_context and len(rag_context.strip()) > 10:
                    # Clean and format the context
                    cleaned_context = self._clean_rag_context(rag_context, character)
                    
                    # Truncate to reasonable length for prompt
                    if len(cleaned_context) > 350:
                        cleaned_context = cleaned_context[:350] + "..."
                    
                    logger.info(f"🔍 Fine-tuning: Retrieved RAG context for {character} query: '{query[:50]}...'")
                    return cleaned_context
                else:
                    logger.info(f"🔍 Fine-tuning: Empty RAG context for {character}, using fallback")
            else:
                logger.warning(f"RAG retrieval failed for {character}: HTTP {response.status_code}")
            
            # Fallback to character-specific context if RAG fails
            return self._get_fallback_context(character)
            
        except requests.exceptions.Timeout:
            logger.warning(f"RAG retrieval timeout for {character}, using fallback")
            return self._get_fallback_context(character)
        except requests.exceptions.ConnectionError:
            logger.warning(f"RAG service unavailable for {character}, using fallback")
            return self._get_fallback_context(character)
        except Exception as e:
            logger.warning(f"Error fetching RAG context for {character}: {e}")
            return self._get_fallback_context(character)

    def _clean_rag_context(self, rag_context: str, character: str) -> str:
        """Clean and format RAG context for prompt use"""
        try:
            # Remove excessive whitespace and newlines
            cleaned = " ".join(rag_context.split())
            
            # Remove any XML/HTML-like tags if present
            import re
            cleaned = re.sub(r'<[^>]+>', '', cleaned)
            
            # Ensure it's relevant to the character
            if character.lower() not in cleaned.lower():
                # If character name not mentioned, add context
                cleaned = f"In {character.title()}'s style: {cleaned}"
            
            return cleaned.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning RAG context: {e}")
            return rag_context[:300]  # Fallback to truncated original

    def _get_fallback_context(self, character: str) -> str:
        """Get fallback context when RAG service is unavailable"""
        fallback_contexts = {
            'peter': "Peter Griffin loves food, beer, and TV. He's impulsive and childlike with simple observations.",
            'brian': "Brian Griffin is intellectual and pretentious, often referencing culture, politics, and literature.",
            'stewie': "Stewie Griffin is a sophisticated baby genius with advanced vocabulary and condescending remarks."
        }
        
        return fallback_contexts.get(character, f"{character.title()} Griffin from Family Guy has a distinctive personality.")

    def create_ab_experiment(self, experiment_name: str, variants: List[Dict], 
                            traffic_split: Dict[str, float] = None) -> Dict:
        """Create a new A/B testing experiment"""
        
        if traffic_split is None:
            # Equal split by default
            split_value = 1.0 / len(variants)
            traffic_split = {f"variant_{i}": split_value for i in range(len(variants))}
        
        experiment = {
            'name': experiment_name,
            'variants': variants,
            'traffic_split': traffic_split,
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            'total_impressions': 0,
            'results': {variant: {'impressions': 0, 'conversions': 0, 'feedback_score': 0.0} 
                       for variant in traffic_split.keys()}
        }
        
        self.active_experiments[experiment_name] = experiment
        logger.info(f"Created A/B experiment: {experiment_name} with {len(variants)} variants")
        
        return experiment

    def get_experiment_variant(self, experiment_name: str, user_id: str = None) -> Dict:
        """Get variant for a user in an A/B test"""
        if experiment_name not in self.active_experiments:
            return {'error': 'Experiment not found'}
        
        experiment = self.active_experiments[experiment_name]
        
        # Consistent assignment based on user_id hash
        if user_id:
            hash_value = int(hashlib.md5(f"{experiment_name}_{user_id}".encode()).hexdigest()[:8], 16)
            cumulative_prob = 0.0
            random_value = (hash_value % 10000) / 10000.0
        else:
            random_value = random.random()
        
        # Select variant based on traffic split
        cumulative_prob = 0.0
        selected_variant = None
        selected_config = None
        
        for i, (variant_name, probability) in enumerate(experiment['traffic_split'].items()):
            cumulative_prob += probability
            if random_value <= cumulative_prob:
                selected_variant = variant_name
                selected_config = experiment['variants'][i]
                break
        
        # Update impression count
        experiment['total_impressions'] += 1
        experiment['results'][selected_variant]['impressions'] += 1
        
        return {
            'experiment': experiment_name,
            'variant': selected_variant,
            'config': selected_config,
            'user_id': user_id
        }

    def optimize_prompt(self, character: str, context: Dict, performance_feedback: Dict = None) -> Dict:
        """Generate optimized prompt based on context, retry history, and performance feedback with enhanced RAG and character config integration"""
        
        # Get current base prompt from character-config service
        base_prompt = self._get_base_prompt(character)
        if not base_prompt:
            return {'error': f'Unable to fetch configuration for character: {character}'}
        
        # Get current character configuration for additional context
        character_config = self._get_current_character_config(character)
        
        # Analyze context to determine optimizations
        message_topic = context.get('topic', 'general')
        user_emotion = context.get('emotion')
        conversation_context = context.get('conversation_context', {})
        request_context = context.get('request_context', {})
        retry_optimization = context.get('retry_optimization', False)
        
        # Start with the current character prompt
        optimized_prompt = base_prompt
        
        # Add context-based enhancements
        context_additions = []
        
        # Enhanced RAG integration - get relevant context for character and topic
        rag_context = self._get_enhanced_rag_context(character, context, retry_optimization)
        if rag_context:
            context_additions.append(f"RELEVANT CONTEXT: {rag_context}")
            logger.info(f"🔍 Fine-tuning: Added RAG context for {character}")
        
        # Handle retry optimization - learn from failed attempts
        if retry_optimization and 'failed_attempts' in conversation_context:
            failed_attempts = conversation_context.get('failed_attempts', [])
            if failed_attempts:
                logger.info(f"🔄 Fine-tuning: Optimizing for retry after {len(failed_attempts)} failed attempts")
                
                # Use RAG to get better examples for retry guidance
                retry_guidance = self._generate_enhanced_retry_guidance(character, failed_attempts, rag_context)
                if retry_guidance:
                    context_additions.append(f"RETRY OPTIMIZATION: {retry_guidance}")
        
        # Character config-based enhancements
        if character_config:
            config_enhancements = self._generate_config_based_enhancements(character, character_config, context)
            if config_enhancements:
                context_additions.extend(config_enhancements)
        
        # Standard context enhancements with RAG support
        if user_emotion and user_emotion != 'neutral':
            emotion_enhancement = self._get_emotion_enhancement_with_rag(character, user_emotion)
            if emotion_enhancement:
                context_additions.append(emotion_enhancement)
        
        if message_topic != 'general':
            topic_enhancement = self._get_topic_enhancement_with_rag(character, message_topic)
            if topic_enhancement:
                context_additions.append(topic_enhancement)
        
        # Add performance-based optimizations
        if performance_feedback:
            performance_optimizations = self._generate_prompt_optimizations(character, performance_feedback)
            if performance_optimizations:
                context_additions.append(performance_optimizations)
        
        # Add conversation context if available
        if conversation_context.get('recent_topics'):
            context_addition = self._generate_context_addition_with_rag(character, conversation_context)
            if context_addition:
                context_additions.append(context_addition)
        
        # Organic response specific optimizations with RAG
        if message_topic == 'organic_follow_up':
            organic_enhancement = self._get_organic_response_enhancement_with_rag(character, conversation_context)
            if organic_enhancement:
                context_additions.append(organic_enhancement)
        
        # Apply conversation length optimizations
        conversation_length = conversation_context.get('conversation_length', 0)
        if conversation_length > 5:
            # Use RAG to find examples of conversation variety
            variety_enhancement = self._get_conversation_variety_enhancement(character, conversation_length)
            if variety_enhancement:
                context_additions.append(variety_enhancement)
        
        # Quality-based optimizations from recent performance data with RAG examples
        recent_performance = self._get_recent_character_performance(character)
        if recent_performance:
            quality_optimization = self._generate_quality_optimization_with_rag(character, recent_performance)
            if quality_optimization:
                context_additions.append(quality_optimization)
        
        # Combine all enhancements
        if context_additions:
            enhancement_text = "\n\nCONTEXT ENHANCEMENTS:\n" + "\n".join(f"- {addition}" for addition in context_additions)
            optimized_prompt = optimized_prompt + enhancement_text
        
        # Calculate confidence based on available context and optimizations
        confidence_factors = []
        if context_additions:
            confidence_factors.append(0.2)  # Base for having enhancements
        if conversation_context:
            confidence_factors.append(0.3)  # Conversation context available
        if performance_feedback:
            confidence_factors.append(0.3)  # Performance data available
        if retry_optimization:
            confidence_factors.append(0.2)  # Retry optimization applied
        if rag_context:
            confidence_factors.append(0.2)  # RAG context available
        if character_config:
            confidence_factors.append(0.1)  # Character config enhanced
        
        confidence = min(1.0, sum(confidence_factors))
        
        logger.info(f"🎯 Fine-tuning: Generated optimized prompt for {character} (confidence: {confidence:.2f})")
        if retry_optimization:
            logger.info(f"   🔄 Retry optimization applied with {len(context_additions)} enhancements")
        if rag_context:
            logger.info(f"   🔍 RAG context integrated for enhanced optimization")
        
        return {
            'optimized_prompt': optimized_prompt,
            'confidence': confidence,
            'enhancements_applied': len(context_additions),
            'character': character,
            'retry_optimization': retry_optimization,
            'rag_enhanced': bool(rag_context),
            'config_enhanced': bool(character_config),
            'timestamp': datetime.now().isoformat()
        }

    def _get_emotion_enhancement(self, character: str, emotion: str) -> str:
        """Generate emotion-based enhancement for character"""
        emotion_map = {
            'peter': {
                'excited': "Show Peter's childlike excitement and enthusiasm.",
                'angry': "Channel Peter's over-the-top anger and impulsiveness.",
                'happy': "Express Peter's simple joy and humor.",
                'sad': "Show Peter's dramatic sadness but keep it lighthearted."
            },
            'brian': {
                'excited': "Express Brian's intellectual enthusiasm with sophistication.",
                'angry': "Show Brian's articulate frustration and wit.",
                'happy': "Display Brian's cultured satisfaction and dry humor.",
                'sad': "Convey Brian's melancholy with philosophical depth."
            },
            'stewie': {
                'excited': "Show Stewie's genius-level enthusiasm with condescension.",
                'angry': "Express Stewie's dramatic fury with sophisticated vocabulary.",
                'happy': "Display Stewie's smug satisfaction and superior intellect.",
                'sad': "Show Stewie's theatrical sadness with British flair."
            }
        }
        
        return emotion_map.get(character, {}).get(emotion, "")

    def _get_topic_enhancement(self, character: str, topic: str) -> str:
        """Generate topic-based enhancement for character"""
        topic_map = {
            'peter': {
                'food': "Peter gets very excited about food and restaurants.",
                'work': "Peter talks about the brewery and his coworkers.",
                'family': "Peter mentions his family dynamics with humor.",
                'tv': "Peter references his favorite TV shows and pop culture."
            },
            'brian': {
                'politics': "Brian shares his liberal political views intellectually.",
                'culture': "Brian references literature, art, or classical music.",
                'philosophy': "Brian explores deep philosophical concepts.",
                'writing': "Brian discusses his literary ambitions and critiques."
            },
            'stewie': {
                'science': "Stewie demonstrates his advanced scientific knowledge.",
                'technology': "Stewie references his inventions and future plans.",
                'world_domination': "Stewie hints at his evil schemes with sophistication.",
                'family': "Stewie expresses his complex relationship with his mother."
            }
        }
        
        char_topics = topic_map.get(character, {})
        for topic_key, enhancement in char_topics.items():
            if topic_key.lower() in topic.lower():
                return enhancement
        
        return ""

    def record_response_performance(self, response_id: str, character: str, 
                                  metrics: Dict, user_feedback: str = None) -> Dict:
        """Record response performance for learning"""
        
        performance_data = {
            'response_id': response_id,
            'character': character,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'user_feedback': user_feedback
        }
        
        # Store performance data
        self.response_performance[character].append(performance_data)
        
        # Update optimization metrics
        for metric_name, value in metrics.items():
            if metric_name in self.optimization_metrics:
                self.optimization_metrics[metric_name].append(value)
        
        # Process user feedback if provided
        feedback_score = 0.0
        if user_feedback and user_feedback in self.feedback_weights:
            feedback_score = self.feedback_weights[user_feedback]
            
            self.user_feedback_history[character].append({
                'response_id': response_id,
                'feedback': user_feedback,
                'score': feedback_score,
                'timestamp': datetime.now().isoformat()
            })
        
        # Generate insights from performance
        insights = self._analyze_performance_trends(character)
        
        return {
            'recorded': True,
            'feedback_score': feedback_score,
            'character_performance': self._calculate_character_performance(character),
            'insights': insights
        }

    def get_optimization_recommendations(self, character: str = None) -> Dict:
        """Get recommendations for improving response quality"""
        
        recommendations = []
        
        if character:
            # Character-specific recommendations
            char_recommendations = self._generate_character_recommendations(character)
            recommendations.extend(char_recommendations)
        else:
            # Global recommendations for all known characters
            known_characters = ['peter', 'brian', 'stewie']
            for char in known_characters:
                char_recommendations = self._generate_character_recommendations(char)
                recommendations.extend(char_recommendations)
        
        # Priority sorting
        recommendations.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        return {
            'recommendations': recommendations,
            'generated_at': datetime.now().isoformat(),
            'total_recommendations': len(recommendations)
        }

    def run_ab_test_analysis(self, experiment_name: str) -> Dict:
        """Analyze A/B test results and determine winner"""
        
        if experiment_name not in self.active_experiments:
            return {'error': 'Experiment not found'}
        
        experiment = self.active_experiments[experiment_name]
        results = experiment['results']
        
        # Calculate conversion rates and statistical significance
        analysis = {}
        conversion_rates = {}
        
        for variant, data in results.items():
            impressions = data['impressions']
            conversions = data['conversions']
            
            if impressions > 0:
                conversion_rate = conversions / impressions
                conversion_rates[variant] = conversion_rate
                
                analysis[variant] = {
                    'impressions': impressions,
                    'conversions': conversions,
                    'conversion_rate': round(conversion_rate, 4),
                    'feedback_score': round(data['feedback_score'], 3),
                    'sample_size': impressions
                }
        
        # Determine winner (simple comparison - could be enhanced with statistical tests)
        if conversion_rates:
            winning_variant = max(conversion_rates, key=conversion_rates.get)
            winning_rate = conversion_rates[winning_variant]
            
            # Calculate confidence level (simplified)
            confidence = self._calculate_test_confidence(results)
            
            recommendation = self._generate_test_recommendation(
                winning_variant, winning_rate, confidence, experiment
            )
        else:
            winning_variant = None
            recommendation = "Insufficient data for analysis"
        
        return {
            'experiment': experiment_name,
            'status': experiment['status'],
            'total_impressions': experiment['total_impressions'],
            'variant_analysis': analysis,
            'winning_variant': winning_variant,
            'confidence_level': confidence if conversion_rates else 0,
            'recommendation': recommendation,
            'analyzed_at': datetime.now().isoformat()
        }

    def apply_learning_updates(self, character: str = None) -> Dict:
        """Apply learned optimizations to prompts and configurations"""
        
        updates_applied = []
        
        if character:
            character_updates = self._apply_character_learning(character)
            updates_applied.extend(character_updates)
        else:
            # Apply learning for all known characters
            known_characters = ['peter', 'brian', 'stewie']
            for char in known_characters:
                character_updates = self._apply_character_learning(char)
                updates_applied.extend(character_updates)
        
        # Update global optimization metrics
        self._update_global_optimizations()
        
        return {
            'updates_applied': updates_applied,
            'total_updates': len(updates_applied),
            'updated_at': datetime.now().isoformat(),
            'next_optimization_scheduled': (datetime.now() + timedelta(hours=24)).isoformat()
        }

    # Helper methods
    def _get_reference_type(self, character: str, topic: str) -> str:
        """Get appropriate reference type for character and topic"""
        reference_map = {
            'peter': {
                'food': 'his favorite restaurants or meals',
                'work': 'the brewery or his coworkers',
                'family': 'his wife Lois or the kids',
                'default': 'some random pop culture reference'
            },
            'brian': {
                'politics': 'political philosophers or current events',
                'culture': 'literature or classical music',
                'work': 'his writing or intellectual pursuits',
                'default': 'some intellectual reference'
            },
            'stewie': {
                'science': 'advanced scientific concepts',
                'technology': 'his inventions or future plans',
                'family': 'his complicated relationship with his mother',
                'default': 'his superior intellect'
            }
        }
        
        char_refs = reference_map.get(character, {})
        return char_refs.get(topic, char_refs.get('default', 'something relevant'))

    def _generate_prompt_optimizations(self, character: str, performance_feedback: Dict) -> str:
        """Generate prompt optimizations based on performance feedback"""
        optimizations = []
        
        if performance_feedback.get('authenticity_score', 0) < 7.0:
            optimizations.append(f"Make sure to really capture {character}'s unique speaking style and mannerisms.")
        
        if performance_feedback.get('engagement_score', 0) < 6.0:
            optimizations.append("Be more engaging and interactive in your response.")
        
        if performance_feedback.get('humor_level', 0) < 0.5:
            optimizations.append("Add more humor and personality to match the Family Guy style.")
        
        return " ".join(optimizations)

    def _generate_context_addition(self, character: str, conversation_context: Dict) -> str:
        """Generate context-aware additions to prompts"""
        additions = []
        
        recent_topics = conversation_context.get('recent_topics', [])
        if recent_topics:
            additions.append(f"Keep in mind the conversation has been about {', '.join(recent_topics[-3:])}.")
        
        last_speaker = conversation_context.get('last_speaker')
        if last_speaker and last_speaker != character:
            additions.append(f"You're responding to {last_speaker}.")
        
        return " ".join(additions)

    def _calculate_optimization_confidence(self, context: Dict, performance_feedback: Dict) -> float:
        """Calculate confidence level in optimization quality"""
        base_confidence = 0.7
        
        # More context = higher confidence
        if context.get('topic') != 'general':
            base_confidence += 0.1
        
        if context.get('emotion'):
            base_confidence += 0.1
        
        # Performance feedback increases confidence
        if performance_feedback:
            base_confidence += 0.2
        
        return min(1.0, base_confidence)

    def _analyze_performance_trends(self, character: str) -> List[str]:
        """Analyze performance trends for a character"""
        insights = []
        
        performance_data = self.response_performance[character]
        if len(performance_data) < 5:
            return ["Insufficient data for trend analysis"]
        
        # Analyze recent performance (last 10 responses)
        recent_data = performance_data[-10:]
        
        # Calculate averages
        avg_quality = statistics.mean([d['metrics'].get('quality_score', 0) for d in recent_data])
        avg_engagement = statistics.mean([d['metrics'].get('engagement_score', 0) for d in recent_data])
        
        if avg_quality < 6.0:
            insights.append(f"{character}'s response quality has been below average")
        
        if avg_engagement < 6.0:
            insights.append(f"{character}'s engagement levels could be improved")
        
        # Feedback analysis
        feedback_data = self.user_feedback_history[character]
        if feedback_data:
            recent_feedback = [f['score'] for f in feedback_data[-20:]]
            avg_feedback = statistics.mean(recent_feedback)
            
            if avg_feedback > 0.5:
                insights.append(f"{character} has been receiving positive user feedback")
            elif avg_feedback < -0.2:
                insights.append(f"{character} needs improvement based on user feedback")
        
        return insights or ["Performance appears stable"]

    def _calculate_character_performance(self, character: str) -> Dict:
        """Calculate overall performance metrics for a character"""
        performance_data = self.response_performance[character]
        
        if not performance_data:
            return {'overall_score': 0.0, 'total_responses': 0}
        
        recent_data = performance_data[-20:]  # Last 20 responses
        
        scores = {
            'quality': statistics.mean([d['metrics'].get('quality_score', 0) for d in recent_data]),
            'engagement': statistics.mean([d['metrics'].get('engagement_score', 0) for d in recent_data]),
            'authenticity': statistics.mean([d['metrics'].get('authenticity_score', 0) for d in recent_data])
        }
        
        overall_score = statistics.mean(scores.values())
        
        return {
            'overall_score': round(overall_score, 2),
            'component_scores': {k: round(v, 2) for k, v in scores.items()},
            'total_responses': len(performance_data),
            'recent_responses': len(recent_data)
        }

    def _generate_character_recommendations(self, character: str) -> List[Dict]:
        """Generate improvement recommendations for a character"""
        recommendations = []
        
        performance = self._calculate_character_performance(character)
        component_scores = performance.get('component_scores', {})
        
        # Quality recommendations
        if component_scores.get('quality', 0) < 7.0:
            recommendations.append({
                'type': 'quality_improvement',
                'character': character,
                'priority_score': 9,
                'recommendation': f"Improve response quality for {character} through better prompt engineering",
                'specific_actions': [
                    "Enhance character-specific prompts",
                    "Add more context-aware optimizations",
                    "Include better personality markers"
                ]
            })
        
        # Engagement recommendations
        if component_scores.get('engagement', 0) < 6.0:
            recommendations.append({
                'type': 'engagement_boost',
                'character': character,
                'priority_score': 7,
                'recommendation': f"Boost engagement levels for {character}",
                'specific_actions': [
                    "Add more interactive elements",
                    "Include questions and conversation starters",
                    "Enhance humor and personality"
                ]
            })
        
        return recommendations

    def _calculate_test_confidence(self, results: Dict) -> float:
        """Calculate statistical confidence for A/B test (simplified)"""
        total_impressions = sum(data['impressions'] for data in results.values())
        
        if total_impressions < 100:
            return 0.3  # Low confidence
        elif total_impressions < 500:
            return 0.7  # Medium confidence
        else:
            return 0.9  # High confidence

    def _generate_test_recommendation(self, winning_variant: str, winning_rate: float, 
                                    confidence: float, experiment: Dict) -> str:
        """Generate recommendation based on A/B test results"""
        if confidence < 0.5:
            return f"Continue testing - insufficient data for confident decision"
        elif confidence < 0.8:
            return f"Tentative winner: {winning_variant} (conversion rate: {winning_rate:.1%}) - continue testing for higher confidence"
        else:
            return f"Clear winner: {winning_variant} (conversion rate: {winning_rate:.1%}) - implement this variant"

    def _apply_character_learning(self, character: str) -> List[str]:
        """Apply learned improvements for a specific character"""
        updates = []
        
        performance = self._calculate_character_performance(character)
        
        # Generate recommendations based on performance
        if performance['overall_score'] < 6.0:
            recommendations = self._generate_character_recommendations(character)
            if recommendations:
                updates.append(f"Generated {len(recommendations)} improvement recommendations for {character}")
            
            # Log performance insights
            insights = self._analyze_performance_trends(character)
            if insights:
                updates.append(f"Analyzed performance trends for {character}: {len(insights)} insights")
        
        return updates

    def _enhance_prompt_with_learning(self, original_prompt: str, character: str) -> str:
        """Enhance prompt based on learning data"""
        # This would contain actual learning logic
        # For now, adding basic enhancements
        enhancements = {
            'peter': " Make sure to include Peter's characteristic energy and random references.",
            'brian': " Emphasize Brian's intellectual nature and cultural sophistication.",
            'stewie': " Highlight Stewie's superior intellect and sophisticated vocabulary."
        }
        
        return original_prompt + enhancements.get(character, "")

    def _update_global_optimizations(self):
        """Update global optimization settings"""
        # This would update global optimization parameters
        logger.info("Global optimizations updated based on learning data")

    def _get_variation_prompts(self, character: str) -> List[str]:
        """Get randomization prompts to prevent identical responses"""
        variations = {
            'peter': [
                "Try a slightly different approach to your response.",
                "Vary your word choice and phrasing this time.",
                "Express yourself with a fresh perspective.",
                "Use different examples or references.",
                "Mix up your typical response pattern.",
                "Add some spontaneity to your reply.",
                "Approach this topic from a new angle."
            ],
            'brian': [
                "Employ different intellectual references this time.",
                "Vary your sophisticated vocabulary choices.", 
                "Use alternative cultural or literary examples.",
                "Express your thoughts with varied eloquence.",
                "Try different philosophical angles.",
                "Mix up your typical intellectual patterns.",
                "Approach with fresh analytical perspective."
            ],
            'stewie': [
                "Employ different condescending phrases this time.",
                "Vary your vocabulary of superiority.",
                "Use alternative expressions of intellectual dominance.",
                "Try different British phrases or references.",
                "Mix up your patterns of dramatic flair.",
                "Express disdain with fresh terminology.",
                "Approach with varied sophisticated mockery."
            ]
        }
        
        return variations.get(character, [
            "Try expressing this differently.",
            "Vary your approach this time.",
            "Use alternative phrasing."
        ])

    def _generate_retry_guidance(self, character: str, most_common_issue: str, failed_attempts: List[Dict]) -> str:
        """Generate specific guidance to address the most common failure pattern"""
        
        # Character-specific guidance for common issues
        character_guidance = {
            'peter': {
                'too_intellectual': "Keep it simple and childish like Peter - use basic words and silly observations",
                'too_serious': "Add Peter's childlike humor and random tangents about food or TV",
                'out_of_character': "Remember Peter is impulsive, loves food/beer, and makes random observations",
                'too_long': "Keep it short like Peter - he doesn't think deeply, just reacts",
                'repetitive': "Try a different Peter reaction - maybe reference food, TV, or family instead"
            },
            'brian': {
                'too_simple': "Add Brian's intellectual vocabulary and cultural references",
                'missing_pretension': "Include Brian's condescending tone and sophisticated observations",
                'out_of_character': "Remember Brian is pretentious, political, and likes to show off his intelligence",
                'too_long': "Keep Brian concise but intellectual - he's smart but not windy",
                'repetitive': "Try a different Brian angle - politics, culture, or correcting someone instead"
            },
            'stewie': {
                'not_sophisticated': "Use Stewie's advanced vocabulary and dramatic flair",
                'missing_evil_genius': "Add Stewie's condescending and slightly sinister tone",
                'out_of_character': "Remember Stewie is a sophisticated baby with evil genius tendencies",
                'too_casual': "Make it more formal and dramatic like Stewie's speech patterns",
                'repetitive': "Try a different Stewie approach - maybe world domination plans or condescending remarks"
            }
        }
        
        guidance = character_guidance.get(character, {}).get(most_common_issue)
        if guidance:
            return guidance
        
        # Generic guidance based on issue type
        generic_guidance = {
            'too_long': "Keep responses shorter and more conversational",
            'repetitive': "Try a completely different approach or angle",
            'out_of_character': f"Stay true to {character.title()}'s personality and speech patterns",
            'poor_flow': "Make the response feel more natural and conversational",
            'low_engagement': "Add more personality and character-specific humor"
        }
        
        return generic_guidance.get(most_common_issue, "Try a different approach to better match the character")

    def _generate_enhanced_retry_guidance(self, character: str, failed_attempts: List[Dict], rag_context: str = None) -> str:
        """Generate enhanced retry guidance using failed attempts analysis and RAG context"""
        
        # Analyze common failure patterns (original logic)
        common_issues = []
        for attempt in failed_attempts:
            issues = attempt.get('issues', [])
            common_issues.extend(issues)
        
        if not common_issues:
            return self._generate_retry_guidance(character, "general", failed_attempts)
        
        # Find most common issue
        issue_counts = {}
        for issue in common_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        most_common_issue = max(issue_counts, key=issue_counts.get)
        
        # Get base guidance
        base_guidance = self._generate_retry_guidance(character, most_common_issue, failed_attempts)
        
        # Enhance with RAG context if available
        if rag_context:
            try:
                # Use RAG context to provide specific examples
                rag_enhancement = f"Use examples from this context: {rag_context[:200]}"
                enhanced_guidance = f"{base_guidance} | {rag_enhancement}"
                return enhanced_guidance
            except Exception as e:
                logger.warning(f"Error enhancing retry guidance with RAG: {e}")
        
        return base_guidance

    def _get_emotion_enhancement_with_rag(self, character: str, emotion: str) -> str:
        """Generate emotion-based enhancement with RAG support"""
        
        # Get base emotion enhancement
        base_enhancement = self._get_emotion_enhancement(character, emotion)
        
        # Try to get RAG examples for emotion
        try:
            emotion_query = f"{character} Griffin {emotion} emotional response"
            rag_context = self._get_rag_context(character, emotion_query)
            
            if rag_context:
                rag_snippet = rag_context[:150].strip()
                enhanced = f"{base_enhancement} | EXAMPLE STYLE: {rag_snippet}"
                return enhanced
            
        except Exception as e:
            logger.warning(f"Error enhancing emotion with RAG for {character}: {e}")
        
        return base_enhancement

    def _get_topic_enhancement_with_rag(self, character: str, topic: str) -> str:
        """Generate topic-based enhancement with RAG support"""
        
        # Get base topic enhancement
        base_enhancement = self._get_topic_enhancement(character, topic)
        
        # Try to get RAG examples for topic
        try:
            topic_query = f"{character} Griffin talking about {topic}"
            rag_context = self._get_rag_context(character, topic_query)
            
            if rag_context:
                rag_snippet = rag_context[:150].strip()
                enhanced = f"{base_enhancement} | REFERENCE STYLE: {rag_snippet}"
                return enhanced
            
        except Exception as e:
            logger.warning(f"Error enhancing topic with RAG for {character}: {e}")
        
        return base_enhancement

    def _generate_context_addition_with_rag(self, character: str, conversation_context: Dict) -> str:
        """Generate context-aware additions with RAG support"""
        
        # Get base context addition
        base_addition = self._generate_context_addition(character, conversation_context)
        
        # Try to get RAG examples for conversation flow
        try:
            recent_topics = conversation_context.get('recent_topics', [])
            if recent_topics:
                flow_query = f"{character} Griffin conversation about {' '.join(recent_topics[-2:])}"
                rag_context = self._get_rag_context(character, flow_query)
                
                if rag_context:
                    rag_snippet = rag_context[:120].strip()
                    enhanced = f"{base_addition} | CONVERSATION FLOW: {rag_snippet}"
                    return enhanced
            
        except Exception as e:
            logger.warning(f"Error enhancing context with RAG for {character}: {e}")
        
        return base_addition

    def _get_organic_response_enhancement_with_rag(self, character: str, conversation_context: Dict) -> str:
        """Generate organic response enhancement with RAG support"""
        
        # Get base organic enhancement
        base_enhancement = self._get_organic_response_enhancement(character, conversation_context)
        
        # Try to get RAG examples for organic responses
        try:
            previous_speaker = conversation_context.get('previous_speaker', '')
            if previous_speaker:
                organic_query = f"{character} Griffin interrupting {previous_speaker} organic response"
                rag_context = self._get_rag_context(character, organic_query)
                
                if rag_context:
                    rag_snippet = rag_context[:130].strip()
                    enhanced = f"{base_enhancement} | ORGANIC EXAMPLE: {rag_snippet}"
                    return enhanced
            
        except Exception as e:
            logger.warning(f"Error enhancing organic response with RAG for {character}: {e}")
        
        return base_enhancement

    def _get_conversation_variety_enhancement(self, character: str, conversation_length: int) -> str:
        """Get conversation variety enhancement using RAG examples"""
        
        try:
            # Query for variety examples
            variety_query = f"{character} Griffin different response styles variety"
            rag_context = self._get_rag_context(character, variety_query)
            
            if rag_context:
                rag_snippet = rag_context[:200].strip()
                return f"CONVERSATION VARIETY: Vary your response style to avoid repetition. Examples: {rag_snippet}"
            else:
                # Fallback to basic variety guidance
                return "CONVERSATION FLOW: Vary your response style and avoid repeating previous patterns from this conversation"
            
        except Exception as e:
            logger.warning(f"Error getting variety enhancement for {character}: {e}")
            return "CONVERSATION FLOW: Vary your response style and avoid repeating previous patterns from this conversation"

    def _generate_quality_optimization_with_rag(self, character: str, performance_data: Dict) -> str:
        """Generate quality optimization with RAG examples"""
        
        # Get base quality optimization
        base_optimization = self._generate_quality_optimization(character, performance_data)
        
        # Try to get RAG examples for high-quality responses
        try:
            avg_quality = performance_data.get('average_quality', 85)
            
            if avg_quality < 75:
                # Get examples of high-quality responses
                quality_query = f"{character} Griffin high quality authentic response"
                rag_context = self._get_rag_context(character, quality_query)
                
                if rag_context:
                    rag_snippet = rag_context[:150].strip()
                    enhanced = f"{base_optimization} | QUALITY EXAMPLE: {rag_snippet}"
                    return enhanced
            
        except Exception as e:
            logger.warning(f"Error enhancing quality optimization with RAG for {character}: {e}")
        
        return base_optimization

    def _get_organic_response_enhancement(self, character: str, conversation_context: Dict) -> str:
        """Generate specific enhancements for organic responses (base version)"""
        
        previous_speaker = conversation_context.get('previous_speaker', '')
        
        # Character-specific organic response patterns
        organic_patterns = {
            'peter': {
                'interrupt_style': "Jump in with a random observation or food-related comment",
                'reaction_style': "React with simple excitement, confusion, or a random tangent",
                'relationship_dynamic': "Be casual and friendly, maybe interrupt with something silly"
            },
            'brian': {
                'interrupt_style': "Interject with an intellectual correction or cultural reference",
                'reaction_style': "Provide a sophisticated counterpoint or analysis",
                'relationship_dynamic': "Show intellectual superiority while being helpful"
            },
            'stewie': {
                'interrupt_style': "Dramatically interrupt with condescending observations",
                'reaction_style': "Make a sophisticated or slightly sinister comment",
                'relationship_dynamic': "Be condescending but engaged in the conversation"
            }
        }
        
        patterns = organic_patterns.get(character, {})
        
        enhancement_parts = []
        if patterns.get('interrupt_style'):
            enhancement_parts.append(f"ORGANIC STYLE: {patterns['interrupt_style']}")
        
        if patterns.get('reaction_style'):
            enhancement_parts.append(f"NATURAL REACTION: {patterns['reaction_style']}")
        
        # Add speaker-specific dynamics
        if previous_speaker and previous_speaker != character:
            enhancement_parts.append(f"RESPONDING TO {previous_speaker.upper()}: React naturally to what they just said")
        
        return " | ".join(enhancement_parts) if enhancement_parts else ""

    def _get_recent_character_performance(self, character: str) -> Dict:
        """Get recent performance data for the character"""
        
        # For now, return recent performance from our tracking
        recent_responses = []
        for response_data in list(self.response_performance[character])[-10:]:  # Last 10 responses
            recent_responses.append(response_data)
        
        if not recent_responses:
            return {}
        
        # Calculate averages
        avg_quality = sum(r.get('quality_score', 0) for r in recent_responses) / len(recent_responses)
        avg_engagement = sum(r.get('engagement_score', 0) for r in recent_responses) / len(recent_responses)
        
        # Count recent failures
        recent_failures = sum(1 for r in recent_responses if not r.get('quality_passed', True))
        
        return {
            'average_quality': avg_quality,
            'average_engagement': avg_engagement,
            'recent_failures': recent_failures,
            'total_recent_responses': len(recent_responses),
            'failure_rate': recent_failures / len(recent_responses) if recent_responses else 0
        }

    def _generate_quality_optimization(self, character: str, performance_data: Dict) -> str:
        """Generate quality-focused optimizations based on recent performance (base version)"""
        
        avg_quality = performance_data.get('average_quality', 85)
        failure_rate = performance_data.get('failure_rate', 0)
        
        optimizations = []
        
        # Quality-based optimizations
        if avg_quality < 75:
            optimizations.append(f"QUALITY FOCUS: Recent responses averaged {avg_quality:.1f}% - focus on character authenticity and engagement")
        
        if failure_rate > 0.3:  # More than 30% failure rate
            optimizations.append(f"RELIABILITY FOCUS: {failure_rate*100:.0f}% recent failures - prioritize character consistency and natural flow")
        
        # Character-specific quality tips
        character_quality_tips = {
            'peter': "Ensure childlike simplicity and authentic Peter vocabulary",
            'brian': "Maintain intellectual tone without being overly verbose",
            'stewie': "Keep sophisticated vocabulary while staying conversational"
        }
        
        if character in character_quality_tips:
            optimizations.append(f"CHARACTER QUALITY: {character_quality_tips[character]}")
        
        return " | ".join(optimizations) if optimizations else ""

    def _should_trigger_optimization(self, character: str) -> bool:
        """Determine if optimization should be triggered based on recent performance"""
        
        character_responses = self.response_performance[character]
        if len(character_responses) < 5:  # Need minimum data
            return False
        
        # Analyze recent performance (last 10 responses)
        recent_responses = character_responses[-10:]
        
        quality_scores = [r.get('quality_score', 0) for r in recent_responses]
        quality_passes = [r.get('quality_passed', True) for r in recent_responses]
        
        if not quality_scores:
            return False
        
        # Calculate metrics
        avg_quality = sum(quality_scores) / len(quality_scores)
        pass_rate = sum(quality_passes) / len(quality_passes)
        recent_failures = sum(1 for passed in quality_passes if not passed)
        
        # Trigger optimization if:
        # 1. Average quality is below 75%
        # 2. Pass rate is below 80%
        # 3. More than 3 failures in last 10 responses
        should_optimize = (
            avg_quality < 75 or 
            pass_rate < 0.8 or 
            recent_failures > 3
        )
        
        if should_optimize:
            logger.info(f"🎯 Optimization trigger for {character}: avg_quality={avg_quality:.1f}, pass_rate={pass_rate:.1f}, failures={recent_failures}")
        
        return should_optimize

    def _get_enhanced_rag_context(self, character: str, context: Dict, retry_optimization: bool = False) -> str:
        """Get enhanced RAG context based on character, topic, and optimization needs"""
        try:
            # Build a comprehensive query for RAG retrieval
            query_parts = []
            
            # Character-specific query base
            query_parts.append(f"{character} Griffin")
            
            # Add topic if available
            topic = context.get('topic', '')
            if topic and topic != 'general':
                query_parts.append(topic)
            
            # Add conversation context
            conversation_context = context.get('conversation_context', {})
            recent_topics = conversation_context.get('recent_topics', [])
            if recent_topics:
                query_parts.extend(recent_topics[-2:])  # Last 2 topics
            
            # Add retry-specific context if needed
            if retry_optimization:
                query_parts.append("examples")
                query_parts.append("good responses")
            
            # Add emotion context
            emotion = context.get('emotion')
            if emotion and emotion != 'neutral':
                query_parts.append(emotion)
            
            # Create the query
            rag_query = " ".join(query_parts[:5])  # Limit to avoid too long queries
            
            # Make request to RAG retriever with enhanced context
            response = requests.post(
                f"{RAG_RETRIEVER_URL}/retrieve",
                json={
                    "query": rag_query, 
                    "num_results": 3,
                    "character_filter": character  # If supported by RAG service
                },
                timeout=8
            )
            
            if response.status_code == 200:
                data = response.json()
                rag_context = data.get("context", "")
                if rag_context:
                    # Truncate and clean up for prompt use
                    cleaned_context = rag_context[:400].strip()
                    if len(rag_context) > 400:
                        cleaned_context += "..."
                    
                    logger.info(f"🔍 Fine-tuning: Retrieved RAG context for query: {rag_query}")
                    return cleaned_context
            
            # Fallback to character-specific RAG if main query fails
            return self._get_rag_context(character, rag_query)
            
        except Exception as e:
            logger.warning(f"Enhanced RAG retrieval failed for {character}: {e}")
            # Fallback to basic RAG
            return self._get_rag_context(character)

    def _generate_config_based_enhancements(self, character: str, character_config: Dict, context: Dict) -> List[str]:
        """Generate enhancements based on character configuration from character-config service"""
        enhancements = []
        
        try:
            # Extract useful config elements
            llm_settings = character_config.get('llm_settings', {})
            character_traits = character_config.get('character_traits', {})
            speaking_style = character_config.get('speaking_style', {})
            
            # Temperature-based enhancements
            temperature = llm_settings.get('temperature', 0.7)
            if temperature < 0.5:
                enhancements.append("CONSISTENCY FOCUS: Maintain very consistent character voice and responses")
            elif temperature > 0.8:
                enhancements.append("CREATIVITY BOOST: Feel free to be more creative and spontaneous in your response")
            
            # Max tokens guidance
            max_tokens = llm_settings.get('max_tokens', 150)
            if max_tokens < 100:
                enhancements.append("BREVITY: Keep responses short and punchy")
            elif max_tokens > 200:
                enhancements.append("ELABORATION: You can provide more detailed and elaborate responses")
            
            # Character traits integration
            if character_traits:
                if character_traits.get('humor_level', 0) > 0.8:
                    enhancements.append("HUMOR EMPHASIS: Prioritize humor and comedic timing in your response")
                if character_traits.get('intelligence_level', 0) > 0.8:
                    enhancements.append("INTELLIGENCE SHOWCASE: Feel free to display your character's intelligence")
                if character_traits.get('aggression_level', 0) > 0.6:
                    enhancements.append("ASSERTIVENESS: Be more direct and assertive in your communication")
            
            # Speaking style enhancements
            if speaking_style:
                vocabulary_level = speaking_style.get('vocabulary_level', 'normal')
                if vocabulary_level == 'simple':
                    enhancements.append("SIMPLE LANGUAGE: Use simple, everyday language")
                elif vocabulary_level == 'sophisticated':
                    enhancements.append("SOPHISTICATED VOCABULARY: Use more advanced and refined language")
                
                pace = speaking_style.get('pace', 'normal')
                if pace == 'fast':
                    enhancements.append("ENERGETIC PACE: Respond with energy and quick-paced dialogue")
                elif pace == 'slow':
                    enhancements.append("THOUGHTFUL PACE: Take your time with more deliberate responses")
            
            if enhancements:
                logger.info(f"🔧 Fine-tuning: Added {len(enhancements)} config-based enhancements for {character}")
            
            return enhancements
            
        except Exception as e:
            logger.warning(f"Error generating config-based enhancements for {character}: {e}")
            return []

# Initialize service
fine_tuning_service = FineTuningService()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'fine-tuning',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/optimize-prompt', methods=['POST'])
def optimize_prompt():
    """Optimize prompt based on context and performance"""
    try:
        data = request.get_json()
        
        if not data or 'character' not in data:
            return jsonify({'error': 'Missing character field'}), 400
        
        character = data['character']
        context = data.get('context', {})
        performance_feedback = data.get('performance_feedback')
        
        result = fine_tuning_service.optimize_prompt(character, context, performance_feedback)
        
        logger.info(f"Prompt optimized for {character}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error optimizing prompt: {str(e)}")
        return jsonify({'error': f'Prompt optimization failed: {str(e)}'}), 500

@app.route('/record-performance', methods=['POST'])
def record_performance():
    """Record response performance metrics for learning"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['response_id', 'character', 'metrics']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {missing_fields}'}), 400
        
        response_id = data['response_id']
        character = data['character']
        metrics = data['metrics']
        user_feedback = data.get('user_feedback', 'neutral')
        feedback_details = data.get('feedback_details', '')
        response_text = data.get('response_text', '')
        user_input = data.get('user_input', '')
        conversation_context = data.get('conversation_context', [])
        
        # Record comprehensive performance data
        performance_record = {
            'response_id': response_id,
            'character': character,
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics,
            'user_feedback': user_feedback,
            'feedback_details': feedback_details,
            'response_text': response_text[:500],  # Truncate for storage
            'user_input': user_input[:200],
            'conversation_context': conversation_context,
            'quality_passed': metrics.get('quality_passed', True),
            'quality_score': metrics.get('quality_score', 0)
        }
        
        # Store in character-specific performance tracking
        fine_tuning_service.response_performance[character].append(performance_record)
        
        # Keep only recent records (last 100 per character)
        if len(fine_tuning_service.response_performance[character]) > 100:
            fine_tuning_service.response_performance[character] = \
                fine_tuning_service.response_performance[character][-100:]
        
        # Update optimization metrics
        quality_score = metrics.get('quality_score', 0)
        quality_passed = metrics.get('quality_passed', True)
        
        fine_tuning_service.optimization_metrics['response_quality'].append(quality_score)
        
        # Calculate engagement score based on various factors
        engagement_score = 0
        if quality_passed:
            engagement_score += 50
        if quality_score > 80:
            engagement_score += 30
        if 'organic' in user_feedback:
            engagement_score += 20
        
        fine_tuning_service.optimization_metrics['user_engagement'].append(engagement_score)
        
        # Calculate character authenticity score
        authenticity_score = metrics.get('authenticity_score', quality_score)
        fine_tuning_service.optimization_metrics['character_authenticity'].append(authenticity_score)
        
        # Keep metrics lists manageable
        for metric_name in fine_tuning_service.optimization_metrics:
            if len(fine_tuning_service.optimization_metrics[metric_name]) > 1000:
                fine_tuning_service.optimization_metrics[metric_name] = \
                    fine_tuning_service.optimization_metrics[metric_name][-1000:]
        
        logger.info(f"📊 Fine-tuning: Recorded performance for {character} - Quality: {quality_score}, Passed: {quality_passed}")
        
        # Analyze if we should trigger optimization
        should_optimize = fine_tuning_service._should_trigger_optimization(character)
        
        result = {
            'status': 'success',
            'recorded': True,
            'character': character,
            'quality_score': quality_score,
            'quality_passed': quality_passed,
            'should_optimize': should_optimize,
            'timestamp': datetime.now().isoformat()
        }
        
        if should_optimize:
            logger.info(f"🎯 Fine-tuning: Performance data suggests optimization needed for {character}")
            result['optimization_suggested'] = True
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error recording performance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/performance-stats', methods=['GET'])
def get_performance_stats():
    """Get performance statistics for analysis"""
    try:
        character = request.args.get('character')
        
        if character:
            # Character-specific stats
            character_responses = fine_tuning_service.response_performance[character]
            if not character_responses:
                return jsonify({'error': f'No performance data for {character}'}), 404
            
            # Calculate character-specific metrics
            recent_responses = character_responses[-20:]  # Last 20 responses
            quality_scores = [r['quality_score'] for r in recent_responses if 'quality_score' in r]
            quality_passes = [r['quality_passed'] for r in recent_responses if 'quality_passed' in r]
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            pass_rate = sum(quality_passes) / len(quality_passes) if quality_passes else 0
            
            return jsonify({
                'character': character,
                'total_responses': len(character_responses),
                'recent_responses': len(recent_responses),
                'average_quality_score': round(avg_quality, 2),
                'quality_pass_rate': round(pass_rate * 100, 1),
                'optimization_suggested': avg_quality < 75 or pass_rate < 0.8
            }), 200
        
        else:
            # Overall stats
            all_stats = {}
            for char in fine_tuning_service.response_performance:
                responses = fine_tuning_service.response_performance[char]
                if responses:
                    recent = responses[-10:]
                    quality_scores = [r['quality_score'] for r in recent if 'quality_score' in r]
                    quality_passes = [r['quality_passed'] for r in recent if 'quality_passed' in r]
                    
                    all_stats[char] = {
                        'total_responses': len(responses),
                        'recent_avg_quality': round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0,
                        'recent_pass_rate': round(sum(quality_passes) / len(quality_passes) * 100, 1) if quality_passes else 0
                    }
            
            return jsonify({
                'overall_stats': all_stats,
                'total_characters_tracked': len(all_stats),
                'timestamp': datetime.now().isoformat()
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/ab-test/create', methods=['POST'])
def create_ab_test():
    """Create new A/B testing experiment"""
    try:
        data = request.get_json()
        
        if not data or 'experiment_name' not in data or 'variants' not in data:
            return jsonify({'error': 'Missing experiment_name or variants'}), 400
        
        experiment_name = data['experiment_name']
        variants = data['variants']
        traffic_split = data.get('traffic_split')
        
        result = fine_tuning_service.create_ab_experiment(experiment_name, variants, traffic_split)
        
        logger.info(f"A/B test created: {experiment_name}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error creating A/B test: {str(e)}")
        return jsonify({'error': f'A/B test creation failed: {str(e)}'}), 500

@app.route('/ab-test/variant', methods=['GET'])
def get_ab_variant():
    """Get variant assignment for A/B test"""
    try:
        experiment_name = request.args.get('experiment')
        user_id = request.args.get('user_id')
        
        if not experiment_name:
            return jsonify({'error': 'Missing experiment parameter'}), 400
        
        result = fine_tuning_service.get_experiment_variant(experiment_name, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting A/B variant: {str(e)}")
        return jsonify({'error': f'Variant assignment failed: {str(e)}'}), 500

@app.route('/ab-test/analyze', methods=['GET'])
def analyze_ab_test():
    """Analyze A/B test results"""
    try:
        experiment_name = request.args.get('experiment')
        
        if not experiment_name:
            return jsonify({'error': 'Missing experiment parameter'}), 400
        
        result = fine_tuning_service.run_ab_test_analysis(experiment_name)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error analyzing A/B test: {str(e)}")
        return jsonify({'error': f'A/B test analysis failed: {str(e)}'}), 500

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    """Get optimization recommendations"""
    try:
        character = request.args.get('character')
        
        result = fine_tuning_service.get_optimization_recommendations(character)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return jsonify({'error': f'Recommendations failed: {str(e)}'}), 500

@app.route('/apply-learning', methods=['POST'])
def apply_learning():
    """Apply learned optimizations"""
    try:
        data = request.get_json()
        character = data.get('character') if data else None
        
        result = fine_tuning_service.apply_learning_updates(character)
        
        logger.info(f"Learning applied for {character or 'all characters'}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error applying learning: {str(e)}")
        return jsonify({'error': f'Learning application failed: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.getenv('FINE_TUNING_PORT', 6004))
    app.run(host='0.0.0.0', port=port, debug=False) 