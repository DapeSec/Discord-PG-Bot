# Enhanced Retry Context System

## Overview

The Enhanced Retry Context System is a significant improvement to the Discord bot's response generation that includes rejected responses and their specific failure reasons in retry attempts. This allows the LLM to learn from its mistakes and generate better responses more quickly.

## Problem Solved

**Previous Behavior**: When a response was rejected by quality control, validation, or duplicate detection, the system would simply retry with generic variation prompts like "Try a different approach" without providing context about what went wrong.

**Enhanced Behavior**: The system now includes the rejected response, failure score, specific issues, and targeted guidance in the retry context, enabling the LLM to understand exactly what needs to be improved.

## Key Features

### 1. Comprehensive Failure Context
- **Rejected Response**: The exact text that was rejected
- **Failure Score**: Numerical score showing how far below threshold it was
- **Specific Issues**: Detailed list of what was wrong (e.g., "Response too long", "Third person self-reference")
- **Threshold Information**: Shows adaptive threshold that wasn't met

### 2. Issue-Specific Guidance
Different types of failures receive targeted guidance:

#### Length Issues
- "Keep it much shorter and more concise"
- "Give a brief, natural response"
- "Respond with just a few words or a short sentence"

#### Third Person Issues
- "Speak in FIRST PERSON only - use 'I' not your character name"
- "Respond as yourself using 'I' statements, not third person"
- "Use first person perspective - 'I think' not 'Character thinks'"

#### Self-Addressing Issues
- "Respond naturally to the conversation, don't address other characters directly"
- "Engage with the conversation flow, avoid talking to specific people"
- "React to what was said without addressing anyone by name"

#### Repetitive Issues
- "Try a completely different response approach"
- "Use different words and phrasing entirely"
- "Take a fresh angle on the topic"

#### General Quality Issues
- "Try a different approach"
- "Be more conversational"
- "Keep it shorter and more natural"

### 3. Three Retry Types

#### Quality Control Retry
**Context Format**:
```
🔄 RETRY GUIDANCE: [specific guidance]

PREVIOUS ATTEMPT FAILED:
Rejected Response: "[exact rejected text]"
Score: [score]/100 (below [threshold] threshold)
Specific Issues: [comma-separated list of issues]
```

**Example**:
```
🔄 RETRY GUIDANCE: Speak in FIRST PERSON only - use 'I' not your character name

PREVIOUS ATTEMPT FAILED:
Rejected Response: "Brian thinks that's actually quite fascinating. Brian would like to add that..."
Score: 25.0/100 (below 50.0 threshold)
Specific Issues: Third person self-reference detected, Character addressing themselves
```

#### Validation Retry
**Context Format**:
```
🔄 VALIDATION RETRY: [character-specific instruction]

VALIDATION FAILED:
Rejected Response: "[exact rejected text]"
Reason: Character validation failed - likely third person, self-addressing, or inappropriate content
```

#### Duplicate Retry
**Context Format**:
```
🔄 DUPLICATE RETRY: Respond differently this time, use different words and approach

DUPLICATE DETECTED:
Rejected Response: "[exact rejected text]"
Reason: This response is too similar to a previous response in the conversation
```

## Implementation Details

### Quality Control Enhancement
Located in `generate_character_response_with_quality_control()` function:

```python
# 🎯 ENHANCED RETRY CONTEXT: Include rejected response and specific issues for learning
rejected_response_context = f"\n\nPREVIOUS ATTEMPT FAILED:\nRejected Response: \"{response_text}\"\nScore: {combined_score:.1f}/100 (below {adaptive_threshold:.1f} threshold)\nSpecific Issues: {', '.join(flow_assessment.get('issues', []))}"

# Issue-specific guidance selection
if length_issue:
    variation_prompts = ["Keep it much shorter and more concise", ...]
elif third_person_issue:
    variation_prompts = ["Speak in FIRST PERSON only - use 'I' not your character name", ...]
elif self_addressing_issue:
    variation_prompts = ["Respond naturally to the conversation, don't address other characters directly", ...]
# ... etc

# Create enhanced retry prompt
retry_guidance = variation_prompts[min(attempt, len(variation_prompts) - 1)]
enhanced_input = f"{input_text}\n\n🔄 RETRY GUIDANCE: {retry_guidance}{rejected_response_context}"
```

### Validation Enhancement
Located in `generate_character_response()` function:

```python
# 🎯 ENHANCED VALIDATION RETRY: Include failed response context for learning
validation_failure_context = f"\n\nVALIDATION FAILED:\nRejected Response: \"{response_text}\"\nReason: Character validation failed - likely third person, self-addressing, or inappropriate content"

modified_input = f"{input_text}\n\n🔄 VALIDATION RETRY: {character_specific_instruction}{validation_failure_context}"
```

