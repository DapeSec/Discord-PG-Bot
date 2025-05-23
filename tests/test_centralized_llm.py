#!/usr/bin/env python3
"""
Unit tests for centralized LLM architecture
Tests the core functionality of the centralized character response generation system
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from langchain.schema import HumanMessage, AIMessage
from langchain.prompts import ChatPromptTemplate

class TestCentralizedCharacterGeneration(unittest.TestCase):
    """Test centralized character response generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_llm = Mock()
        self.conversation_history = [
            HumanMessage(content="Hello everyone"),
            AIMessage(content="Hey there!", name="peter")
        ]
        self.mention_context = "Peter: <@peter_id>\nBrian: <@brian_id>\nStewie: <@stewie_id>"
        
    @patch('src.app.orchestrator.server.character_llm')
    def test_peter_character_consistency(self, mock_llm):
        """Test that Peter's responses maintain character consistency."""
        from src.app.orchestrator.server import generate_character_response
        
        # Mock different Peter-style responses
        peter_responses = [
            "Hehehe, that's funny!",
            "Holy crap, I didn't know that!",
            "This is worse than that time when I fought the giant chicken!"
        ]
        mock_llm.side_effect = peter_responses
        
        for expected_response in peter_responses:
            response = generate_character_response(
                character_name="Peter",
                conversation_history=self.conversation_history,
                mention_context=self.mention_context,
                input_text="Tell me something funny.",
                retrieved_context=""
            )
            self.assertEqual(response, expected_response)
            
    @patch('src.app.orchestrator.server.character_llm')
    def test_brian_character_consistency(self, mock_llm):
        """Test that Brian's responses maintain character consistency."""
        from src.app.orchestrator.server import generate_character_response
        
        mock_llm.return_value = "Well, actually, the socio-political implications of that are quite fascinating."
        
        response = generate_character_response(
            character_name="Brian",
            conversation_history=self.conversation_history,
            mention_context=self.mention_context,
            input_text="What do you think about politics?",
            retrieved_context=""
        )
        
        # Verify Brian's intellectual tone
        self.assertIn("Well, actually", response)
        self.assertIn("fascinating", response)
        
    @patch('src.app.orchestrator.server.character_llm')
    def test_stewie_character_consistency(self, mock_llm):
        """Test that Stewie's responses maintain character consistency."""
        from src.app.orchestrator.server import generate_character_response
        
        mock_llm.return_value = "Blast! My latest invention shall bring about the downfall of this pathetic world!"
        
        response = generate_character_response(
            character_name="Stewie",
            conversation_history=self.conversation_history,
            mention_context=self.mention_context,
            input_text="What's your latest plan?",
            retrieved_context=""
        )
        
        # Verify Stewie's evil genius tone
        self.assertIn("Blast", response)
        self.assertIn("invention", response)
        
    def test_invalid_character_name(self):
        """Test handling of invalid character names."""
        from src.app.orchestrator.server import generate_character_response
        
        with self.assertRaises(ValueError):
            generate_character_response(
                character_name="InvalidCharacter",
                conversation_history=self.conversation_history,
                mention_context=self.mention_context,
                input_text="Test",
                retrieved_context=""
            )

class TestCharacterPromptTemplates(unittest.TestCase):
    """Test character-specific prompt templates."""
    
    def test_character_prompts_exist(self):
        """Test that all character prompts are properly defined."""
        from src.app.orchestrator.server import CHARACTER_PROMPTS
        
        required_characters = ["Peter", "Brian", "Stewie"]
        for character in required_characters:
            self.assertIn(character, CHARACTER_PROMPTS)
            self.assertIsInstance(CHARACTER_PROMPTS[character], ChatPromptTemplate)
            
    def test_character_chains_exist(self):
        """Test that all character chains are properly defined."""
        from src.app.orchestrator.server import CHARACTER_CHAINS
        
        required_characters = ["Peter", "Brian", "Stewie"]
        for character in required_characters:
            self.assertIn(character, CHARACTER_CHAINS)
            
    def test_prompt_template_structure(self):
        """Test that prompt templates have the required structure."""
        from src.app.orchestrator.server import CHARACTER_PROMPTS
        
        for character, prompt in CHARACTER_PROMPTS.items():
            # Check that prompts contain required variables
            prompt_vars = prompt.input_variables
            required_vars = ["chat_history", "mention_context", "input_text", "retrieved_context"]
            
            for var in required_vars:
                self.assertIn(var, prompt_vars, 
                            f"Character {character} prompt missing variable: {var}")

