# Adaptive Quality Control System

## Overview

The Adaptive Quality Control System creates a natural correlation between conversation history richness and quality standards. As conversation history grows, both quality expectations and context weighting progressively adjust to maintain optimal response quality.

**Core Principle**: "More History = Higher Standards + Better Context Balance = Superior Quality"

## Key Components

### 1. Adaptive Quality Control
Progressive quality thresholds based on conversation richness:
- **Cold Start** (0-6 messages): 30/100 threshold - extremely lenient for first interactions
- **Warm Conversation** (7-20 messages): 60/100 threshold - moderate expectations with developing context
- **Hot Conversation** (21+ messages): 75/100 threshold - high standards with rich conversation history

### 2. Adaptive Context Weighting & Length Scaling
Progressive balance and volume adjustment between conversation history and RAG retrieval context:
- **Cold Start**: 60% conversation (2 messages), 40% RAG (400 chars) - need external context to enhance responses
- **Warm Conversation**: 75% conversation (4 messages), 25% RAG (250 chars) - balanced approach with moderate context
- **Hot Conversation**: 85% conversation (6 messages), 15% RAG (150 chars) - rich conversation history with minimal external context

### 3. Adaptive Anti-Hallucination Scaling
Progressive strictness measures that increase with conversation richness to combat higher hallucination risk:
- **Cold Start**: 450 char limit, 20% risk, 0.8x strictness - generous controls for sparse context
- **Warm Conversation**: 375 char limit, 50% risk, 1.2x strictness - moderate controls for developing context
- **Hot Conversation**: 325 char limit, 80% risk, 1.6x strictness - focused controls for rich context

## Configuration

### Adaptive Quality Control Variables
```bash
# Enable/disable adaptive quality control
ADAPTIVE_QUALITY_CONTROL_ENABLED=true

# Quality thresholds for different conversation stages
COLD_START_THRESHOLD=40.0
WARM_CONVERSATION_THRESHOLD=60.0  
HOT_CONVERSATION_THRESHOLD=75.0

# Message count thresholds for conversation stages
CONVERSATION_HISTORY_COLD_LIMIT=6
CONVERSATION_HISTORY_WARM_LIMIT=20
```

### Adaptive Context Weighting & Length Variables
```bash
# Enable/disable adaptive context weighting and length scaling
ADAPTIVE_CONTEXT_WEIGHTING_ENABLED=true

# Context weight ratios for different conversation stages
COLD_START_CONVERSATION_WEIGHT=0.60      # 60% conversation, 40% RAG
WARM_CONVERSATION_WEIGHT=0.75            # 75% conversation, 25% RAG  
HOT_CONVERSATION_WEIGHT=0.85             # 85% conversation, 15% RAG

# Adaptive conversation message counts
COLD_START_CONVERSATION_MESSAGES=2       # Minimal conversation context
WARM_CONVERSATION_MESSAGES=4             # Moderate conversation context
HOT_CONVERSATION_MESSAGES=6              # Rich conversation context

# Adaptive RAG context character limits
COLD_START_RAG_CONTEXT_LENGTH=400        # More RAG context needed
WARM_CONVERSATION_RAG_CONTEXT_LENGTH=250 # Moderate RAG context
HOT_CONVERSATION_RAG_CONTEXT_LENGTH=150  # Minimal RAG context

# Adaptive anti-hallucination measures
ADAPTIVE_ANTI_HALLUCINATION_ENABLED=true

# Response length limits that scale with conversation state
COLD_START_MAX_RESPONSE_LENGTH=450       # More generous for cold starts
WARM_CONVERSATION_MAX_RESPONSE_LENGTH=375 # Moderate length
HOT_CONVERSATION_MAX_RESPONSE_LENGTH=325  # Shorter, focused responses

# Hallucination risk factors (increase with conversation length)
COLD_START_HALLUCINATION_RISK=0.2        # 20% risk - very low for sparse context
WARM_CONVERSATION_HALLUCINATION_RISK=0.5 # 50% risk - moderate context
HOT_CONVERSATION_HALLUCINATION_RISK=0.8  # 80% risk - rich context

# Strictness multipliers for anti-hallucination measures
COLD_START_STRICTNESS_MULTIPLIER=0.8     # More lenient for cold starts
WARM_CONVERSATION_STRICTNESS_MULTIPLIER=1.2 # 20% stricter
HOT_CONVERSATION_STRICTNESS_MULTIPLIER=1.6  # 60% stricter
```

