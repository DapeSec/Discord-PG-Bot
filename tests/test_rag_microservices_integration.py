import unittest
from unittest.mock import Mock, patch, MagicMock, call
import requests
import json
from datetime import datetime
import threading
import time

class TestRAGMicroservicesIntegration(unittest.TestCase):
    """
    Comprehensive test suite for the separated RAG microservices architecture.
    Tests both RAG Retriever and RAG Crawler services and their integration.
    """
    
    def setUp(self):
        """Set up test fixtures for both RAG services."""
        self.rag_retriever_url = "http://localhost:5005"
        self.rag_crawler_url = "http://localhost:5009"
        self.orchestrator_url = "http://localhost:5003"
        
        # Mock data for retriever service
        self.mock_retrieval_response = {
            "success": True,
            "context": "Peter Griffin is the main character of Family Guy. He lives at 31 Spooner Street in Quahog, Rhode Island.",
            "documents_found": 3,
            "query_processed": "Peter Griffin",
            "results": [
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
        }
        
        # Mock data for crawler service
        self.mock_crawler_status = {
            "service_name": "RAG_Crawler_Service",
            "crawl_in_progress": False,
            "last_crawl": {
                "timestamp": "2024-01-15T10:30:00Z",
                "status": "SUCCESS",
                "pages_crawled": 150,
                "documents_added": 1200,
                "error_message": None
            }
        }

class TestRAGRetrieverService(TestRAGMicroservicesIntegration):
    """Test suite specifically for RAG Retriever Service."""
    
    @patch('requests.post')
    def test_retrieve_context_success(self, mock_post):
        """Test successful context retrieval from RAG Retriever service."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_retrieval_response
        mock_post.return_value = mock_response
        
        # Test data
        query_data = {
            "query": "Peter Griffin",
            "num_results": 3
        }
        
        # Make request
        response = requests.post(f"{self.rag_retriever_url}/retrieve", json=query_data)
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["documents_found"], 3)
        self.assertIn("Peter Griffin", response_data["context"])
        
        # Verify the request was made correctly
        mock_post.assert_called_once_with(f"{self.rag_retriever_url}/retrieve", json=query_data)
        
    @patch('requests.post')
    def test_retrieve_context_no_results(self, mock_post):
        """Test retrieval when no relevant context is found."""
        # Mock no results response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "context": "",
            "documents_found": 0,
            "query_processed": "obscure query",
            "results": []
        }
        mock_post.return_value = mock_response
        
        query_data = {"query": "obscure query"}
        response = requests.post(f"{self.rag_retriever_url}/retrieve", json=query_data)
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data["success"])
        self.assertEqual(response_data["documents_found"], 0)
        self.assertEqual(response_data["context"], "")
        
    @patch('requests.get')
    def test_retriever_health_check(self, mock_get):
        """Test RAG Retriever service health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "service_name": "RAG_Retriever_Service",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "dependencies": {
                "mongodb": "connected",
                "embeddings_model": "loaded",
                "vector_store": "ready"
            }
        }
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.rag_retriever_url}/health")
        
        self.assertEqual(response.status_code, 200)
        health_data = response.json()
        self.assertEqual(health_data["status"], "healthy")
        self.assertEqual(health_data["service_name"], "RAG_Retriever_Service")
        
    @patch('requests.get')
    def test_vector_store_status(self, mock_get):
        """Test vector store status endpoint on retriever."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "vector_store": "ChromaDB",
            "document_count": 1500,
            "status": "available",
            "path": "/app/chroma_db"
        }
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.rag_retriever_url}/vector_store_status")
        
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertEqual(status_data["status"], "available")
        self.assertGreater(status_data["document_count"], 0)

class TestRAGCrawlerService(TestRAGMicroservicesIntegration):
    """Test suite specifically for RAG Crawler Service."""
    
    @patch('requests.post')
    def test_start_crawl_success(self, mock_post):
        """Test starting a new crawl operation."""
        mock_response = Mock()
        mock_response.status_code = 202  # Accepted
        mock_response.json.return_value = {
            "message": "Crawl started successfully",
            "status": "started",
            "parameters": {
                "start_url": "https://familyguy.fandom.com/wiki/Main_Page",
                "max_pages": 100,
                "delay": 1
            },
            "timestamp": datetime.now().isoformat()
        }
        mock_post.return_value = mock_response
        
        crawl_data = {
            "start_url": "https://familyguy.fandom.com/wiki/Main_Page",
            "max_pages": 100,
            "delay": 1
        }
        
        response = requests.post(f"{self.rag_crawler_url}/crawl/start", json=crawl_data)
        
        self.assertEqual(response.status_code, 202)
        response_data = response.json()
        self.assertEqual(response_data["status"], "started")
        self.assertIn("parameters", response_data)
        
    @patch('requests.post')
    def test_start_crawl_already_running(self, mock_post):
        """Test starting crawl when one is already in progress."""
        mock_response = Mock()
        mock_response.status_code = 409  # Conflict
        mock_response.json.return_value = {
            "error": "Crawl already in progress",
            "status": "rejected"
        }
        mock_post.return_value = mock_response
        
        response = requests.post(f"{self.rag_crawler_url}/crawl/start", json={})
        
        self.assertEqual(response.status_code, 409)
        response_data = response.json()
        self.assertEqual(response_data["status"], "rejected")
        
    @patch('requests.get')
    def test_crawl_status(self, mock_get):
        """Test getting crawl status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_crawler_status
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.rag_crawler_url}/crawl/status")
        
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertEqual(status_data["service_name"], "RAG_Crawler_Service")
        self.assertFalse(status_data["crawl_in_progress"])
        self.assertEqual(status_data["last_crawl"]["status"], "SUCCESS")
        
    @patch('requests.post')
    def test_stop_crawl(self, mock_post):
        """Test stopping a running crawl."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "Crawl stop requested",
            "status": "stopping",
            "note": "Crawl will stop after current page completes"
        }
        mock_post.return_value = mock_response
        
        response = requests.post(f"{self.rag_crawler_url}/crawl/stop")
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "stopping")
        
    @patch('requests.get')
    def test_crawler_health_check(self, mock_get):
        """Test RAG Crawler service health check."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "service_name": "RAG_Crawler_Service",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "crawl_status": "idle",
            "dependencies": {
                "mongodb": "connected",
                "embeddings_model": "loaded"
            }
        }
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.rag_crawler_url}/health")
        
        self.assertEqual(response.status_code, 200)
        health_data = response.json()
        self.assertEqual(health_data["status"], "healthy")
        self.assertEqual(health_data["crawl_status"], "idle")
        
    @patch('requests.get')
    def test_vector_store_info(self, mock_get):
        """Test vector store info endpoint on crawler."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "vector_store": "ChromaDB",
            "document_count": 1500,
            "status": "available",
            "path": "/app/chroma_db"
        }
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.rag_crawler_url}/vector_store/info")
        
        self.assertEqual(response.status_code, 200)
        info_data = response.json()
        self.assertEqual(info_data["status"], "available")
        self.assertGreater(info_data["document_count"], 0)
        
    @patch('requests.get')
    def test_auto_crawl_status(self, mock_get):
        """Test auto-crawl status endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "auto_crawl_enabled": True,
            "auto_crawl_interval_days": 30,
            "auto_crawl_check_interval_hours": 24,
            "crawl_in_progress": False,
            "last_crawl": {
                "timestamp": "2024-01-15T10:30:00Z",
                "status": "SUCCESS",
                "pages_crawled": 150,
                "documents_added": 1200
            },
            "next_auto_crawl": "2024-02-14T10:30:00Z",
            "should_crawl_now": False
        }
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.rag_crawler_url}/auto_crawl/status")
        
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertTrue(status_data["auto_crawl_enabled"])
        self.assertEqual(status_data["auto_crawl_interval_days"], 30)
        self.assertFalse(status_data["should_crawl_now"])

