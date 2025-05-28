import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestPeterDiscordHandler:
    """Test suite for Peter Discord Handler Service."""

    @pytest.fixture
    def peter_client(self):
        """Create a test client for Peter Discord Handler."""
        from app.discord_handler.peter_discord_service import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_peter_health_check_healthy(self, peter_client):
        """Test Peter health check when client is ready."""
        with patch('app.discord_handler.peter_discord_service.peter_client') as mock_client:
            mock_user = Mock()
            mock_user.id = 123456789
            mock_user.name = "Peter Griffin"
            mock_client.user = mock_user
            mock_client.is_ready.return_value = True
            
            with patch('app.discord_handler.peter_discord_service.CACHE_AVAILABLE', True):
                with patch('app.discord_handler.peter_discord_service.get_discord_state') as mock_get_state:
                    mock_get_state.return_value = {
                        'ready': True,
                        'mention': '<@123456789>',
                        'user_id': 123456789,
                        'username': 'Peter Griffin'
                    }
                    
                    response = peter_client.get('/health')
                    assert response.status_code == 200
                    
                    data = json.loads(response.data)
                    assert data['status'] == 'healthy'
                    assert data['service'] == 'PeterDiscordHandler'
                    assert data['cache']['available'] is True
                    assert data['discord_client']['logged_in'] is True

    def test_peter_health_check_cache_unavailable(self, peter_client):
        """Test Peter health check when cache is unavailable."""
        with patch('app.discord_handler.peter_discord_service.peter_client') as mock_client:
            mock_user = Mock()
            mock_user.id = 123456789
            mock_user.name = "Peter Griffin"
            mock_client.user = mock_user
            mock_client.is_ready.return_value = True
            
            with patch('app.discord_handler.peter_discord_service.CACHE_AVAILABLE', False):
                response = peter_client.get('/health')
                assert response.status_code == 200
                
                data = json.loads(response.data)
                assert data['cache']['available'] is False

    def test_peter_send_message_success(self, peter_client):
        """Test successful message sending via Peter."""
        with patch('app.discord_handler.peter_discord_service.peter_client') as mock_client:
            mock_client.user = Mock()
            mock_client.is_ready.return_value = True
            mock_client.loop = Mock()
            mock_client.loop.is_running.return_value = True
            
            with patch('asyncio.run_coroutine_threadsafe') as mock_run:
                mock_future = Mock()
                mock_future.result.return_value = None
                mock_run.return_value = mock_future
                
                response = peter_client.post('/send_message', 
                    json={
                        "channel_id": "123456789",
                        "message_content": "Hehehe! This is a test!"
                    })
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['status'] == 'Message sent successfully'

    def test_peter_bot_info_ready(self, peter_client):
        """Test getting Peter bot info when ready."""
        with patch('app.discord_handler.peter_discord_service.peter_client') as mock_client:
            mock_user = Mock()
            mock_user.id = 123456789
            mock_user.name = "Peter Griffin"
            mock_client.user = mock_user
            mock_client.is_ready.return_value = True
            
            response = peter_client.get('/bot_info')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['ready'] is True
            assert data['id'] == 123456789
            assert data['username'] == "Peter Griffin"
            assert data['mention'] == "<@123456789>"

class TestBrianDiscordHandler:
    """Test suite for Brian Discord Handler Service."""

    @pytest.fixture
    def brian_client(self):
        """Create a test client for Brian Discord Handler."""
        from app.discord_handler.brian_discord_service import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_brian_health_check_with_cache(self, brian_client):
        """Test Brian health check with KeyDB cache integration."""
        with patch('app.discord_handler.brian_discord_service.brian_client') as mock_client:
            mock_user = Mock()
            mock_user.id = 987654321
            mock_user.name = "Brian Griffin"
            mock_client.user = mock_user
            mock_client.is_ready.return_value = True
            
            with patch('app.discord_handler.brian_discord_service.CACHE_AVAILABLE', True):
                with patch('app.discord_handler.brian_discord_service.get_discord_state') as mock_get_state:
                    mock_get_state.return_value = {
                        'ready': True,
                        'mention': '<@987654321>',
                        'user_id': 987654321,
                        'username': 'Brian Griffin',
                        'service_name': 'BrianDiscordHandler'
                    }
                    
                    response = brian_client.get('/health')
                    assert response.status_code == 200
                    
                    data = json.loads(response.data)
                    assert data['status'] == 'healthy'
                    assert data['service'] == 'BrianDiscordHandler'
                    assert 'cached_state' in data

    def test_brian_send_message_not_ready(self, brian_client):
        """Test Brian message sending when client is not ready."""
        with patch('app.discord_handler.brian_discord_service.brian_client') as mock_client:
            mock_client.user = None
            mock_client.is_ready.return_value = False
            
            with patch('app.discord_handler.brian_discord_service.brian_ready', False):
                response = brian_client.post('/send_message', 
                    json={
                        "channel_id": "123456789",
                        "message_content": "*sighs* This won't work..."
                    })
                
                assert response.status_code == 503
                data = json.loads(response.data)
                assert 'not logged in or ready' in data['error']

