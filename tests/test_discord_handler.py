import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.discord_handler.discord_service import app, bot_clients, setup_discord_events

@pytest.fixture
def client():
    """Create a test client for the Discord Handler Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestDiscordHandler:
    """Test suite for Discord Handler Service."""

    def test_health_check_healthy(self, client):
        """Test health check when all Discord clients are ready."""
        # Mock all clients as ready
        for bot_client in bot_clients.values():
            bot_client.is_ready = Mock(return_value=True)
        
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'DiscordHandler'
        assert 'discord_clients' in data

    def test_health_check_degraded(self, client):
        """Test health check when some Discord clients are not ready."""
        # Mock some clients as not ready
        bot_clients["Peter"].is_ready = Mock(return_value=True)
        bot_clients["Brian"].is_ready = Mock(return_value=False)
        bot_clients["Stewie"].is_ready = Mock(return_value=True)
        
        response = client.get('/health')
        assert response.status_code == 503
        
        data = json.loads(response.data)
        assert data['status'] == 'degraded'

    def test_send_message_success(self, client):
        """Test successful message sending."""
        # Mock Discord client
        mock_client = Mock()
        mock_client.is_ready.return_value = True
        mock_client.loop = Mock()
        mock_client.loop.is_running.return_value = True
        
        bot_clients["Peter"] = mock_client
        
        # Mock asyncio.run_coroutine_threadsafe
        with patch('asyncio.run_coroutine_threadsafe') as mock_run:
            mock_future = Mock()
            mock_future.result.return_value = None
            mock_run.return_value = mock_future
            
            response = client.post('/send_message', 
                json={
                    "bot_name": "Peter",
                    "channel_id": "123456789",
                    "message_content": "Holy crap! This is a test!"
                })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'Message sent successfully'

    def test_send_message_invalid_bot(self, client):
        """Test sending message with invalid bot name."""
        response = client.post('/send_message', 
            json={
                "bot_name": "InvalidBot",
                "channel_id": "123456789",
                "message_content": "Test message"
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Unknown bot' in data['error']

    def test_send_message_missing_fields(self, client):
        """Test sending message with missing required fields."""
        response = client.post('/send_message', 
            json={
                "bot_name": "Peter",
                "channel_id": "123456789"
                # Missing message_content
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Missing required fields' in data['error']

    def test_send_message_client_not_ready(self, client):
        """Test sending message when Discord client is not ready."""
        mock_client = Mock()
        mock_client.is_ready.return_value = False
        bot_clients["Peter"] = mock_client
        
        response = client.post('/send_message', 
            json={
                "bot_name": "Peter",
                "channel_id": "123456789",
                "message_content": "Test message"
            })
        
        assert response.status_code == 503
        data = json.loads(response.data)
        assert 'not ready' in data['error']

    def test_get_bot_info_success(self, client):
        """Test getting bot information when clients are ready."""
        # Mock clients with user info
        for name, bot_client in bot_clients.items():
            bot_client.is_ready.return_value = True
            mock_user = Mock()
            mock_user.id = 123456789
            mock_user.name = f"{name}Bot"
            bot_client.user = mock_user
        
        response = client.get('/bot_info')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'Peter' in data
        assert 'Brian' in data
        assert 'Stewie' in data
        
        for name in ['Peter', 'Brian', 'Stewie']:
            assert data[name]['ready'] is True
            assert 'id' in data[name]
            assert 'username' in data[name]
            assert 'mention' in data[name]

    def test_get_bot_info_not_ready(self, client):
        """Test getting bot information when clients are not ready."""
        for bot_client in bot_clients.values():
            bot_client.is_ready.return_value = False
        
        response = client.get('/bot_info')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        for name in ['Peter', 'Brian', 'Stewie']:
            assert data[name]['ready'] is False

    @patch('src.app.discord_handler.discord_service.requests.post')
    def test_forward_to_orchestrator_success(self, mock_post):
        """Test successful forwarding to orchestrator."""
        from app.discord_handler.discord_service import forward_to_orchestrator
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        message_data = {
            "user_query": "test message",
            "channel_id": "123456789",
            "initiator_bot_name": "Peter"
        }
        
        # Should not raise any exceptions
        forward_to_orchestrator(message_data)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['json'] == message_data
        assert kwargs['timeout'] == 120

    @patch('src.app.discord_handler.discord_service.requests.post')
    def test_forward_to_orchestrator_failure(self, mock_post):
        """Test forwarding to orchestrator with network failure."""
        from app.discord_handler.discord_service import forward_to_orchestrator
        
        mock_post.side_effect = Exception("Network error")
        
        message_data = {
            "user_query": "test message",
            "channel_id": "123456789",
            "initiator_bot_name": "Peter"
        }
        
        # Should handle exception gracefully
        forward_to_orchestrator(message_data)
        mock_post.assert_called_once()

class TestDiscordEventHandling:
    """Test Discord event handling logic."""

    @pytest.mark.asyncio
    async def test_handle_discord_message_with_mention(self):
        """Test handling Discord message with bot mention."""
        from app.discord_handler.discord_service import handle_discord_message, bot_mentions, bot_ids
        
        # Setup mock data
        bot_mentions["Peter"] = "<@123456789>"
        bot_ids["Peter"] = 123456789
        
        mock_message = Mock()
        mock_message.author.id = 987654321  # Different from bot IDs
        mock_message.author.display_name = "TestUser"
        mock_message.content = "<@123456789> Hello Peter!"
        mock_message.channel.id = 555666777
        mock_message.channel.send = AsyncMock()
        
        with patch('threading.Thread') as mock_thread:
            await handle_discord_message(mock_message, "Brian")
            
            # Should start a thread to forward to orchestrator
            mock_thread.assert_called_once()
            args, kwargs = mock_thread.call_args
            assert kwargs['daemon'] is True

    @pytest.mark.asyncio
    async def test_handle_discord_message_from_bot(self):
        """Test ignoring messages from bot users."""
        from app.discord_handler.discord_service import handle_discord_message, bot_ids
        
        # Setup bot IDs
        bot_ids["Peter"] = 123456789
        
        mock_message = Mock()
        mock_message.author.id = 123456789  # Same as bot ID
        
        with patch('threading.Thread') as mock_thread:
            await handle_discord_message(mock_message, "Peter")
            
            # Should not start any thread
            mock_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_discord_message_empty_content(self):
        """Test handling message with empty content after processing."""
        from app.discord_handler.discord_service import handle_discord_message, bot_mentions, bot_ids
        
        # Setup mock data
        bot_mentions["Peter"] = "<@123456789>"
        bot_ids["Peter"] = 123456789
        
        mock_message = Mock()
        mock_message.author.id = 987654321
        mock_message.author.display_name = "TestUser"
        mock_message.content = "<@123456789>"  # Only mention, no actual content
        mock_message.channel.send = AsyncMock()
        
        with patch('threading.Thread') as mock_thread:
            await handle_discord_message(mock_message, "Peter")
            
            # Should send default response and not forward to orchestrator
            mock_message.channel.send.assert_called_once_with("Yes? What can I do for you?")
            mock_thread.assert_not_called()

if __name__ == '__main__':
    pytest.main([__file__]) 