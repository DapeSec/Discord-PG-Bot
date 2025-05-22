import pytest
from unittest.mock import Mock
import chromadb
from pymongo import MongoClient
from langchain_community.embeddings import SentenceTransformerEmbeddings
from flask import Flask

@pytest.fixture
def mock_discord_client():
    """Fixture for mocked Discord client."""
    return Mock()

@pytest.fixture
def mock_ollama():
    """Fixture for mocked Ollama LLM."""
    mock = Mock()
    mock.predict.return_value = "Test response"
    return mock

@pytest.fixture
def mock_mongo():
    """Fixture for mocked MongoDB client."""
    mock = Mock(spec=MongoClient)
    mock_collection = Mock()
    mock.get_database.return_value.get_collection.return_value = mock_collection
    return mock

@pytest.fixture
def mock_chroma():
    """Fixture for mocked Chroma client."""
    mock = Mock(spec=chromadb.Client)
    mock_collection = Mock()
    mock.create_collection.return_value = mock_collection
    return mock

@pytest.fixture
def mock_embeddings():
    """Fixture for mocked sentence embeddings."""
    mock = Mock(spec=SentenceTransformerEmbeddings)
    mock.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    mock.embed_query.return_value = [0.1, 0.2, 0.3]
    return mock

@pytest.fixture
def test_app():
    """Fixture for Flask test client."""
    from orchestrator_server import app
    return app.test_client()

@pytest.fixture
def sample_conversation():
    """Fixture for sample conversation data."""
    return [
        {
            "content": "Test message 1",
            "author": "user1",
            "timestamp": "2024-05-22T10:00:00",
            "channel_id": "123456789"
        },
        {
            "content": "Test response 1",
            "author": "peter",
            "timestamp": "2024-05-22T10:00:01",
            "channel_id": "123456789"
        }
    ]

@pytest.fixture
def sample_rag_context():
    """Fixture for sample RAG context data."""
    return {
        "documents": ["Test context 1", "Test context 2"],
        "scores": [0.9, 0.7],
        "metadata": [
            {"source": "test1", "type": "document"},
            {"source": "test2", "type": "document"}
        ]
    } 