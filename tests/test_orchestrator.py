import unittest
from unittest.mock import Mock, patch, AsyncMock
import json
from flask import Flask
import pytest
from pymongo import MongoClient

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        from src.app.orchestrator.server import app
        self.app = app.test_client()
        self.mock_mongo = Mock(spec=MongoClient)
        
    @patch('pymongo.MongoClient')
    def test_message_queue(self, mock_mongo):
        """Test message queue functionality."""
        # Test data
        test_message = {
            "content": "Test message",
            "author": "test_user",
            "channel_id": "123456789",
            "session_id": "test_session"
        }
        
        # Test adding message to queue
        response = self.app.post('/queue_message', 
                               data=json.dumps(test_message),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
    @patch('requests.post')
    def test_bot_communication(self, mock_post):
        """Test communication with individual bots."""
        # Mock successful bot response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"response": "Test response"}
        
        # Test data
        test_data = {
            "message": "Test message",
            "bot": "peter"
        }
        
        response = self.app.post('/send_to_bot',
                               data=json.dumps(test_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
    @patch('pymongo.MongoClient')
    def test_conversation_history(self, mock_mongo):
        """Test conversation history storage and retrieval."""
        # Mock MongoDB operations
        mock_collection = Mock()
        mock_mongo.return_value.get_database.return_value.get_collection.return_value = mock_collection
        mock_collection.find.return_value = [
            {"content": "Test message 1"},
            {"content": "Test message 2"}
        ]
        
        # Test retrieving conversation history
        response = self.app.get('/conversation_history/test_channel')
        self.assertEqual(response.status_code, 200)
        
    def test_error_handling(self):
        """Test error handling in orchestrator."""
        # Test invalid request
        response = self.app.post('/queue_message',
                               data="invalid json",
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
    @patch('src.app.orchestrator.server.process_rag_context')
    def test_rag_integration(self, mock_rag):
        """Test RAG system integration."""
        # Mock RAG response
        mock_rag.return_value = {
            "context": "Test context",
            "relevance_score": 0.85
        }
        
        # Test data
        test_data = {
            "query": "Test query",
            "bot": "peter"
        }
        
        response = self.app.post('/get_context',
                               data=json.dumps(test_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        
if __name__ == '__main__':
    unittest.main() 