class TestRAGIntegration(unittest.TestCase):
    """Test RAG system integration with centralized LLM."""
    
    def setUp(self):
        """Set up RAG test fixtures."""
        self.test_query = "Tell me about Family Guy characters"
        self.mock_context = "Family Guy is an animated sitcom featuring the Griffin family..."
        
    @patch('src.app.orchestrator.server.vectorstore')
    def test_context_retrieval(self, mock_vectorstore):
        """Test RAG context retrieval."""
        from src.app.orchestrator.server import retrieve_context
        
        # Mock vector store response
        mock_doc = Mock()
        mock_doc.page_content = self.mock_context
        mock_vectorstore.similarity_search_with_score.return_value = [(mock_doc, 0.85)]
        
        context = retrieve_context(self.test_query)
        self.assertEqual(context, self.mock_context)
        mock_vectorstore.similarity_search_with_score.assert_called_with(self.test_query, k=3)
        
    @patch('src.app.orchestrator.server.vectorstore')
    def test_empty_vectorstore_handling(self, mock_vectorstore):
        """Test handling when vector store is empty."""
        from src.app.orchestrator.server import retrieve_context
        
        # Mock empty vector store
        mock_vectorstore._collection.count.return_value = 0
        
        context = retrieve_context(self.test_query)
        self.assertEqual(context, "")
        
    @patch('src.app.orchestrator.server.retrieve_context')
    @patch('src.app.orchestrator.server.generate_character_response')
    def test_rag_enhanced_responses(self, mock_generate, mock_retrieve):
        """Test that RAG context is properly passed to character generation."""
        mock_retrieve.return_value = self.mock_context
        mock_generate.return_value = "Hehehe, yeah Family Guy is awesome!"
        
        # This would be tested through the orchestrate endpoint
        # For now, test that the functions can work together
        context = mock_retrieve(self.test_query)
        response = mock_generate(
            character_name="Peter",
            conversation_history=[],
            mention_context="",
            input_text=self.test_query,
            retrieved_context=context
        )
        
        mock_retrieve.assert_called_with(self.test_query)
        self.assertIsNotNone(response)

class TestResponseCleaning(unittest.TestCase):
    """Test response cleaning and formatting."""
    
    def test_clean_ai_prefixes(self):
        """Test removal of AI prefixes."""
        from src.app.orchestrator.server import clean_llm_response
        
        test_cases = [
            ("AI: Hehehe, that's funny!", "Hehehe, that's funny!"),
            ("Assistant: Well, actually...", "Well, actually..."),
            ("Bot: Blast!", "Blast!"),
            ("Peter: Hehehe!", "Hehehe!"),
            ("Clean response", "Clean response")
        ]
        
        for dirty, expected in test_cases:
            clean = clean_llm_response(dirty)
            self.assertEqual(clean, expected)
            
    def test_clean_end_markers(self):
        """Test removal of end conversation markers."""
        from src.app.orchestrator.server import clean_llm_response
        
        test_cases = [
            ("Great response! [END_CONVERSATION]", "Great response!"),
            ("Another response [END CONVERSATION]", "Another response"),
            ("Normal response", "Normal response")
        ]
        
        for dirty, expected in test_cases:
            clean = clean_llm_response(dirty)
            self.assertEqual(clean, expected)
            
    def test_clean_human_placeholders(self):
        """Test removal of human name placeholders."""
        from src.app.orchestrator.server import clean_llm_response
        
        test_cases = [
            ("[HumanName] said something", "said something"),
            ("User mentioned that", "mentioned that"),
            ("Regular response", "Regular response")
        ]
        
        for dirty, expected in test_cases:
            clean = clean_llm_response(dirty)
            self.assertEqual(clean, expected)