## How It Works

### Context Analysis
The system analyzes conversation richness using multiple factors:
- **Message Count**: Total meaningful messages in conversation
- **Message Quality**: Length and substance of individual messages
- **Topic Continuity**: Connecting words indicating flowing conversation
- **Character Diversity**: Number of different speakers participating
- **Database History**: Recent channel history (last 24 hours)

### Progressive Adjustment
As conversation develops:

1. **Quality Standards Rise**: From lenient (50/100) to demanding (75/100)
2. **Context Balance Shifts**: From RAG-heavy (40%) to conversation-focused (15% RAG)
3. **Context Volume Scales**: More conversation messages (2→6), fewer RAG characters (400→150)
4. **Anti-Hallucination Intensifies**: Stricter response limits (300→200 chars) and controls (1.0x→1.6x)
5. **Input Structure Adapts**: Richer conversation context, minimal external information, explicit warnings
6. **Assessment Criteria Evolve**: Higher expectations for character accuracy and flow

### Input Structure Examples

**Cold Start (60% conversation, 40% RAG - 2 messages, 400 chars, 400 max response)**:
```
RESPOND NATURALLY: You may respond up to 400 characters. VERY LOW HALLUCINATION RISK (20%) - feel free to use background context and respond in character.

RESPOND TO THE CONVERSATION: [last 2 conversation messages]
Original input: [user message]
Helpful background context (use to enhance response): [up to 400 chars RAG context]
```

**Warm Conversation (75% conversation, 25% RAG - 4 messages, 250 chars, 300 max response)**:
```
IMPORTANT: Keep response under 300 characters. MODERATE HALLUCINATION RISK (50%) - stay focused on conversation topics.

RESPOND TO THE CONVERSATION: [last 4 conversation messages - richer context]
Original input: [user message]  
Background context (use moderately): [up to 250 chars RAG context]
```

**Hot Conversation (85% conversation, 15% RAG - 6 messages, 150 chars, 250 max response)**:
```
CRITICAL: Keep response under 250 characters. HIGH HALLUCINATION RISK (80%) - stick strictly to conversation facts. Do not elaborate beyond what's directly discussed.

RESPOND TO THE CONVERSATION (primary focus): [last 6 conversation messages - rich context]
Original input: [user message]
Minimal background context (reference only): [up to 150 chars RAG context]
```

## Benefits

### 1. Natural Progression
- **Early Interactions**: System provides helpful external context when conversation history is sparse
- **Developing Conversations**: Balanced approach as context builds
- **Rich Conversations**: Focus on conversation flow with minimal external interference

### 2. Quality Alignment
- **Consistent Standards**: Quality expectations match available context richness
- **No Cold Start Penalties**: Lenient thresholds when context is limited
- **High Standards When Warranted**: Demanding quality when rich context is available

### 3. Context Optimization
- **Efficient Resource Use**: More conversation messages when valuable, fewer RAG characters when not needed
- **Reduced Hallucination Risk**: Less external context in rich conversations reduces over-elaboration
- **Enhanced Relevance**: Progressive focus on conversation flow over external knowledge
- **Volume Scaling**: Context amounts scale naturally with conversation richness

### 4. Character Authenticity
- **Natural Development**: Characters can build on conversation history progressively
- **Contextual Responses**: Appropriate balance of knowledge vs conversation awareness
- **Consistent Personality**: Quality standards ensure character accuracy at all stages

### 5. Retry-Based Length Validation
- **No Truncation**: Responses exceeding adaptive length limits trigger regeneration instead of truncation
- **Length-Specific Prompts**: Retry attempts use targeted prompts for length issues ("Keep it much shorter and more concise")
- **Quality Preservation**: Maintains response quality while ensuring appropriate length
- **Progressive Guidance**: Different retry strategies for different conversation states

