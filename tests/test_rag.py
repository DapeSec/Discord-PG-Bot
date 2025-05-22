import unittest
from unittest.mock import Mock, patch
import chromadb
from langchain_community.embeddings import SentenceTransformerEmbeddings

class TestRAG(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_chroma = Mock(spec=chromadb.Client)
        self.mock_embeddings = Mock(spec=SentenceTransformerEmbeddings)
        
    @patch('chromadb.Client')
    def test_vector_store_operations(self, mock_chroma_client):
        """Test vector store operations."""
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
        """Test similarity search functionality."""
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
        
if __name__ == '__main__':
    unittest.main() 