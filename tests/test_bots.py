import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
import json
from langchain.schema import HumanMessage, AIMessage

class TestBots(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_discord = Mock()
        self.mock_ollama = Mock()
        self.mock_db = Mock()
        
    @patch('discord.Client')
    @patch('langchain_community.llms.Ollama')
    async def test_peter_bot_response(self, mock_ollama, mock_client):
        """Test Peter bot's response generation."""
        from peter_bot import generate_peter_response
        
        # Mock LLM response
        mock_ollama.return_value.predict.return_value = "Hehehe, that's funny!"
        
        # Test input
        messages = [
            HumanMessage(content="Tell me a joke"),
            AIMessage(content="Here's a joke...")
        ]
        
        response = await generate_peter_response(messages)
        self.assertIn("Hehehe", response)
        mock_ollama.return_value.predict.assert_called_once()

    @patch('discord.Client')
    @patch('langchain_community.llms.Ollama')
    async def test_brian_bot_response(self, mock_ollama, mock_client):
        """Test Brian bot's response generation."""
        from brian_bot import generate_brian_response
        
        # Mock LLM response
        mock_ollama.return_value.predict.return_value = "Well, actually..."
        
        # Test input
        messages = [
            HumanMessage(content="What do you think about literature?"),
            AIMessage(content="Literature is...")
        ]
        
        response = await generate_brian_response(messages)
        self.assertIn("Well", response)
        mock_ollama.return_value.predict.assert_called_once()

    @patch('discord.Client')
    @patch('langchain_community.llms.Ollama')
    async def test_stewie_bot_response(self, mock_ollama, mock_client):
        """Test Stewie bot's response generation."""
        from stewie_bot import generate_stewie_response
        
        # Mock LLM response
        mock_ollama.return_value.predict.return_value = "Victory shall be mine!"
        
        # Test input
        messages = [
            HumanMessage(content="What's your evil plan?"),
            AIMessage(content="My plan is...")
        ]
        
        response = await generate_stewie_response(messages)
        self.assertIn("Victory", response)
        mock_ollama.return_value.predict.assert_called_once()

    def test_bot_error_handling(self):
        """Test error handling in bots."""
        # Add error handling tests
        pass

if __name__ == '__main__':
    unittest.main() 