### 6. Character-Aware Anti-Hallucination
- **Personality-Based Adjustments**: Different characters get different anti-hallucination settings based on their natural response patterns
- **Peter Griffin**: Stricter length controls (0.7x), higher hallucination risk (1.2x), stricter validation (1.3x) - prevents rambling
- **Brian Griffin**: Conversational length (1.0x), lower risk (0.8x), lenient strictness (0.9x) - enables natural sarcasm and self-deprecation
- **Stewie Griffin**: Concise length (0.8x), lowest risk (0.6x), most lenient strictness (0.7x) - allows witty, cutting remarks
- **Natural Fallbacks**: Character-appropriate fallback responses instead of generic error messages
- **Conversational Prompts**: Updated character instructions emphasize natural conversation over formal academic language
- **Dynamic Character Guidance**: Context-aware prompts that encourage character-specific speech patterns and catchphrases

## Implementation Details

### Functions

#### `calculate_adaptive_quality_threshold(conversation_history, channel_id=None)`
Calculates dynamic quality thresholds based on conversation richness.

#### `calculate_adaptive_context_weights(conversation_history, channel_id=None, character_name=None)`
Determines progressive balance and volume scaling between conversation and RAG context. Now includes character-aware anti-hallucination adjustments.

#### `calculate_character_aware_anti_hallucination_settings(character_name, conversation_state, base_settings)`
Adjusts anti-hallucination settings based on character personality and conversation state. Different characters get different length limits, risk assessments, and strictness controls.

#### `get_conversation_context_value(conversation_history)`
Analyzes conversation richness for both quality and context decisions.

#### `_assess_conversation_flow_quality(character_name, response_text, conversation_context)`
Enhanced flow assessment that includes adaptive length validation. Penalizes responses exceeding adaptive limits and provides detailed feedback for retry guidance.

### Integration Points

1. **Response Generation**: `generate_character_response()` uses adaptive context weighting
2. **Quality Control**: `generate_character_response_with_quality_control()` uses adaptive thresholds and retry-based length validation
3. **Flow Assessment**: `_assess_conversation_flow_quality()` includes adaptive length validation with penalty scoring
4. **Retry Logic**: Length-specific retry prompts guide regeneration when responses exceed adaptive limits
5. **Orchestration**: `/orchestrate` endpoint passes channel_id for database history analysis

## Testing

Run comprehensive tests:
```bash
python scripts/test_adaptive_quality_control.py
python scripts/test_character_aware_anti_hallucination.py
```

**Primary Test Suite** (`test_adaptive_quality_control.py`):
- Threshold calculations for different conversation scenarios
- Context weight calculations and ranges
- Progressive adjustment behavior
- Integration with quality control system
- Environment variable configuration

**Character-Aware Test Suite** (`test_character_aware_anti_hallucination.py`):
- Character-specific anti-hallucination adjustments (Peter strict, Brian moderate, Stewie lenient)
- Integrated system testing with conversation history
- Natural fallback response validation
- Character modifier application testing

## Migration from Static System

### Before (Static System)
- Fixed 70/100 quality threshold regardless of context
- Fixed 75% conversation focus weight
- Static conversation context (3 messages) and RAG limit (200 chars)
- Same standards and context volumes for all conversation stages
- No correlation between context richness and expectations

### After (Adaptive System)
- Dynamic 50-75/100 quality thresholds based on conversation richness
- Progressive 60-85% conversation focus based on context value
- Adaptive context volumes: 2-6 conversation messages, 150-400 RAG characters
- Appropriate standards and context amounts for each conversation stage
- Natural correlation between available context, volume scaling, and quality expectations

### Backward Compatibility
- Set `ADAPTIVE_QUALITY_CONTROL_ENABLED=false` to use static thresholds
- Set `ADAPTIVE_CONTEXT_WEIGHTING_ENABLED=false` to use static conversation focus
- All existing functionality preserved when adaptive features disabled

## Monitoring

The system provides detailed logging:
- Adaptive threshold calculations and reasoning
- Context weight decisions and conversation analysis
- Quality assessment results with adaptive context
- Progressive adjustment tracking

Example log output:
```
🎯 Adaptive Quality Threshold: 52.3/100 (COLD_START)
   📊 Messages: 2, Context Score: 3.5, Modifier: +2.3

🎚️ Adaptive Context Weights: 62.1% conversation, 37.9% RAG (COLD_START)
📏 Adaptive Context Lengths: 2 conv messages, 380 RAG chars
   📊 Total Context: 2.0 messages, Quality Score: 3.5
   🔧 Modifiers: Weight +0.021, Conv +0 msgs, RAG -20 chars
```

This creates a cohesive system where quality standards and context weighting evolve together, ensuring optimal response quality at every stage of conversation development. 