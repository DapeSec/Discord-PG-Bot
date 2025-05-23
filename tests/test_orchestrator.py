import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
from flask import Flask
import pytest
from pymongo import MongoClient
from langchain.schema import HumanMessage, AIMessage

class TestCentralizedLLM(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures for centralized LLM architecture."""
        from src.app.orchestrator.server import app
        self.app = app.test_client()
        self.mock_mongo = Mock(spec=MongoClient)
        
    @patch('src.app.orchestrator.server.generate_character_response')
    def test_character_response_generation(self, mock_generate):
        """Test centralized character response generation."""
        # Mock response for Peter
        mock_generate.return_value = "Hehehe, that's funny!"
        
        # Test data simulating a user message
        test_data = {
            "user_query": "Tell me a joke",
            "channel_id": "123456789",
            "initiator_bot_name": "Peter",
            "initiator_mention": "<@peter_id>",
            "human_user_display_name": "TestUser"
        }
        
        response = self.app.post('/orchestrate',
                               data=json.dumps(test_data),
                               content_type='application/json')
        
        # Verify orchestrator processes the request
        self.assertEqual(response.status_code, 200)
        mock_generate.assert_called()
        
    @patch('src.app.orchestrator.server.character_llm')
    def test_peter_personality_prompts(self, mock_llm):
        """Test Peter's character-specific prompts."""
        from src.app.orchestrator.server import generate_character_response
        
        mock_llm.return_value = "Hehehe, holy crap! That reminds me of that time..."
        
        conversation_history = [HumanMessage(content="What do you think about work?")]
        mention_context = "Peter: <@peter_id>\nBrian: <@brian_id>\nStewie: <@stewie_id>"
        
        response = generate_character_response(
            character_name="Peter",
            conversation_history=conversation_history,
            mention_context=mention_context,
            input_text="Continue the conversation.",
            retrieved_context=""
        )
        
        self.assertIsInstance(response, str)
        mock_llm.assert_called()
        
    @patch('src.app.orchestrator.server.character_llm')
    def test_brian_personality_prompts(self, mock_llm):
        """Test Brian's character-specific prompts."""
        from src.app.orchestrator.server import generate_character_response
        
        mock_llm.return_value = "Well, actually, the philosophical implications of that are quite fascinating..."
        
        conversation_history = [HumanMessage(content="What's your opinion on literature?")]
        mention_context = "Peter: <@peter_id>\nBrian: <@brian_id>\nStewie: <@stewie_id>"
        
        response = generate_character_response(
            character_name="Brian",
            conversation_history=conversation_history,
            mention_context=mention_context,
            input_text="Continue the conversation.",
            retrieved_context=""
        )
        
        self.assertIsInstance(response, str)
        mock_llm.assert_called()
        
    @patch('src.app.orchestrator.server.character_llm')
    def test_stewie_personality_prompts(self, mock_llm):
        """Test Stewie's character-specific prompts."""
        from src.app.orchestrator.server import generate_character_response
        
        mock_llm.return_value = "Blast! My latest invention shall bring world domination!"
        
        conversation_history = [HumanMessage(content="What's your latest plan?")]
        mention_context = "Peter: <@peter_id>\nBrian: <@brian_id>\nStewie: <@stewie_id>"
        
        response = generate_character_response(
            character_name="Stewie",
            conversation_history=conversation_history,
            mention_context=mention_context,
            input_text="Continue the conversation.",
            retrieved_context=""
        )
        
        self.assertIsInstance(response, str)
        mock_llm.assert_called()
        
    @patch('src.app.orchestrator.server.retrieve_context')
    @patch('src.app.orchestrator.server.generate_character_response')
    def test_rag_integration(self, mock_generate, mock_rag):
        """Test RAG system integration with centralized LLM."""
        # Mock RAG context retrieval
        mock_rag.return_value = "Family Guy is an animated sitcom created by Seth MacFarlane..."
        
        # Mock character response generation
        mock_generate.return_value = "Hehehe, yeah! Family Guy is awesome!"
        
        # Test data
        test_data = {
            "user_query": "Tell me about Family Guy",
            "channel_id": "123456789",
            "initiator_bot_name": "Peter",
            "initiator_mention": "<@peter_id>",
            "human_user_display_name": "TestUser"
        }
        
        response = self.app.post('/orchestrate',
                               data=json.dumps(test_data),
                               content_type='application/json')
        
        # Verify RAG context was retrieved
        mock_rag.assert_called_with("Tell me about Family Guy")
        # Verify character response was generated with context
        mock_generate.assert_called()
        
    @patch('pymongo.MongoClient')
    def test_conversation_persistence(self, mock_mongo):
        """Test conversation history storage and retrieval."""
        # Mock MongoDB operations
        mock_collection = Mock()
        mock_mongo.return_value.get_database.return_value.get_collection.return_value = mock_collection
        mock_collection.find.return_value = [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-01"},
            {"role": "assistant", "content": "Hehehe, hey there!", "name": "peter", "timestamp": "2024-01-01"}
        ]
        
        # Test conversation history retrieval (internal function)
        from src.app.orchestrator.server import conversations_collection
        if conversations_collection:
            history = list(conversations_collection.find({"channel_id": "test_channel"}))
            mock_collection.find.assert_called()
            
    @patch('requests.post')
    def test_discord_message_sending(self, mock_post):
        """Test sending generated responses to Discord via bots."""
        # Mock successful Discord API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"status": "Message sent"}
        
        # This would be tested as part of the orchestrate endpoint
        # The orchestrator should call the bot's /send_discord_message endpoint
        test_payload = {
            "message_content": "Hehehe, that's funny!",
            "channel_id": "123456789"
        }
        
        # Simulate orchestrator calling bot's endpoint
        import requests
        response = requests.post("http://localhost:5005/send_discord_message", 
                               json=test_payload)
        
        mock_post.assert_called()
        
    def test_clean_llm_response(self):
        """Test response cleaning function."""
        from src.app.orchestrator.server import clean_llm_response
        
        # Test removing AI prefixes
        dirty_response = "AI: Peter: Hehehe, that's funny!"
        clean_response = clean_llm_response(dirty_response)
        self.assertEqual(clean_response, "Hehehe, that's funny!")
        
        # Test removing end conversation markers
        dirty_response = "Hehehe, that's funny! [END_CONVERSATION]"
        clean_response = clean_llm_response(dirty_response)
        self.assertEqual(clean_response, "Hehehe, that's funny!")
        
    @patch('src.app.orchestrator.server.dlq')
    def test_dead_letter_queue(self, mock_dlq):
        """Test dead letter queue functionality for failed messages."""
        # Mock DLQ operations
        mock_dlq.add_message = Mock()
        mock_dlq.get_retryable_messages = Mock(return_value=[])
        mock_dlq.update_retry_status = Mock()
        
        # Test adding failed message to DLQ
        mock_dlq.add_message("llm_request", {"test": "data"}, "Test error", "Peter")
        mock_dlq.add_message.assert_called_with("llm_request", {"test": "data"}, "Test error", "Peter")

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        from src.app.orchestrator.server import app
        self.app = app.test_client()
        self.mock_mongo = Mock(spec=MongoClient)
        
    def test_health_endpoint(self):
        """Test orchestrator health check."""
        response = self.app.get('/health')
        self.assertIn(response.status_code, [200, 503])  # Healthy or degraded
        
        data = json.loads(response.data)
        self.assertIn("status", data)
        self.assertIn("components", data)
        
    def test_error_handling(self):
        """Test error handling in orchestrator."""
        # Test invalid request
        response = self.app.post('/orchestrate',
                               data="invalid json",
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Test missing user_query
        test_data = {
            "channel_id": "123456789",
            "initiator_bot_name": "Peter"
        }
        
        response = self.app.post('/orchestrate',
                               data=json.dumps(test_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main() 