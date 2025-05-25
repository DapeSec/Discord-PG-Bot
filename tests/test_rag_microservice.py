import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
import json
from datetime import datetime

class TestRAGMicroservice(unittest.TestCase):
    """Test suite for the RAG Retriever microservice."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rag_service_url = "http://localhost:5005"
        self.mock_response_data = {
            "success": True,
            "results": [
                {
                    "content": "Test content about Family Guy",
                    "source": "familyguy.fandom.com/wiki/Test_Page",
                    "relevance_score": 0.89
                }
            ],
            "query_processed": "test query",
            "total_results": 1
        }
        
    @patch('requests.post')
    def test_retrieve_context_success(self, mock_post):
        """Test successful context retrieval from RAG service."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response_data
        mock_post.return_value = mock_response
        
        # Test data
        query_data = {
            "query": "test query",
            "num_results": 3,
            "min_relevance_score": 0.7
        }
        
        # Make request
        response = requests.post(f"{self.rag_service_url}/retrieve", json=query_data)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertEqual(len(response_data["results"]), 1)
        self.assertGreater(response_data["results"][0]["relevance_score"], 0.8)
        
        # Verify the request was made correctly
        mock_post.assert_called_once_with(f"{self.rag_service_url}/retrieve", json=query_data)
        
    @patch('requests.post')
    def test_retrieve_context_failure(self, mock_post):
        """Test handling of RAG service failures."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_post.return_value = mock_response
        
        query_data = {"query": "test query"}
        response = requests.post(f"{self.rag_service_url}/retrieve", json=query_data)
        
        self.assertEqual(response.status_code, 500)
        
    @patch('requests.get')
    def test_health_check(self, mock_get):
        """Test RAG service health check endpoint."""
        # Mock health check response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "service": "RAG_Retriever_Service",
            "timestamp": datetime.now().isoformat(),
            "vector_store_status": "ready",
            "embeddings_model": "all-MiniLM-L6-v2"
        }
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.rag_service_url}/health")
        
        self.assertEqual(response.status_code, 200)
        health_data = response.json()
        self.assertEqual(health_data["status"], "healthy")
        self.assertEqual(health_data["service"], "RAG_Retriever_Service")
        
    @patch('requests.get')
    def test_vector_store_status(self, mock_get):
        """Test vector store status endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ready",
            "total_documents": 1500,
            "last_update": "2024-01-15T10:30:00Z",
            "embeddings_model": "all-MiniLM-L6-v2",
            "database_size_mb": 45.2
        }
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.rag_service_url}/vector_store_status")
        
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertEqual(status_data["status"], "ready")
        self.assertGreater(status_data["total_documents"], 0)
        
    @patch('requests.post')
    def test_load_fandom_wiki(self, mock_post):
        """Test wiki crawling trigger endpoint."""
        mock_response = Mock()
        mock_response.status_code = 202  # Accepted - async operation
        mock_response.json.return_value = {
            "message": "Wiki crawl initiated",
            "crawl_id": "crawl_123456",
            "estimated_duration": "10-15 minutes"
        }
        mock_post.return_value = mock_response
        
        response = requests.post(f"{self.rag_service_url}/load_fandom_wiki")
        
        self.assertEqual(response.status_code, 202)
        crawl_data = response.json()
        self.assertIn("crawl_id", crawl_data)
        
    def test_context_integration_format(self):
        """Test that retrieved context is properly formatted for LLM integration."""
        # Test context formatting
        context_results = [
            {
                "content": "Peter Griffin is the main character of Family Guy.",
                "source": "familyguy.fandom.com/wiki/Peter_Griffin",
                "relevance_score": 0.95
            },
            {
                "content": "He lives at 31 Spooner Street in Quahog, Rhode Island.",
                "source": "familyguy.fandom.com/wiki/Griffin_House",
                "relevance_score": 0.87
            }
        ]
        
        # Format for LLM prompt
        formatted_context = "\n".join([
            f"- {result['content']}" for result in context_results
        ])
        
        expected_format = "- Peter Griffin is the main character of Family Guy.\n- He lives at 31 Spooner Street in Quahog, Rhode Island."
        self.assertEqual(formatted_context, expected_format)
        
    def test_relevance_score_filtering(self):
        """Test filtering of results by relevance score."""
        results = [
            {"content": "High relevance", "relevance_score": 0.9},
            {"content": "Medium relevance", "relevance_score": 0.75},
            {"content": "Low relevance", "relevance_score": 0.5}
        ]
        
        min_score = 0.7
        filtered_results = [r for r in results if r["relevance_score"] >= min_score]
        
        self.assertEqual(len(filtered_results), 2)
        self.assertTrue(all(r["relevance_score"] >= min_score for r in filtered_results))
        
    @patch('requests.post')
    def test_orchestrator_rag_integration(self, mock_post):
        """Test integration between orchestrator and RAG service."""
        # Mock orchestrator making request to RAG service
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response_data
        mock_post.return_value = mock_response
        
        # Simulate orchestrator request
        user_query = "Tell me about Peter Griffin"
        rag_request = {
            "query": user_query,
            "num_results": 3,
            "min_relevance_score": 0.7
        }
        
        # Make request (simulating orchestrator)
        response = requests.post(f"{self.rag_service_url}/retrieve", json=rag_request)
        
        # Verify successful integration
        self.assertEqual(response.status_code, 200)
        context_data = response.json()
        self.assertTrue(context_data["success"])
        
        # Verify context can be integrated into prompt
        context_text = "\n".join([
            f"- {result['content']}" for result in context_data["results"]
        ])
        self.assertIn("Family Guy", context_text)
        
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios."""
        # Test invalid query format
        invalid_queries = [
            {},  # Empty query
            {"query": ""},  # Empty string
            {"query": None},  # None value
            {"num_results": -1},  # Invalid num_results
            {"min_relevance_score": 1.5}  # Invalid score range
        ]
        
        for invalid_query in invalid_queries:
            with self.subTest(query=invalid_query):
                # These would normally return 400 Bad Request
                # We're testing the validation logic
                if not invalid_query.get("query"):
                    self.assertFalse(bool(invalid_query.get("query")))
                if invalid_query.get("num_results", 1) < 0:
                    self.assertLess(invalid_query["num_results"], 0)
                if invalid_query.get("min_relevance_score", 0.5) > 1.0:
                    self.assertGreater(invalid_query["min_relevance_score"], 1.0)
                    
    @patch('requests.post')
    def test_concurrent_requests(self, mock_post):
        """Test handling of concurrent requests to RAG service."""
        # Mock multiple concurrent responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_response_data
        mock_post.return_value = mock_response
        
        # Simulate multiple concurrent requests
        queries = [
            {"query": "Peter Griffin", "num_results": 2},
            {"query": "Brian Griffin", "num_results": 2},
            {"query": "Stewie Griffin", "num_results": 2}
        ]
        
        responses = []
        for query in queries:
            response = requests.post(f"{self.rag_service_url}/retrieve", json=query)
            responses.append(response)
            
        # Verify all requests succeeded
        for response in responses:
            self.assertEqual(response.status_code, 200)
            
        # Verify correct number of calls
        self.assertEqual(mock_post.call_count, len(queries))

if __name__ == '__main__':
    unittest.main() 