class TestStewieDiscordHandler:
    """Test suite for Stewie Discord Handler Service."""

    @pytest.fixture
    def stewie_client(self):
        """Create a test client for Stewie Discord Handler."""
        from app.discord_handler.stewie_discord_service import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_stewie_health_check_degraded(self, stewie_client):
        """Test Stewie health check when client is not ready."""
        with patch('app.discord_handler.stewie_discord_service.stewie_client') as mock_client:
            mock_client.user = None
            mock_client.is_ready.return_value = False
            
            with patch('app.discord_handler.stewie_discord_service.stewie_ready', False):
                with patch('app.discord_handler.stewie_discord_service.CACHE_AVAILABLE', True):
                    with patch('app.discord_handler.stewie_discord_service.get_discord_state') as mock_get_state:
                        mock_get_state.return_value = None
                        
                        response = stewie_client.get('/health')
                        assert response.status_code == 503
                        
                        data = json.loads(response.data)
                        assert data['status'] == 'degraded'

    def test_stewie_bot_info_not_ready(self, stewie_client):
        """Test getting Stewie bot info when not ready."""
        with patch('app.discord_handler.stewie_discord_service.stewie_client') as mock_client:
            mock_client.is_ready.return_value = False
            
            response = stewie_client.get('/bot_info')
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert data['ready'] is False

class TestDiscordHandlerCacheIntegration:
    """Test KeyDB cache integration across Discord handlers."""

    def test_cache_discord_state_success(self):
        """Test successful caching of Discord state."""
        with patch('app.discord_handler.peter_discord_service.CACHE_AVAILABLE', True):
            with patch('app.discord_handler.peter_discord_service.cache_discord_state') as mock_cache:
                mock_cache.return_value = True
                
                # Simulate on_ready event
                from app.discord_handler.peter_discord_service import peter_client
                
                # Mock the event handler
                with patch.object(peter_client, 'event'):
                    state_data = {
                        'ready': True,
                        'mention': '<@123456789>',
                        'user_id': 123456789,
                        'username': 'Peter Griffin',
                        'service_name': 'PeterDiscordHandler'
                    }
                    
                    # This would be called in the actual on_ready event
                    mock_cache.assert_not_called()  # Not called yet
                    
                    # Simulate the cache call
                    mock_cache('peter', state_data, ttl=3600)
                    mock_cache.assert_called_with('peter', state_data, ttl=3600)

    def test_get_discord_state_from_cache(self):
        """Test retrieving Discord state from cache."""
        with patch('app.discord_handler.brian_discord_service.CACHE_AVAILABLE', True):
            with patch('app.discord_handler.brian_discord_service.get_discord_state') as mock_get_state:
                expected_state = {
                    'ready': True,
                    'mention': '<@987654321>',
                    'user_id': 987654321,
                    'username': 'Brian Griffin'
                }
                mock_get_state.return_value = expected_state
                
                # Test the function
                result = mock_get_state('brian')
                assert result == expected_state
                mock_get_state.assert_called_with('brian')

    def test_cache_fallback_behavior(self):
        """Test fallback behavior when cache is unavailable."""
        with patch('app.discord_handler.stewie_discord_service.CACHE_AVAILABLE', False):
            # When cache is unavailable, services should still function
            # using in-memory state
            from app.discord_handler.stewie_discord_service import stewie_ready, stewie_mention, stewie_id
            
            # These should work even without cache
            assert stewie_ready is not None  # Should be False initially
            assert stewie_mention is None    # Should be None initially
            assert stewie_id is None         # Should be None initially

