# Supervised Fine-Tuning System Guide

## Overview

The Supervised Fine-Tuning System continuously improves character accuracy by learning from conversation quality feedback. It **automatically rates every response using LLM evaluation** and **ensures quality before sending to users with Quality Control Agent** while optimizing character prompts based on accumulated quality assessments.

## 🎯 How It Works

### 1. Quality Control Agent (Pre-Send Filtering)
- **Real-Time Quality Assurance**: Every response is evaluated BEFORE being sent to Discord
- **Automatic Retry**: Poor quality responses are regenerated until they meet standards
- **Configurable Thresholds**: Set minimum quality rating (default: 3.0/5) for acceptance
- **Max Retry Protection**: Prevents infinite loops with configurable retry limits (default: 3 attempts)
- **Transparent Operation**: All quality control decisions are logged with reasoning

### 2. Automatic LLM-Based Assessment
- **Real-Time Evaluation**: Every bot response is automatically evaluated by the LLM for character accuracy
- **Detailed Analysis**: LLM provides rating (1-5) with reasoning, strengths, weaknesses, and improvement suggestions
- **Comprehensive Scoring**: Evaluates speech patterns, personality traits, humor style, catchphrases, and character knowledge
- **Automatic Recording**: All assessments are automatically stored for learning and optimization
- **No Manual Work**: System continuously learns without human intervention

### 3. Prompt Optimization Engine
- **Smart Triggers**: Automatically optimizes prompts when average ratings drop below threshold (default: 0.7)
- **Minimum Data**: Requires sufficient ratings (default: 10) before optimization to ensure reliability
- **LLM-Powered Improvement**: Uses advanced prompts to analyze feedback patterns and generate better character prompts
- **Version Control**: Maintains history of all prompt versions with performance metrics

### 4. A/B Testing System
- **Gradual Rollout**: New optimized prompts are tested on limited traffic (default: 20%) before full deployment
- **Performance Validation**: Compares optimized vs original prompts to ensure actual improvement
- **Automatic Rollback**: Reverts to previous version if optimized prompt performs worse
- **Risk Mitigation**: Ensures system only gets better, never worse

## 🔧 Configuration

### Environment Variables

```bash
# Fine-Tuning System
FINE_TUNING_ENABLED=true                    # Enable/disable automatic optimization
OPTIMIZATION_THRESHOLD=0.7                  # Trigger optimization when avg rating < 0.7
MIN_RATINGS_FOR_OPTIMIZATION=10             # Minimum ratings before optimization
AB_TEST_PERCENTAGE=0.2                      # 20% traffic for A/B testing

# Quality Control
QUALITY_CONTROL_ENABLED=true                # Enable/disable pre-send quality filtering
QUALITY_CONTROL_MIN_RATING=3.0             # Minimum acceptable rating (1-5)
QUALITY_CONTROL_MAX_RETRIES=3              # Max retries for quality improvement
```

### Character-Specific Quality Indicators

The system recognizes character-specific patterns for accurate assessment:

**Peter Griffin:**
- ✅ Positive: "hehehehehe", "holy crap", "freakin", "awesome", "chicken fight"
- ❌ Negative: "sophisticated", "intellectual", "profound", "eloquent"

**Brian Griffin:**
- ✅ Positive: "intellectual", "sophisticated", "literary", "profound", "actually"
- ❌ Negative: "hehehe", "stupid", "simple", "dumb"

**Stewie Griffin:**
- ✅ Positive: "what the deuce", "blast", "evil genius", "sophisticated", "british"
- ❌ Negative: "simple", "dumb", "hehehe"

## 📊 API Endpoints

### Core Rating System
```bash
# Rate a character response
POST /rate_response
{
  "character_name": "Peter|Brian|Stewie",
  "response_text": "The response to rate",
  "rating": 1-5,
  "feedback": "Optional feedback text",
  "conversation_context": "Optional context"
}
```

### Performance Monitoring
```bash
# Get overall system statistics
GET /fine_tuning_stats

# Get optimization reports for all characters
GET /optimization_report?days=7

# Get detailed performance for specific character
GET /prompt_performance?character=Peter&days=30

# Get quality control status and statistics
GET /quality_control_status
```

