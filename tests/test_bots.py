import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
import json
from flask import Flask

class TestBotInterfaces(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures for bot Discord interfaces."""
        self.mock_discord = Mock()
        
    def test_peter_bot_health_check(self):
        """Test Peter bot's health endpoint."""
        from src.app.bots.peter_bot import app
        client = app.test_client()
        
        response = client.get('/health')
        self.assertIn(response.status_code, [200, 503])  # Healthy or degraded
        
        data = json.loads(response.data)
        self.assertIn("status", data)
        self.assertEqual(data["bot_name"], "Peter")
        self.assertIn("components", data)
        
    def test_brian_bot_health_check(self):
        """Test Brian bot's health endpoint."""
        from src.app.bots.brian_bot import app
        client = app.test_client()
        
        response = client.get('/health')
        self.assertIn(response.status_code, [200, 503])
        
        data = json.loads(response.data)
        self.assertIn("status", data)
        self.assertEqual(data["bot_name"], "Brian")
        
    def test_stewie_bot_health_check(self):
        """Test Stewie bot's health endpoint."""
        from src.app.bots.stewie_bot import app
        client = app.test_client()
        
        response = client.get('/health')
        self.assertIn(response.status_code, [200, 503])
        
        data = json.loads(response.data)
        self.assertIn("status", data)
        self.assertEqual(data["bot_name"], "Stewie")

class TestDiscordMessageHandling(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures for Discord message handling."""
        self.mock_discord_client = Mock()
        
    def test_peter_send_discord_message_endpoint(self):
        """Test Peter bot's send_discord_message endpoint."""
        from src.app.bots.peter_bot import app
        client = app.test_client()
        
        test_data = {
            "message_content": "Hehehe, that's funny!",
            "channel_id": "123456789"
        }
        
        with patch('src.app.bots.peter_bot.client') as mock_client:
            mock_client.loop.create_task = Mock()
            
            response = client.post('/send_discord_message',
                                 data=json.dumps(test_data),
                                 content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data["status"], "Message sent to Discord channel")
            
    def test_brian_send_discord_message_endpoint(self):
        """Test Brian bot's send_discord_message endpoint."""
        from src.app.bots.brian_bot import app
        client = app.test_client()
        
        test_data = {
            "message_content": "Well, actually, that's quite interesting.",
            "channel_id": "123456789"
        }
        
        with patch('src.app.bots.brian_bot.client') as mock_client:
            mock_client.loop.create_task = Mock()
            
            response = client.post('/send_discord_message',
                                 data=json.dumps(test_data),
                                 content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            
    def test_stewie_send_discord_message_endpoint(self):
        """Test Stewie bot's send_discord_message endpoint."""
        from src.app.bots.stewie_bot import app
        client = app.test_client()
        
        test_data = {
            "message_content": "Blast! Victory shall be mine!",
            "channel_id": "123456789"
        }
        
        with patch('src.app.bots.stewie_bot.client') as mock_client:
            mock_client.loop.create_task = Mock()
            
            response = client.post('/send_discord_message',
                                 data=json.dumps(test_data),
                                 content_type='application/json')
            
            self.assertEqual(response.status_code, 200)

class TestConversationInitiation(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures for conversation initiation."""
        self.mock_discord_client = Mock()
        
    @patch('requests.post')
    def test_peter_initiate_conversation(self, mock_post):
        """Test Peter bot's conversation initiation endpoint."""
        from src.app.bots.peter_bot import app
        client = app.test_client()
        
        # Mock successful orchestrator response
        mock_post.return_value.status_code = 200
        
        test_data = {
            "conversation_starter_prompt": "Hehehe, hey everyone!",
            "channel_id": "123456789",
            "is_new_conversation": True,
            "conversation_session_id": "test_session_123"
        }
        
        with patch('src.app.bots.peter_bot.client') as mock_client:
            mock_client.loop.create_task = Mock()
            
            response = client.post('/initiate_conversation',
                                 data=json.dumps(test_data),
                                 content_type='application/json')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data["status"], "Initial conversation message scheduled and orchestrator informed")

class TestBotErrorHandling(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures for error handling."""
        pass
        
    def test_missing_message_content(self):
        """Test handling of missing message content."""
        from src.app.bots.peter_bot import app
        client = app.test_client()
        
        # Missing message_content
        test_data = {
            "channel_id": "123456789"
        }
        
        response = client.post('/send_discord_message',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)
        
    def test_missing_channel_id(self):
        """Test handling of missing channel ID."""
        from src.app.bots.brian_bot import app
        client = app.test_client()
        
        # Missing channel_id
        test_data = {
            "message_content": "Test message"
        }
        
        response = client.post('/send_discord_message',
                             data=json.dumps(test_data),
                             content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
    def test_invalid_json(self):
        """Test handling of invalid JSON."""
        from src.app.bots.stewie_bot import app
        client = app.test_client()
        
        response = client.post('/send_discord_message',
                             data="invalid json",
                             content_type='application/json')
        
        self.assertEqual(response.status_code, 400)

class TestDiscordIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures for Discord integration."""
        self.mock_channel = Mock()
        self.mock_message = Mock()
        
    @patch('discord.Client')
    async def test_discord_message_reception(self, mock_client):
        """Test Discord message reception and processing."""
        # Mock Discord message
        self.mock_message.author.id = 12345
        self.mock_message.content = "!peter Hello there"
        self.mock_message.channel.id = 123456789
        self.mock_message.author.display_name = "TestUser"
        
        # Mock that message is not from the bot itself
        mock_client.user.id = 99999  # Different from author ID
        
        # This test would require more complex setup to properly test
        # the on_message event handler. For now, we verify the structure exists.
        from src.app.bots.peter_bot import client
        self.assertIsNotNone(client)

if __name__ == '__main__':
    unittest.main() 