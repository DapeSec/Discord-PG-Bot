import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.orchestrator.server import app, CHARACTER_API_URLS

@pytest.fixture
def client():
    """Create a test client for the Orchestrator V2."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_mongodb():
    """Mock MongoDB connections and collections."""
    with patch('app.orchestrator.server.mongo_client') as mock_client, \
         patch('app.orchestrator.server.conversations_collection') as mock_conv_coll, \
         patch('app.orchestrator.server.performance_collection') as mock_perf_coll:
        
        # Mock successful ping
        mock_client.admin.command.return_value = True
        
        yield {
            'client': mock_client,
            'conversations': mock_conv_coll,
            'performance': mock_perf_coll
        }

@pytest.fixture
def mock_keydb_cache():
    """Mock KeyDB cache integration."""
    with patch('app.orchestrator.server.CACHE_AVAILABLE', True), \
         patch('app.orchestrator.server.get_cache') as mock_get_cache, \
         patch('app.orchestrator.server.cache_recent_response') as mock_cache_response, \
         patch('app.orchestrator.server.get_recent_responses') as mock_get_responses:
        
        mock_cache_instance = Mock()
        mock_get_cache.return_value = mock_cache_instance
        mock_cache_response.return_value = True
        mock_get_responses.return_value = []
        
        yield {
            'get_cache': mock_get_cache,
            'cache_response': mock_cache_response,
            'get_responses': mock_get_responses,
            'cache_instance': mock_cache_instance
        }

class TestOrchestratorV2:
    """Test suite for Orchestrator V2 Service."""

    def test_health_check_healthy(self, client, mock_mongodb, mock_keydb_cache):
        """Test health check when all services are healthy including KeyDB."""
        with patch('requests.get') as mock_get:
            # Mock all external service health checks as successful
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            response = client.get('/health')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert data['service'] == 'OrchestratorV2'
            assert 'components' in data
            assert data['components']['mongodb'] == 'healthy'
            assert data['cache']['available'] is True

    def test_health_check_degraded(self, client, mock_mongodb):
        """Test health check when some services are unhealthy."""
        with patch('requests.get') as mock_get:
            # Mock some services as failing
            def side_effect(url, **kwargs):
                if 'peter' in url:
                    raise Exception("Service down")
                mock_response = Mock()
                mock_response.status_code = 200
                return mock_response
            
            mock_get.side_effect = side_effect
            
            response = client.get('/health')
            assert response.status_code == 503
            
            data = json.loads(response.data)
            assert data['status'] == 'degraded'

    def test_health_check_cache_unavailable(self, client, mock_mongodb):
        """Test health check when KeyDB cache is unavailable."""
        with patch('app.orchestrator.server.CACHE_AVAILABLE', False), \
             patch('requests.get') as mock_get:
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            response = client.get('/health')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['cache']['available'] is False
            assert data['cache']['fallback'] == 'in-memory'

    @patch('app.orchestrator.server.get_conversation_history')
    @patch('app.orchestrator.server._generate_with_mistral_llm')  # Updated to mock local Mistral LLM
    @patch('app.orchestrator.server.send_to_discord')
    @patch('app.orchestrator.server.save_conversation_turn')
    def test_orchestrate_conversation_success(self, mock_save, mock_discord, mock_generate, mock_history, client, mock_keydb_cache):
        """Test successful conversation orchestration with local Mistral LLM and KeyDB caching."""
        # Mock dependencies
        mock_history.return_value = []
        mock_generate.return_value = "Holy crap! This is a test response!"  # Now returns string directly
        mock_discord.return_value = True
        mock_save.return_value = True
        
        request_data = {
            "user_query": "Hello Peter!",
            "channel_id": "123456789",
            "initiator_bot_name": "Peter",
            "human_user_display_name": "TestUser",
            "source": "discord_handler"
        }
        
        response = client.post('/orchestrate', json=request_data)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['character_name'] == 'Peter'
        assert data['response_sent'] is True
        
        # Verify all functions were called
        mock_history.assert_called_once()
        mock_generate.assert_called_once()
        mock_discord.assert_called_once()
        mock_save.assert_called_once()
        
        # Verify cache operations were called
        mock_keydb_cache['get_responses'].assert_called_once()
        mock_keydb_cache['cache_response'].assert_called_once()

    @patch('app.orchestrator.server.get_conversation_history')
    @patch('app.orchestrator.server._generate_with_mistral_llm')
    def test_orchestrate_response_deduplication(self, mock_generate, mock_history, client):
        """Test response deduplication using KeyDB cache."""
        with patch('app.orchestrator.server.CACHE_AVAILABLE', True), \
             patch('app.orchestrator.server.get_recent_responses') as mock_get_responses, \
             patch('app.orchestrator.server.is_duplicate_response') as mock_is_duplicate:
            
            # Mock dependencies
            mock_history.return_value = []
            mock_get_responses.return_value = ["previous response", "another response"]
            mock_is_duplicate.return_value = True  # Simulate duplicate detected
            mock_generate.return_value = "Holy crap! This is a test response!"
            
            request_data = {
                "user_query": "Hello Peter!",
                "channel_id": "123456789",
                "initiator_bot_name": "Peter",
                "human_user_display_name": "TestUser"
            }
            
            response = client.post('/orchestrate', json=request_data)
            
            # Should still succeed but with duplicate detection
            assert response.status_code == 200
            
            # Verify duplicate check was performed
            mock_get_responses.assert_called_once_with("Peter", limit=50)
            mock_is_duplicate.assert_called_once()

    def test_orchestrate_conversation_missing_fields(self, client):
        """Test orchestration with missing required fields."""
        request_data = {
            "user_query": "Hello!",
            "channel_id": "123456789"
            # Missing initiator_bot_name
        }
        
        response = client.post('/orchestrate', json=request_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'Missing required fields' in data['error']

    def test_orchestrate_conversation_unknown_character(self, client):
        """Test orchestration with unknown character."""
        request_data = {
            "user_query": "Hello!",
            "channel_id": "123456789",
            "initiator_bot_name": "UnknownBot"
        }
        
        response = client.post('/orchestrate', json=request_data)
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'Unknown character' in data['error']

    @patch('app.orchestrator.server.get_conversation_history')
    @patch('app.orchestrator.server.generate_character_response')
    def test_orchestrate_conversation_generation_failure(self, mock_generate, mock_history, client):
        """Test orchestration when centralized LLM generation fails."""
        mock_history.return_value = []
        mock_generate.return_value = None  # Simulate failure
        
        request_data = {
            "user_query": "Hello Peter!",
            "channel_id": "123456789",
            "initiator_bot_name": "Peter",
            "human_user_display_name": "TestUser"
        }
        
        response = client.post('/orchestrate', json=request_data)
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert 'Failed to generate character response' in data['error']

    @patch('requests.post')
    def test_generate_character_response_success(self, mock_post):
        """Test successful character response generation."""
        from app.orchestrator.server import generate_character_response
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "character_name": "Peter",
            "response": "Holy crap! Test response!",
            "timestamp": datetime.now().isoformat()
        }
        mock_post.return_value = mock_response
        
        result = generate_character_response(
            character_name="Peter",
            user_query="Hello!",
            conversation_history=[],
            human_user_display_name="TestUser"
        )
        
        assert result is not None
        assert result['character_name'] == 'Peter'
        assert 'response' in result
        
        # Verify API was called with correct data
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert 'peter:5005/generate_response' in args[0]
        assert kwargs['json']['user_query'] == 'Hello!'
        assert kwargs['json']['max_length'] == 500  # Peter's max length

    @patch('requests.post')
    def test_generate_character_response_api_error(self, mock_post):
        """Test character response generation with API error."""
        from app.orchestrator.server import generate_character_response
        
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        result = generate_character_response(
            character_name="Brian",
            user_query="Hello!",
            conversation_history=[],
            human_user_display_name="TestUser"
        )
        
        assert result is None

    @patch('requests.post')
    def test_send_to_discord_success(self, mock_post):
        """Test successful Discord message sending."""
        from app.orchestrator.server import send_to_discord
        
        # Mock successful Discord Handler response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = send_to_discord(
            bot_name="Stewie",
            channel_id="123456789",
            message_content="What the deuce?"
        )
        
        assert result is True
        
        # Verify Discord Handler was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert 'discord-handler:5001/send_message' in args[0]
        assert kwargs['json']['bot_name'] == 'Stewie'
        assert kwargs['json']['channel_id'] == '123456789'
        assert kwargs['json']['message_content'] == 'What the deuce?'

    @patch('requests.post')
    def test_send_to_discord_failure(self, mock_post):
        """Test Discord message sending failure."""
        from app.orchestrator.server import send_to_discord
        
        # Mock Discord Handler error
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_post.return_value = mock_response
        
        result = send_to_discord(
            bot_name="Peter",
            channel_id="123456789",
            message_content="Holy crap!"
        )
        
        assert result is False

    def test_get_conversation_history(self, mock_mongodb):
        """Test conversation history retrieval."""
        from app.orchestrator.server import get_conversation_history
        
        # Mock database response
        mock_docs = [
            {
                "timestamp": datetime.now(),
                "user_query": "Hello!",
                "character_name": "Peter",
                "character_response": "Holy crap! Hi there!",
                "human_user_display_name": "TestUser"
            },
            {
                "timestamp": datetime.now(),
                "user_query": "How are you?",
                "character_name": "Brian",
                "character_response": "I'm contemplating existence.",
                "human_user_display_name": "TestUser"
            }
        ]
        
        mock_cursor = Mock()
        mock_cursor.__iter__ = Mock(return_value=iter(mock_docs))
        mock_mongodb['conversations'].find.return_value.sort.return_value.limit.return_value = mock_cursor
        
        history = get_conversation_history("123456789")
        
        assert len(history) == 2
        assert history[0]['character_name'] == 'Peter'
        assert history[1]['character_name'] == 'Brian'

    def test_save_conversation_turn(self, mock_mongodb):
        """Test conversation turn saving."""
        from app.orchestrator.server import save_conversation_turn
        
        mock_mongodb['conversations'].insert_one.return_value = Mock()
        
        result = save_conversation_turn(
            channel_id="123456789",
            user_query="Hello!",
            character_name="Peter",
            character_response="Holy crap! Hi!",
            human_user_display_name="TestUser"
        )
        
        assert result is True
        mock_mongodb['conversations'].insert_one.assert_called_once()
        
        # Verify the document structure
        call_args = mock_mongodb['conversations'].insert_one.call_args[0][0]
        assert call_args['channel_id'] == "123456789"
        assert call_args['user_query'] == "Hello!"
        assert call_args['character_name'] == "Peter"
        assert call_args['character_response'] == "Holy crap! Hi!"

    @patch('requests.get')
    def test_get_all_character_info(self, mock_get, client):
        """Test getting information about all characters."""
        # Mock character API responses
        def side_effect(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            if 'peter' in url:
                mock_response.json.return_value = {
                    "character_name": "Peter",
                    "personality": "Lovable oaf",
                    "max_response_length": 500
                }
            elif 'brian' in url:
                mock_response.json.return_value = {
                    "character_name": "Brian",
                    "personality": "Intellectual dog",
                    "max_response_length": 1800
                }
            elif 'stewie' in url:
                mock_response.json.return_value = {
                    "character_name": "Stewie",
                    "personality": "Evil baby genius",
                    "max_response_length": 1800
                }
            return mock_response
        
        mock_get.side_effect = side_effect
        
        response = client.get('/character_info')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['service'] == 'OrchestratorV2'
        assert 'characters' in data
        assert 'Peter' in data['characters']
        assert 'Brian' in data['characters']
        assert 'Stewie' in data['characters']

    def test_get_performance_metrics(self, client, mock_mongodb):
        """Test performance metrics retrieval."""
        # Mock database queries
        mock_mongodb['conversations'].count_documents.return_value = 42
        mock_mongodb['conversations'].find.return_value = [
            {"character_response": "Short response"},
            {"character_response": "This is a longer response with more content"}
        ]
        
        response = client.get('/metrics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'total_conversations_24h' in data
        assert 'conversations_by_character' in data
        assert 'average_response_length' in data
        assert data['service_uptime'] == 'healthy'

    def test_local_mistral_character_response_generation(self):
        """Test the local Mistral LLM response generation."""
        from app.orchestrator.server import generate_character_response
        
        with patch('app.orchestrator.server._generate_with_mistral_llm') as mock_mistral:
            mock_mistral.return_value = "Holy crap! Test response!"
            
            result = generate_character_response(
                character_name="Peter",
                user_query="Hello!",
                conversation_history=[],
                human_user_display_name="TestUser"
            )
            
            assert result is not None
            assert result['character_name'] == 'Peter'
            assert 'response' in result
            assert result['llm_type'] == 'local_mistral'
            assert result['model'] == 'mistral:4070'
            
            # Verify Mistral was called with correct parameters
            mock_mistral.assert_called_once()

    def test_character_settings_and_prompts(self):
        """Test that character settings and prompts are properly configured for Mistral."""
        from app.orchestrator.server import CHARACTER_PROMPTS, CHARACTER_SETTINGS, CHARACTER_FALLBACKS
        
        # Verify all characters are configured
        expected_characters = ["Peter", "Brian", "Stewie"]
        for character in expected_characters:
            assert character in CHARACTER_PROMPTS
            assert character in CHARACTER_SETTINGS
            assert character in CHARACTER_FALLBACKS
        
        # Verify character-specific settings
        assert CHARACTER_SETTINGS["Peter"]["max_tokens"] == 500
        assert CHARACTER_SETTINGS["Brian"]["max_tokens"] == 1800
        assert CHARACTER_SETTINGS["Stewie"]["max_tokens"] == 1800
        
        # Verify prompts contain character-specific content
        assert "Peter Griffin" in CHARACTER_PROMPTS["Peter"]
        assert "Brian Griffin" in CHARACTER_PROMPTS["Brian"]
        assert "Stewie Griffin" in CHARACTER_PROMPTS["Stewie"]

class TestOrchestratorV2Integration:
    """Integration tests for Orchestrator V2."""

    @patch('app.orchestrator.server.mongo_client')
    @patch('requests.post')
    @patch('requests.get')
    def test_full_orchestration_flow(self, mock_get, mock_post, mock_mongo, client):
        """Test the complete orchestration flow from Discord message to response."""
        # Mock MongoDB
        mock_mongo.admin.command.return_value = True
        
        # Mock conversation history (empty)
        mock_cursor = Mock()
        mock_cursor.__iter__ = Mock(return_value=iter([]))
        
        with patch('app.orchestrator.server.conversations_collection') as mock_conv_coll:
            mock_conv_coll.find.return_value.sort.return_value.limit.return_value = mock_cursor
            mock_conv_coll.insert_one.return_value = Mock()
            
            # Mock character API response
            character_response = Mock()
            character_response.status_code = 200
            character_response.json.return_value = {
                "character_name": "Peter",
                "response": "Holy crap! This is working!",
                "timestamp": datetime.now().isoformat()
            }
            
            # Mock Discord Handler response
            discord_response = Mock()
            discord_response.status_code = 200
            
            def post_side_effect(url, **kwargs):
                if 'generate_response' in url:
                    return character_response
                elif 'send_message' in url:
                    return discord_response
                return Mock(status_code=404)
            
            mock_post.side_effect = post_side_effect
            
            # Test the orchestration
            request_data = {
                "user_query": "Hello Peter!",
            "channel_id": "123456789",
                "initiator_bot_name": "Peter",
                "human_user_display_name": "TestUser",
                "source": "discord_handler"
            }
            
            response = client.post('/orchestrate', json=request_data)
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert data['character_name'] == 'Peter'
            assert data['response_sent'] is True
            
            # Verify both API calls were made
            assert mock_post.call_count == 2  # Character API + Discord Handler

if __name__ == '__main__':
    pytest.main([__file__]) 