### Manual Control
```bash
# Manually trigger optimization
POST /trigger_optimization
{
  "character_name": "Peter|Brian|Stewie"
}
```

## 🎭 Example Usage

### 1. Automatic Operation (No Manual Work Required)

The system works completely automatically:

1. **User sends message** → Peter responds
2. **LLM Auto-Assessment** → Rates Peter's response quality (e.g., 4.2/5)
3. **Quality Control** → Ensures response meets minimum standards before sending
4. **Data Collection** → Rating and feedback stored for learning
5. **Optimization Trigger** → If ratings drop, system automatically improves prompts
6. **A/B Testing** → New prompts tested carefully before full deployment

### 2. Manual Rating (Optional Enhancement)

Users can still provide manual ratings for additional data:

```python
import requests

# Rate a response manually
rating_data = {
    "character_name": "Peter",
    "response_text": "Hehehehehe! Holy crap, that's awesome!",
    "rating": 5,
    "feedback": "Perfect Peter voice with signature laugh and catchphrase",
    "user_id": "discord_user_123"
}

response = requests.post("http://orchestrator:5003/rate_response", json=rating_data)
```

### 3. Monitoring Performance

```python
# Get system statistics
stats = requests.get("http://orchestrator:5003/fine_tuning_stats").json()
print(f"Peter's average rating: {stats['system_stats']['Peter']['average_rating']}")

# Get quality control statistics
qc_status = requests.get("http://orchestrator:5003/quality_control_status").json()
print(f"Quality control acceptance rate: {qc_status['statistics']['Peter']['acceptance_rate']}%")
```

## 📈 Performance Metrics

### Automatic Tracking
- **Response Quality**: Average ratings per character over time
- **Improvement Trends**: Before/after optimization comparisons
- **Quality Control Stats**: Acceptance/rejection rates and reasons
- **A/B Test Results**: Performance comparison between prompt versions
- **User Satisfaction**: Distribution of ratings and feedback patterns

### Character-Specific Metrics
- **Authenticity Score**: How well responses match character personality
- **Consistency Rating**: Variation in quality over time
- **Engagement Level**: User interaction and response rates
- **Problem Areas**: Common issues identified by assessments
- **Strength Areas**: What the character does well consistently

## 🔍 Quality Assessment Criteria

The LLM evaluates responses based on:

1. **Speech Patterns (25%)**: Vocabulary, catchphrases, speaking style
2. **Personality Accuracy (25%)**: Core traits and motivations
3. **Character Knowledge (20%)**: Consistency with character's background
4. **Humor Style (20%)**: Appropriate comedic approach for character
5. **Contextual Appropriateness (10%)**: Fit within conversation flow

## 🚀 Advanced Features

### Intelligent Feedback Analysis
- **Pattern Recognition**: Identifies common issues across multiple ratings
- **Contextual Understanding**: Considers conversation context in assessments
- **Improvement Suggestions**: Provides specific, actionable feedback for optimization
- **Trend Analysis**: Tracks improvement over time and identifies regression

### Robust Error Handling
- **Graceful Degradation**: System continues working even if components fail
- **Fallback Mechanisms**: Multiple backup systems ensure continuous operation
- **Error Recovery**: Automatic retry and recovery from temporary failures
- **Data Integrity**: Protects against data loss and corruption

### Scalability Features
- **Efficient Database**: Optimized MongoDB queries and indexing
- **Background Processing**: Non-blocking assessment and optimization
- **Resource Management**: Controlled LLM usage and rate limiting
- **Performance Monitoring**: Tracks system performance and bottlenecks

## 🎯 Best Practices

### For Optimal Performance
1. **Let the system run**: Automatic assessment works best with natural conversations
2. **Monitor trends**: Check performance reports regularly to understand improvements
3. **Adjust thresholds**: Fine-tune quality control settings based on your requirements
4. **Trust the process**: The system learns and improves over time