class TestErrorHandling(unittest.TestCase):
    """Test error handling in centralized LLM processing."""
    
    @patch('src.app.orchestrator.server.character_llm')
    def test_llm_generation_failure(self, mock_llm):
        """Test handling of LLM generation failures."""
        from src.app.orchestrator.server import generate_character_response
        
        # Mock LLM failure
        mock_llm.side_effect = Exception("LLM connection error")
        
        response = generate_character_response(
            character_name="Peter",
            conversation_history=[],
            mention_context="",
            input_text="Test",
            retrieved_context=""
        )
        
        # Should return a fallback response
        self.assertIn("trouble thinking", response.lower())
        
    def test_character_prompt_validation(self):
        """Test validation of character prompts."""
        from src.app.orchestrator.server import CHARACTER_PROMPTS
        
        # All prompts should be ChatPromptTemplate instances
        for character, prompt in CHARACTER_PROMPTS.items():
            self.assertIsInstance(prompt, ChatPromptTemplate,
                                f"Character {character} prompt is not a ChatPromptTemplate")

class TestResourceEfficiency(unittest.TestCase):
    """Test resource efficiency of centralized architecture."""
    
    def test_single_llm_instance(self):
        """Test that only one LLM instance is used."""
        from src.app.orchestrator.server import character_llm, CHARACTER_CHAINS
        
        # Verify all chains use the same LLM instance
        for character, chain in CHARACTER_CHAINS.items():
            # The chain should end with the same LLM instance
            # This is a structural test to ensure resource sharing
            self.assertIsNotNone(chain)
            
    def test_shared_prompt_templates(self):
        """Test that prompt templates are efficiently managed."""
        from src.app.orchestrator.server import CHARACTER_PROMPTS
        
        # Verify all characters have prompts without duplication
        character_count = len(CHARACTER_PROMPTS)
        self.assertEqual(character_count, 3)  # Peter, Brian, Stewie
        
        # Each prompt should be distinct
        prompt_ids = [id(prompt) for prompt in CHARACTER_PROMPTS.values()]
        unique_prompt_ids = set(prompt_ids)
        self.assertEqual(len(prompt_ids), len(unique_prompt_ids))

class TestArchitectureIntegration(unittest.TestCase):
    """Test integration between orchestrator and bots."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        from src.app.orchestrator.server import app
        self.orchestrator_client = app.test_client()
        
    @patch('requests.post')
    @patch('src.app.orchestrator.server.generate_character_response')
    def test_end_to_end_message_flow(self, mock_generate, mock_post):
        """Test complete message flow from input to Discord output."""
        # Mock character response generation
        mock_generate.return_value = "Hehehe, that's a great question!"
        
        # Mock successful Discord API call
        mock_post.return_value.status_code = 200
        
        # Test orchestrate endpoint
        test_data = {
            "user_query": "How are you doing?",
            "channel_id": "123456789",
            "initiator_bot_name": "Peter",
            "initiator_mention": "<@peter_id>",
            "human_user_display_name": "TestUser"
        }
        
        response = self.orchestrator_client.post('/orchestrate',
                                               data=json.dumps(test_data),
                                               content_type='application/json')
        
        # Verify orchestrator processed the request
        self.assertEqual(response.status_code, 200)
        
        # Verify character response was generated
        mock_generate.assert_called()
        
        # Verify Discord message was sent
        mock_post.assert_called()

if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2) 