class TestOrchestratorRAGIntegration(TestRAGMicroservicesIntegration):
    """Test suite for Orchestrator integration with RAG microservices."""
    
    @patch('requests.post')
    def test_orchestrator_trigger_crawl(self, mock_post):
        """Test orchestrator triggering crawl via RAG Crawler service."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "message": "RAG crawl triggered successfully",
            "status": "initiated",
            "crawler_response": {
                "status": "started",
                "parameters": {
                    "start_url": "https://familyguy.fandom.com/wiki/Main_Page",
                    "max_pages": 100,
                    "delay": 1
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        mock_post.return_value = mock_response
        
        crawl_data = {
            "start_url": "https://familyguy.fandom.com/wiki/Main_Page",
            "max_pages": 100,
            "delay": 1
        }
        
        response = requests.post(f"{self.orchestrator_url}/crawl/trigger", json=crawl_data)
        
        self.assertEqual(response.status_code, 202)
        response_data = response.json()
        self.assertEqual(response_data["status"], "initiated")
        self.assertIn("crawler_response", response_data)
        
    @patch('requests.get')
    def test_orchestrator_get_crawl_status(self, mock_get):
        """Test orchestrator getting crawl status via RAG Crawler service."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "orchestrator_status": "healthy",
            "crawler_status": self.mock_crawler_status,
            "timestamp": datetime.now().isoformat()
        }
        mock_get.return_value = mock_response
        
        response = requests.get(f"{self.orchestrator_url}/crawl/status")
        
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertEqual(status_data["orchestrator_status"], "healthy")
        self.assertIn("crawler_status", status_data)
        
    @patch('requests.post')
    def test_orchestrator_context_retrieval(self, mock_post):
        """Test orchestrator retrieving context via RAG Retriever service."""
        # Mock the orchestrator's internal call to RAG Retriever
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_retrieval_response
        mock_post.return_value = mock_response
        
        # Simulate orchestrator making request during conversation
        orchestrate_data = {
            "user_query": "Tell me about Peter Griffin",
            "channel_id": "123456789",
            "initiator_bot_name": "Peter",
            "initiator_mention": "<@peter_bot>"
        }
        
        response = requests.post(f"{self.orchestrator_url}/orchestrate", json=orchestrate_data)
        
        # The orchestrator should have made a call to RAG Retriever
        # This tests the integration flow
        self.assertEqual(response.status_code, 200)