### For Troubleshooting
1. **Check logs**: Quality control and assessment decisions are logged with reasoning
2. **Monitor health**: Use `/health` endpoint to verify system status
3. **Review metrics**: Performance dashboards show system health and trends
4. **Test endpoints**: Use test scripts to verify functionality

## 📝 Testing

Run the comprehensive test suite:

```bash
python scripts/test_fine_tuning.py
```

This script demonstrates:
- LLM auto-assessment in action
- Quality control filtering
- Manual rating capabilities
- Optimization triggers
- Performance monitoring
- A/B testing results

## 🔧 Maintenance

### Regular Tasks
- Monitor system performance metrics
- Review optimization results
- Adjust configuration as needed
- Check error logs for issues

### Database Maintenance
- Monitor MongoDB storage usage
- Archive old ratings if needed
- Backup prompt versions
- Index optimization for performance

## 📊 System Architecture

### MongoDB Collections

The fine-tuning system uses several MongoDB collections:

#### `response_ratings`
```javascript
{
  "_id": ObjectId,
  "character_name": "Peter|Brian|Stewie",
  "response_text": "The actual response",
  "rating": 1-5,
  "feedback": "Detailed feedback text",
  "user_id": "llm_auto_assessment|human_evaluator_123",
  "conversation_context": "Context of the conversation",
  "timestamp": ISODate,
  "prompt_version": 1
}
```

#### `prompt_versions`
```javascript
{
  "_id": ObjectId,
  "character_name": "Peter|Brian|Stewie",
  "version": 2,
  "optimized_prompt": "Enhanced character prompt text",
  "created_at": ISODate,
  "is_active": true,
  "based_on_ratings": 15,
  "average_rating_before": 2.3
}
```

#### `performance_metrics`
```javascript
{
  "_id": ObjectId,
  "character_name": "Peter|Brian|Stewie",
  "date": ISODate,
  "total_ratings": 25,
  "rating_sum": 102.5,
  "ratings": [4.1, 3.8, 4.5, ...]  // Last 100 ratings
}
```

### Data Flow

1. **Response Generation** → Character generates response
2. **Quality Assessment** → LLM evaluates response (automatic)
3. **Quality Control** → Pre-send filtering based on rating
4. **Data Storage** → Rating and feedback stored in MongoDB
5. **Performance Analysis** → Background monitoring of rating trends
6. **Optimization Trigger** → Automatic prompt improvement when needed
7. **A/B Testing** → Gradual rollout of optimized prompts
8. **Continuous Learning** → System improves over time

## 🔬 Advanced Configuration

### Custom Assessment Criteria

You can customize the LLM assessment by modifying the assessment prompt in the `_assess_response_quality_with_llm` function:

```python
# Example customization for stricter speech pattern requirements
assessment_prompt = f"""...
EVALUATION CRITERIA:
1. **Speech Patterns (35%)**: Increased weight on catchphrases and vocabulary
2. **Personality Accuracy (25%)**: Core traits and motivations  
3. **Character Knowledge (20%)**: Consistency with character's background
4. **Humor Style (15%)**: Appropriate comedic approach
5. **Contextual Appropriateness (5%)**: Reduced weight on context fit
..."""
```

### Quality Control Tuning

Adjust quality thresholds based on your requirements:

```bash
# Stricter quality control
QUALITY_CONTROL_MIN_RATING=3.5
QUALITY_CONTROL_MAX_RETRIES=5

# More lenient for development
QUALITY_CONTROL_MIN_RATING=2.5
QUALITY_CONTROL_MAX_RETRIES=2
```

### A/B Testing Configuration

Control how aggressively new prompts are tested:

```bash
# Conservative testing (5% traffic)
AB_TEST_PERCENTAGE=0.05

# Aggressive testing (50% traffic)
AB_TEST_PERCENTAGE=0.5
```

The Supervised Fine-Tuning System provides a complete, automated solution for continuously improving character authenticity while ensuring quality responses are delivered to users. The combination of real-time quality control, automatic assessment, and intelligent optimization creates a self-improving system that gets better over time without manual intervention. 