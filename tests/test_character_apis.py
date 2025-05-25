import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestCharacterConfigAPIs:
    """Test suite for Character Configuration APIs (Local Mistral Version)."""

    @pytest.fixture
    def peter_client(self):
        """Create a test client for Peter's character config API."""
        from app.bots.peter_bot import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def brian_client(self):
        """Create a test client for Brian's character config API."""
        from app.bots.brian_bot import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def stewie_client(self):
        """Create a test client for Stewie's character config API."""
        from app.bots.stewie_bot import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_peter_health_check(self, peter_client):
        """Test Peter's health endpoint."""
        response = peter_client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'Peter_Character_Config_API' in data['service']
        assert 'centralized orchestrator LLM' in data['note']

    def test_brian_health_check(self, brian_client):
        """Test Brian's health endpoint."""
        response = brian_client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'Brian_Character_Config_API' in data['service']

    def test_stewie_health_check(self, stewie_client):
        """Test Stewie's health endpoint."""
        response = stewie_client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'Stewie_Character_Config_API' in data['service']

    def test_peter_character_info(self, peter_client):
        """Test Peter's character information endpoint."""
        response = peter_client.get('/character_info')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['character_name'] == 'Peter'
        assert 'Lovable oaf' in data['personality']
        assert data['max_response_length'] == 500
        assert data['service_version'] == '3.0_config_only'
        assert data['llm_centralized'] is True
        assert 'centralized orchestrator LLM' in data['note']

    def test_brian_character_info(self, brian_client):
        """Test Brian's character information endpoint."""
        response = brian_client.get('/character_info')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['character_name'] == 'Brian'
        assert 'Intellectual' in data['personality']
        assert data['max_response_length'] == 1800
        assert data['service_version'] == '3.0_config_only'
        assert data['llm_centralized'] is True

    def test_stewie_character_info(self, stewie_client):
        """Test Stewie's character information endpoint."""
        response = stewie_client.get('/character_info')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['character_name'] == 'Stewie'
        assert 'Evil baby genius' in data['personality']
        assert data['max_response_length'] == 1800
        assert data['service_version'] == '3.0_config_only'
        assert data['llm_centralized'] is True

    def test_generate_response_deprecated(self, peter_client):
        """Test that generate_response endpoint returns 410 Gone (deprecated)."""
        response = peter_client.post('/generate_response', json={
            "user_query": "Hello!",
            "max_length": 500
        })
        assert response.status_code == 410  # Gone
        
        data = json.loads(response.data)
        assert 'centralized orchestrator LLM' in data['error']
        assert 'orchestrator service' in data['redirect']

    def test_brian_generate_response_deprecated(self, brian_client):
        """Test that Brian's generate_response endpoint is deprecated."""
        response = brian_client.post('/generate_response', json={
            "user_query": "Hello!",
            "max_length": 1800
        })
        assert response.status_code == 410

    def test_stewie_generate_response_deprecated(self, stewie_client):
        """Test that Stewie's generate_response endpoint is deprecated."""
        response = stewie_client.post('/generate_response', json={
            "user_query": "Hello!",
            "max_length": 1800
        })
        assert response.status_code == 410

    def test_character_traits_and_speech_style(self, peter_client, brian_client, stewie_client):
        """Test that character information includes proper traits and speech styles."""
        # Test Peter
        response = peter_client.get('/character_info')
        peter_data = json.loads(response.data)
        assert 'chicken fights' in str(peter_data['traits'])
        assert 'working-class' in peter_data['speech_style']
        
        # Test Brian
        response = brian_client.get('/character_info')
        brian_data = json.loads(response.data)
        assert 'intellectual' in str(brian_data['traits']).lower()
        assert 'sophisticated' in brian_data['speech_style']
        
        # Test Stewie
        response = stewie_client.get('/character_info')
        stewie_data = json.loads(response.data)
        assert 'British accent' in str(stewie_data['traits'])
        assert 'British accent' in stewie_data['speech_style']

    def test_api_endpoints_documentation(self, peter_client):
        """Test that character APIs document their available endpoints."""
        response = peter_client.get('/character_info')
        data = json.loads(response.data)
        
        assert 'api_endpoints' in data
        assert '/health' in data['api_endpoints']
        assert '/character_info' in data['api_endpoints']
        
        assert 'deprecated_endpoints' in data
        assert '/generate_response' in data['deprecated_endpoints']

class TestCharacterConfigIntegration:
    """Integration tests for character configuration services."""

    def test_all_characters_consistent_config(self):
        """Test that all character services have consistent configuration."""
        from app.bots import peter_bot, brian_bot, stewie_bot
        
        # All should be Flask apps
        assert hasattr(peter_bot, 'app')
        assert hasattr(brian_bot, 'app')
        assert hasattr(stewie_bot, 'app')
        
        # All should have health endpoints
        with peter_bot.app.test_client() as client:
            response = client.get('/health')
            assert response.status_code == 200
        
        with brian_bot.app.test_client() as client:
            response = client.get('/health')
            assert response.status_code == 200
            
        with stewie_bot.app.test_client() as client:
            response = client.get('/health')
            assert response.status_code == 200

    def test_no_llm_dependencies(self):
        """Test that character services don't import LLM dependencies."""
        # This test ensures character services are lightweight
        from app.bots import peter_bot, brian_bot, stewie_bot
        
        # Character services should not import OpenAI or LangChain
        import sys
        
        # Check that character modules don't have LLM imports
        for module_name in ['app.bots.peter_bot', 'app.bots.brian_bot', 'app.bots.stewie_bot']:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                # Should not have openai or langchain attributes
                assert not hasattr(module, 'openai')
                assert not hasattr(module, 'langchain')

if __name__ == '__main__':
    pytest.main([__file__]) 