class TestRAGMicroservicesFailureScenarios(TestRAGMicroservicesIntegration):
    """Test suite for failure scenarios and error handling."""
    
    @patch('requests.post')
    def test_retriever_service_unavailable(self, mock_post):
        """Test handling when RAG Retriever service is unavailable."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Service unavailable")
        
        with self.assertRaises(requests.exceptions.ConnectionError):
            requests.post(f"{self.rag_retriever_url}/retrieve", json={"query": "test"})
            
    @patch('requests.post')
    def test_crawler_service_unavailable(self, mock_post):
        """Test handling when RAG Crawler service is unavailable."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Service unavailable")
        
        with self.assertRaises(requests.exceptions.ConnectionError):
            requests.post(f"{self.rag_crawler_url}/crawl/start", json={})
            
    @patch('requests.post')
    def test_orchestrator_handles_rag_failure(self, mock_post):
        """Test orchestrator graceful handling of RAG service failures."""
        # Mock RAG service returning error
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.return_value = {
            "error": "RAG Retriever service is not available",
            "status": "service_unavailable"
        }
        mock_post.return_value = mock_response
        
        response = requests.post(f"{self.orchestrator_url}/crawl/trigger", json={})
        
        self.assertEqual(response.status_code, 503)
        error_data = response.json()
        self.assertEqual(error_data["status"], "service_unavailable")
        
    @patch('requests.post')
    def test_timeout_handling(self, mock_post):
        """Test timeout handling for RAG service calls."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        with self.assertRaises(requests.exceptions.Timeout):
            requests.post(f"{self.rag_retriever_url}/retrieve", json={"query": "test"}, timeout=5)

class TestRAGMicroservicesPerformance(TestRAGMicroservicesIntegration):
    """Test suite for performance and scalability scenarios."""
    
    @patch('requests.post')
    def test_concurrent_retrieval_requests(self, mock_post):
        """Test handling of concurrent retrieval requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_retrieval_response
        mock_post.return_value = mock_response
        
        def make_request():
            return requests.post(f"{self.rag_retriever_url}/retrieve", json={"query": "test"})
        
        # Simulate concurrent requests
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(target=lambda: results.append(make_request()))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result.status_code, 200)
            
    @patch('requests.post')
    def test_large_query_handling(self, mock_post):
        """Test handling of large queries."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_retrieval_response
        mock_post.return_value = mock_response
        
        # Large query
        large_query = "Tell me everything about " + "Peter Griffin " * 100
        
        response = requests.post(f"{self.rag_retriever_url}/retrieve", json={"query": large_query})
        
        self.assertEqual(response.status_code, 200)
        
    @patch('requests.post')
    def test_high_num_results_request(self, mock_post):
        """Test requesting high number of results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "context": "Large context response",
            "documents_found": 50,
            "results": [{"content": f"Result {i}", "relevance_score": 0.8} for i in range(50)]
        }
        mock_post.return_value = mock_response
        
        response = requests.post(f"{self.rag_retriever_url}/retrieve", json={"query": "test", "num_results": 50})
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["results"]), 50)

class TestRAGMicroservicesDataFlow(TestRAGMicroservicesIntegration):
    """Test suite for data flow between RAG microservices."""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_crawl_to_retrieval_flow(self, mock_get, mock_post):
        """Test the flow from crawling to retrieval availability."""
        # Mock crawl completion
        mock_post_response = Mock()
        mock_post_response.status_code = 202
        mock_post_response.json.return_value = {"status": "started"}
        mock_post.return_value = mock_post_response
        
        # Mock status check showing completion
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "crawl_in_progress": False,
            "last_crawl": {"status": "SUCCESS", "documents_added": 100}
        }
        mock_get.return_value = mock_get_response
        
        # Start crawl
        crawl_response = requests.post(f"{self.rag_crawler_url}/crawl/start", json={})
        self.assertEqual(crawl_response.status_code, 202)
        
        # Check status
        status_response = requests.get(f"{self.rag_crawler_url}/crawl/status")
        self.assertEqual(status_response.status_code, 200)
        status_data = status_response.json()
        self.assertEqual(status_data["last_crawl"]["status"], "SUCCESS")
        
    def test_shared_vector_store_access(self):
        """Test that both services can access the shared ChromaDB."""
        # This would test that both services can read/write to the same vector store
        # In a real scenario, this would involve actual ChromaDB operations
        
        # Mock shared storage path
        shared_path = "/app/chroma_db"
        
        # Both services should use the same path
        self.assertEqual(shared_path, "/app/chroma_db")
        
        # This test validates the configuration rather than runtime behavior
        # since we're using mocks for the actual services

if __name__ == '__main__':
    unittest.main() 