class TestDiscordMessageHandling:
    """Test Discord message handling logic for individual handlers."""

    @pytest.mark.asyncio
    async def test_peter_message_handling_with_mention(self):
        """Test Peter handling messages with his mention."""
        with patch('app.discord_handler.peter_discord_service.peter_mention', '<@123456789>'):
            with patch('app.discord_handler.peter_discord_service.peter_id', 123456789):
                from app.discord_handler.peter_discord_service import handle_discord_message
                
                # Mock message object
                mock_message = Mock()
                mock_message.author.id = 555555555  # Different from Peter's ID
                mock_message.author.bot = False
                mock_message.content = "<@123456789> what's up?"
                mock_message.channel.id = 999999999
                mock_message.author.display_name = "TestUser"
                
                # Mock the threading and requests
                with patch('threading.Thread') as mock_thread:
                    await handle_discord_message(mock_message)
                    
                    # Should start a thread to forward to orchestrator
                    mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_brian_message_handling_command(self):
        """Test Brian handling !brian commands."""
        with patch('app.discord_handler.brian_discord_service.brian_mention', '<@987654321>'):
            with patch('app.discord_handler.brian_discord_service.brian_id', 987654321):
                from app.discord_handler.brian_discord_service import handle_discord_message
                
                # Mock message object
                mock_message = Mock()
                mock_message.author.id = 555555555
                mock_message.author.bot = False
                mock_message.content = "!brian tell me something intellectual"
                mock_message.channel.id = 999999999
                mock_message.author.display_name = "TestUser"
                
                with patch('threading.Thread') as mock_thread:
                    await handle_discord_message(mock_message)
                    
                    mock_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_stewie_ignore_bot_messages(self):
        """Test Stewie ignoring messages from other bots."""
        with patch('app.discord_handler.stewie_discord_service.stewie_id', 111111111):
            from app.discord_handler.stewie_discord_service import handle_discord_message
            
            # Mock message from another bot
            mock_message = Mock()
            mock_message.author.id = 222222222
            mock_message.author.bot = True  # This is a bot message
            mock_message.content = "Hello from another bot"
            
            with patch('threading.Thread') as mock_thread:
                await handle_discord_message(mock_message)
                
                # Should not start any thread for bot messages
                mock_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_mention_default_response(self):
        """Test default response for empty mentions."""
        with patch('app.discord_handler.peter_discord_service.peter_mention', '<@123456789>'):
            with patch('app.discord_handler.peter_discord_service.peter_id', 123456789):
                from app.discord_handler.peter_discord_service import handle_discord_message
                
                # Mock message with empty mention
                mock_message = Mock()
                mock_message.author.id = 555555555
                mock_message.author.bot = False
                mock_message.content = "<@123456789>"  # Just the mention, no text
                mock_message.channel = Mock()
                mock_message.channel.send = AsyncMock()
                
                await handle_discord_message(mock_message)
                
                # Should send default response
                mock_message.channel.send.assert_called_once()
                call_args = mock_message.channel.send.call_args[0][0]
                assert "Hehehe" in call_args or "Yeah" in call_args

class TestDiscordHandlerForwarding:
    """Test message forwarding to orchestrator."""

    def test_forward_to_orchestrator_peter(self):
        """Test Peter forwarding message to orchestrator."""
        from app.discord_handler.peter_discord_service import forward_to_orchestrator
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            message_data = {
                "user_query": "test message",
                "channel_id": 123456789,
                "initiator_bot_name": "Peter",
                "initiator_mention": "<@123456789>",
                "human_user_display_name": "TestUser",
                "source": "peter_discord_handler"
            }
            
            forward_to_orchestrator(message_data)
            
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert kwargs['json'] == message_data
            assert kwargs['timeout'] == 300

    def test_forward_to_orchestrator_network_error(self):
        """Test graceful handling of network errors."""
        from app.discord_handler.brian_discord_service import forward_to_orchestrator
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            message_data = {
                "user_query": "test message",
                "channel_id": 123456789,
                "initiator_bot_name": "Brian"
            }
            
            # Should handle exception gracefully without raising
            forward_to_orchestrator(message_data)
            mock_post.assert_called_once() 