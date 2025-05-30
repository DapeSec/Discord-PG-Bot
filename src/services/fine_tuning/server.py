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
        """Get dynamic RAG context to add variety to prompts"""
        try:
            # Create character-specific queries for RAG retrieval
            if not query:
                query_options = {
                    'peter': ["Peter Griffin funny moments", "Peter Griffin at work", "Peter Griffin family", "Peter Griffin jokes"],
                    'brian': ["Brian Griffin intellectual", "Brian Griffin writing", "Brian Griffin culture", "Brian Griffin politics"], 
                    'stewie': ["Stewie Griffin genius", "Stewie Griffin inventions", "Stewie Griffin evil plans", "Stewie Griffin British"]
                }
                
                character_queries = query_options.get(character, [f"{character} Griffin"])
                query = random.choice(character_queries)
            
            # Make request to RAG retriever
            response = requests.post(
                f"{RAG_RETRIEVER_URL}/retrieve",
                json={"query": query, "num_results": 2},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                rag_context = data.get("context", "")
                if rag_context:
                    # Truncate to reasonable length for prompt
                    return rag_context[:300] + "..." if len(rag_context) > 300 else rag_context
            
            logger.warning(f"RAG retrieval failed for {character}: {response.status_code}")
            return ""
            
        except Exception as e:
            logger.warning(f"Error fetching RAG context for {character}: {e}")
            return ""

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
        """Generate optimized prompt based on context and performance"""
        
        # Get current base prompt from character-config service
        base_prompt = self._get_base_prompt(character)
        if not base_prompt:
            return {'error': f'Unable to fetch configuration for character: {character}'}
        
        # Analyze context to determine optimizations
        message_topic = context.get('topic', 'general')
        user_emotion = context.get('emotion')
        conversation_context = context.get('conversation_context', {})
        
        # Start with the current character prompt
        optimized_prompt = base_prompt
        
        # Add context-based enhancements
        context_additions = []
        
        if user_emotion and user_emotion != 'neutral':
            emotion_enhancement = self._get_emotion_enhancement(character, user_emotion)
            if emotion_enhancement:
                context_additions.append(emotion_enhancement)
        
        if message_topic != 'general':
            topic_enhancement = self._get_topic_enhancement(character, message_topic)
            if topic_enhancement:
                context_additions.append(topic_enhancement)
        
        # Add performance-based optimizations
        if performance_feedback:
            performance_optimizations = self._generate_prompt_optimizations(character, performance_feedback)
            if performance_optimizations:
                context_additions.append(performance_optimizations)
        
        # Add conversation context if available
        if conversation_context.get('recent_topics'):
            context_addition = self._generate_context_addition(character, conversation_context)
            if context_addition:
                context_additions.append(context_addition)
        
        # ADD DYNAMIC RAG CONTEXT TO PREVENT IDENTICAL RESPONSES
        rag_context = self._get_rag_context(character)
        if rag_context:
            context_additions.append(f"Reference this for inspiration: {rag_context}")
        
        # Combine base prompt with additions
        if context_additions:
            optimized_prompt += "\n\nAdditional context: " + " ".join(context_additions)
        
        optimization_metadata = {
            'character': character,
            'base_prompt_source': 'character-config-service',
            'optimizations_applied': len(context_additions),
            'context_enhanced': bool(conversation_context),
            'rag_context_added': bool(rag_context),
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'optimized_prompt': optimized_prompt,
            'metadata': optimization_metadata,
            'confidence': self._calculate_optimization_confidence(context, performance_feedback)
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
    """Record response performance for learning"""
    try:
        data = request.get_json()
        
        required_fields = ['response_id', 'character', 'metrics']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': f'Missing required fields: {required_fields}'}), 400
        
        response_id = data['response_id']
        character = data['character']
        metrics = data['metrics']
        user_feedback = data.get('user_feedback')
        
        result = fine_tuning_service.record_response_performance(
            response_id, character, metrics, user_feedback
        )
        
        logger.info(f"Performance recorded for {character}: {response_id}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error recording performance: {str(e)}")
        return jsonify({'error': f'Performance recording failed: {str(e)}'}), 500

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