### Duplicate Detection Enhancement
Located in `generate_character_response()` function:

```python
# 🎯 ENHANCED DUPLICATE RETRY: Include duplicate response context for learning
duplicate_failure_context = f"\n\nDUPLICATE DETECTED:\nRejected Response: \"{response_text}\"\nReason: This response is too similar to a previous response in the conversation"

modified_input = f"{input_text}\n\n🔄 DUPLICATE RETRY: Respond differently this time, use different words and approach{duplicate_failure_context}"
```

## Benefits

### 1. Faster Convergence
- LLM understands specific issues immediately
- Reduces trial-and-error approach
- More targeted improvements in each retry

### 2. Better Learning
- Sees exact examples of what doesn't work
- Understands severity through numerical scores
- Gets actionable, specific guidance

### 3. Reduced Repetition
- Avoids making the same mistakes repeatedly
- Learns patterns of what to avoid
- Builds understanding of character voice requirements

### 4. Enhanced Character Authenticity
- Character-specific guidance maintains voice consistency
- Learns appropriate first-person usage
- Understands conversation flow requirements

## Example Learning Scenarios

### Scenario 1: Third Person Issue
```
Attempt 1: "Brian thinks that's interesting. Brian would say..."
❌ Rejected: Third person self-reference (Score: 25/100)
📝 Retry Context: Includes rejected response + specific third person issues
🎯 Guidance: "Speak in FIRST PERSON only - use 'I' not your character name"
Attempt 2: "I think that's actually quite fascinating. I'd say..."
✅ Accepted: First person, character-appropriate (Score: 75/100)
```

### Scenario 2: Length Issue
```
Attempt 1: "Well, actually, I think that's a really interesting point you've made there, and I'd like to elaborate on it extensively because there are so many nuances to consider..."
❌ Rejected: Response too long (245 chars > 200 limit) (Score: 45/100)
📝 Retry Context: Includes rejected response + length issue details
🎯 Guidance: "Keep it much shorter and more concise"
Attempt 2: "Actually, that's quite interesting. I agree."
✅ Accepted: Appropriate length, character voice (Score: 70/100)
```

### Scenario 3: Self-Addressing Issue
```
Attempt 1: "Hey Peter, what do you think about that? Peter, you should really consider..."
❌ Rejected: Self-conversation detected (Score: 30/100)
📝 Retry Context: Includes rejected response + self-addressing issues
🎯 Guidance: "Respond naturally to the conversation, don't address other characters directly"
Attempt 2: "That's actually worth considering. Interesting point."
✅ Accepted: Natural conversation flow (Score: 65/100)
```

## Configuration

The enhanced retry context system works with existing configuration variables:

- `QUALITY_CONTROL_ENABLED`: Must be `True` for quality control retries
- `QUALITY_CONTROL_MAX_RETRIES`: Number of retry attempts (default: 5)
- `ADAPTIVE_QUALITY_CONTROL_ENABLED`: Enables adaptive thresholds
- Character-specific anti-hallucination settings

## Testing

Use `test_enhanced_retry_context.py` to validate the system:

```bash
python test_enhanced_retry_context.py
```

The test validates:
- Enhanced retry context structure
- Issue-specific guidance mapping
- Integration with existing retry types
- Learning effectiveness potential

## Monitoring

Enhanced retry context can be monitored through:

1. **Console Logs**: Look for "🔄 RETRY GUIDANCE:" messages
2. **Quality Control Status**: `/quality_control_status` endpoint shows retry statistics
3. **Fine-Tuning Records**: Rejected responses are recorded for analysis

## Future Enhancements

Potential improvements to the enhanced retry context system:

1. **Multi-Attempt Learning**: Include context from multiple previous attempts
2. **Success Pattern Recognition**: Include examples of successful responses
3. **Character-Specific Issue Tracking**: Track common issues per character
4. **Adaptive Guidance**: Adjust guidance based on character's historical issues
5. **Cross-Conversation Learning**: Learn from issues across different conversations

## Related Systems

The Enhanced Retry Context System integrates with:

- **Adaptive Quality Control**: Uses adaptive thresholds in failure context
- **Character-Aware Anti-Hallucination**: Provides character-specific guidance
- **Conversation Flow Assessment**: Uses detailed issue analysis
- **Fine-Tuning System**: Records enhanced feedback for learning

## Conclusion

The Enhanced Retry Context System represents a significant improvement in the bot's ability to learn from mistakes and generate better responses. By providing specific, actionable feedback about what went wrong, the system enables faster convergence to acceptable responses while maintaining character authenticity and conversation flow. 