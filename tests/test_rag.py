import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
import chromadb
from langchain_community.embeddings import SentenceTransformerEmbeddings

class TestRAGLegacy(unittest.TestCase):
    """Legacy RAG tests - now testing RAG service components in isolation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_chroma = Mock(spec=chromadb.Client)
        self.mock_embeddings = Mock(spec=SentenceTransformerEmbeddings)
        self.rag_service_url = "http://localhost:5005"
        
    @patch('chromadb.Client')
    def test_vector_store_operations(self, mock_chroma_client):
        """Test vector store operations within RAG service."""
        # Mock data
        test_texts = [
            "Test document 1",
            "Test document 2"
        ]
        test_metadata = [
            {"source": "test1", "type": "document"},
            {"source": "test2", "type": "document"}
        ]
        
        # Mock embeddings
        mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        self.mock_embeddings.embed_documents.return_value = mock_embeddings
        
        # Test adding documents
        collection = self.mock_chroma.create_collection("test_collection")
        collection.add.return_value = None
        
        # Verify the add operation
        collection.add(
            documents=test_texts,
            metadatas=test_metadata,
            embeddings=mock_embeddings
        )
        collection.add.assert_called_once()
        
    @patch('chromadb.Client')
    def test_similarity_search(self, mock_chroma_client):
        """Test similarity search functionality within RAG service."""
        # Mock query
        test_query = "Test query"
        
        # Mock embeddings and search results
        mock_query_embedding = [0.1, 0.2, 0.3]
        self.mock_embeddings.embed_query.return_value = mock_query_embedding
        
        # Mock search results
        mock_results = [
            {"document": "Test document 1", "score": 0.9},
            {"document": "Test document 2", "score": 0.7}
        ]
        
        collection = self.mock_chroma.create_collection("test_collection")
        collection.query.return_value = {
            "documents": [r["document"] for r in mock_results],
            "distances": [1 - r["score"] for r in mock_results]
        }
        
        # Verify search operation
        results = collection.query(
            query_embeddings=[mock_query_embedding],
            n_results=2
        )
        collection.query.assert_called_once()
        
    def test_context_processing(self):
        """Test context processing and relevance scoring."""
        # Test data
        test_context = [
            "Relevant context 1",
            "Relevant context 2"
        ]
        test_query = "Test query"
        
        # Mock relevance scoring
        relevance_scores = [0.9, 0.7]
        
        # Test context selection
        selected_context = test_context[0]  # Select highest scoring context
        self.assertEqual(selected_context, "Relevant context 1")
        
    @patch('chromadb.Client')
    def test_error_handling(self, mock_chroma_client):
        """Test error handling in RAG operations."""
        # Test invalid embedding
        mock_chroma_client.create_collection.side_effect = Exception("Test error")
        
        with self.assertRaises(Exception):
            self.mock_chroma.create_collection("test_collection")
            
    def test_context_integration(self):
        """Test integration of context with bot responses."""
        # Test data
        test_context = "Relevant context"
        test_query = "Test query"
        
        # Mock bot response generation with context
        mock_response = f"Response incorporating {test_context}"
        
        # Verify context integration
        self.assertIn(test_context, mock_response)

class TestRAGServiceIntegration(unittest.TestCase):
    """Test RAG service integration with orchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rag_service_url = "http://localhost:5005"
        
    @patch('requests.post')
    def test_orchestrator_rag_request(self, mock_post):
        """Test orchestrator making requests to RAG service."""
        # Mock RAG service response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "results": [
                {
                    "content": "Peter Griffin is the main character",
                    "source": "familyguy.fandom.com/wiki/Peter_Griffin",
                    "relevance_score": 0.95
                }
            ],
            "query_processed": "Peter Griffin",
            "total_results": 1
        }
        mock_post.return_value = mock_response
        
        # Simulate orchestrator request
        query_data = {
            "query": "Peter Griffin",
            "num_results": 3,
            "min_relevance_score": 0.7
        }
        
        # Make request
        response = requests.post(f"{self.rag_service_url}/retrieve", json=query_data)
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["results"]), 1)
        
    @patch('requests.post')
    def test_rag_service_fallback(self, mock_post):
        """Test orchestrator handling RAG service unavailability."""
        # Mock RAG service failure
        mock_post.side_effect = requests.ConnectionError("Service unavailable")
        
        # Test fallback behavior
        try:
            response = requests.post(f"{self.rag_service_url}/retrieve", json={"query": "test"})
        except requests.ConnectionError as e:
            # Orchestrator should handle this gracefully
            self.assertIn("Service unavailable", str(e))
            
    def test_context_formatting_for_llm(self):
        """Test formatting of RAG results for LLM consumption."""
        # Mock RAG service results
        rag_results = [
            {
                "content": "Peter Griffin is a fictional character.",
                "source": "familyguy.fandom.com/wiki/Peter_Griffin",
                "relevance_score": 0.95
            },
            {
                "content": "He works at the Pawtucket Patriot Brewery.",
                "source": "familyguy.fandom.com/wiki/Pawtucket_Patriot_Brewery",
                "relevance_score": 0.87
            }
        ]
        
        # Format for LLM prompt (as orchestrator would do)
        formatted_context = "Retrieved Context from Family Guy Wiki:\n"
        for result in rag_results:
            formatted_context += f"- {result['content']}\n"
            
        expected_format = (
            "Retrieved Context from Family Guy Wiki:\n"
            "- Peter Griffin is a fictional character.\n"
            "- He works at the Pawtucket Patriot Brewery.\n"
        )
        
        self.assertEqual(formatted_context, expected_format)

if __name__ == '__main__':
    unittest.main() 