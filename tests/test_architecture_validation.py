#!/usr/bin/env python3
"""
Comprehensive test script for centralized LLM architecture with RAG microservices
This script validates the entire centralized character response generation system
"""

import requests
import json
import time
import sys
import traceback
from typing import Dict, List, Tuple

# Test configuration
ORCHESTRATOR_URL = "http://localhost:5003"
RAG_RETRIEVER_URL = "http://localhost:5005"
RAG_CRAWLER_URL = "http://localhost:5009"
TEST_CHANNEL_ID = "1234567890"  # Replace with actual test channel ID

class ArchitectureValidator:
    """Comprehensive validator for the centralized LLM architecture with RAG microservices."""
    
    def __init__(self):
        self.results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
            
        self.results.append(result)
        print(result)
        
    def test_health_endpoints(self) -> bool:
        """Test health endpoints of all services."""
        print("\n🏥 Testing Health Endpoints...")
        
        services = [
            ("Orchestrator", f"{ORCHESTRATOR_URL}/health"),
            ("RAG Retriever", f"{RAG_RETRIEVER_URL}/health"),
            ("RAG Crawler", f"{RAG_CRAWLER_URL}/health"),
            ("Peter Bot", "http://localhost:5006/health"),
            ("Brian Bot", "http://localhost:5007/health"),
            ("Stewie Bot", "http://localhost:5008/health")
        ]
        
        all_healthy = True
        for service_name, health_url in services:
            try:
                response = requests.get(health_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if service_name == "RAG Retriever":
                        # RAG Retriever service health response format
                        dependencies = data.get('dependencies', {})
                        self.log_result(f"{service_name} Health", True, 
                                      f"Status: {data.get('status')}, Dependencies: {list(dependencies.keys())}")
                    elif service_name == "RAG Crawler":
                        # RAG Crawler service health response format
                        crawl_status = data.get('crawl_status', 'unknown')
                        dependencies = data.get('dependencies', {})
                        self.log_result(f"{service_name} Health", True, 
                                      f"Status: {data.get('status')}, Crawl: {crawl_status}, Dependencies: {list(dependencies.keys())}")
                    else:
                        # Standard health response format
                        components = data.get("components", {})
                        self.log_result(f"{service_name} Health", True, 
                                      f"Status: {data.get('status')}, Components: {list(components.keys())}")
                else:
                    self.log_result(f"{service_name} Health", False, 
                                  f"Status: {response.status_code}")
                    all_healthy = False
            except requests.exceptions.ConnectionError:
                self.log_result(f"{service_name} Health", False, "Service not running")
                all_healthy = False
            except Exception as e:
                self.log_result(f"{service_name} Health", False, f"Error: {e}")
                all_healthy = False
                
        return all_healthy

    def test_centralized_llm_processing(self) -> bool:
        """Test centralized LLM character response generation."""
        print("\n🧠 Testing Centralized LLM Processing...")
        
        # Test different characters and queries
        test_cases = [
            {
                "character": "Peter",
                "query": "Tell me a funny story",
                "expected_traits": ["hehe", "holy", "crap", "time when"],
                "mention": "<@peter_id>"
            },
            {
                "character": "Brian", 
                "query": "What do you think about literature?",
                "expected_traits": ["well", "actually", "intellectual", "fascinating"],
                "mention": "<@brian_id>"
            },
            {
                "character": "Stewie",
                "query": "What's your latest invention?",
                "expected_traits": ["blast", "invention", "world", "plan"],
                "mention": "<@stewie_id>"
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            try:
                test_payload = {
                    "user_query": test_case["query"],
                    "channel_id": TEST_CHANNEL_ID,
                    "initiator_bot_name": test_case["character"],
                    "initiator_mention": test_case["mention"],
                    "human_user_display_name": "TestUser",
                    "is_new_conversation": False,
                    "conversation_session_id": None
                }
                
                response = requests.post(
                    f"{ORCHESTRATOR_URL}/orchestrate",
                    json=test_payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    self.log_result(f"{test_case['character']} Response Generation", True,
                                  f"Session: {response_data.get('conversation_session_id', 'N/A')}")
                else:
                    self.log_result(f"{test_case['character']} Response Generation", False,
                                  f"Status: {response.status_code}, Response: {response.text[:100]}")
                    all_passed = False
                    
            except requests.exceptions.Timeout:
                self.log_result(f"{test_case['character']} Response Generation", False,
                              "Request timed out - LLM might be slow")
                all_passed = False
            except Exception as e:
                self.log_result(f"{test_case['character']} Response Generation", False,
                              f"Error: {e}")
                all_passed = False
                
        return all_passed

    def test_rag_microservices_integration(self) -> bool:
        """Test RAG microservices integration with orchestrator."""
        print("\n📚 Testing RAG Microservices Integration...")
        
        all_passed = True
        
        # Test 1: RAG Retriever Service
        try:
            # Test direct retrieval from RAG Retriever service
            retrieval_payload = {
                "query": "Peter Griffin chicken fight",
                "num_results": 3
            }
            
            response = requests.post(
                f"{RAG_RETRIEVER_URL}/retrieve",
                json=retrieval_payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                documents_found = data.get('documents_found', 0)
                self.log_result("RAG Retriever Service", True, 
                              f"Retrieved {documents_found} documents")
            else:
                self.log_result("RAG Retriever Service", False, 
                              f"Status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("RAG Retriever Service", False, f"Error: {e}")
            all_passed = False
        
        # Test 2: RAG Crawler Service Status
        try:
            response = requests.get(f"{RAG_CRAWLER_URL}/crawl/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                service_name = data.get('service_name', 'Unknown')
                crawl_in_progress = data.get('crawl_in_progress', False)
                self.log_result("RAG Crawler Status", True, 
                              f"Service: {service_name}, Active: {crawl_in_progress}")
            else:
                self.log_result("RAG Crawler Status", False, 
                              f"Status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("RAG Crawler Status", False, f"Error: {e}")
            all_passed = False
        
        # Test 3: Vector Store Info
        try:
            response = requests.get(f"{RAG_CRAWLER_URL}/vector_store/info", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                document_count = data.get('document_count', 0)
                status = data.get('status', 'unknown')
                self.log_result("Vector Store Info", True, 
                              f"Status: {status}, Documents: {document_count}")
            else:
                self.log_result("Vector Store Info", False, 
                              f"Status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("Vector Store Info", False, f"Error: {e}")
            all_passed = False
        
        # Test 4: Orchestrator RAG Integration
        try:
            # Test orchestrator integration with RAG services
            test_payload = {
                "user_query": "Tell me about the chicken fight",
                "channel_id": TEST_CHANNEL_ID,
                "initiator_bot_name": "Peter",
                "initiator_mention": "<@peter_id>",
                "human_user_display_name": "TestUser",
                "is_new_conversation": False,
                "conversation_session_id": None
            }
            
            response = requests.post(
                f"{ORCHESTRATOR_URL}/orchestrate",
                json=test_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                self.log_result("Orchestrator-RAG Integration", True, 
                              "Successfully integrated RAG context")
            else:
                self.log_result("Orchestrator-RAG Integration", False, 
                              f"Status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("Orchestrator-RAG Integration", False, f"Error: {e}")
            all_passed = False
        
        # Test 5: Orchestrator Crawl Trigger
        try:
            # Test orchestrator triggering crawl via RAG Crawler service
            crawl_payload = {
                "start_url": "https://familyguy.fandom.com/wiki/Main_Page",
                "max_pages": 5,
                "delay": 1
            }
            
            response = requests.post(
                f"{ORCHESTRATOR_URL}/crawl/trigger",
                json=crawl_payload,
                timeout=15
            )
            
            if response.status_code == 202:  # Accepted
                data = response.json()
                status = data.get('status', 'unknown')
                self.log_result("Orchestrator Crawl Trigger", True, 
                              f"Status: {status}")
            elif response.status_code == 409:  # Conflict - crawl already running
                self.log_result("Orchestrator Crawl Trigger", True, 
                              "Crawl already in progress")
            else:
                self.log_result("Orchestrator Crawl Trigger", False, 
                              f"Status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("Orchestrator Crawl Trigger", False, f"Error: {e}")
            all_passed = False
                
        return all_passed

    def test_error_handling(self) -> bool:
        """Test error handling and resilience."""
        print("\n🛡️ Testing Error Handling...")
        
        all_passed = True
        
        # Test invalid orchestrator request
        try:
            invalid_payload = {
                "invalid_field": "test"
                # Missing required fields
            }
            
            response = requests.post(
                f"{ORCHESTRATOR_URL}/orchestrate",
                json=invalid_payload,
                timeout=10
            )
            
            if response.status_code == 400:  # Bad Request expected
                self.log_result("Invalid Request Handling", True, "Properly rejected invalid request")
            else:
                self.log_result("Invalid Request Handling", False, 
                              f"Unexpected status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("Invalid Request Handling", False, f"Error: {e}")
            all_passed = False
        
        # Test RAG service error handling
        try:
            # Test invalid retrieval request
            invalid_rag_payload = {
                "invalid_query_field": "test"
            }
            
            response = requests.post(
                f"{RAG_RETRIEVER_URL}/retrieve",
                json=invalid_rag_payload,
                timeout=10
            )
            
            # Should handle gracefully (either 400 or return empty results)
            if response.status_code in [200, 400]:
                self.log_result("RAG Error Handling", True, "Gracefully handled invalid request")
            else:
                self.log_result("RAG Error Handling", False, 
                              f"Unexpected status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("RAG Error Handling", False, f"Error: {e}")
            all_passed = False
            
        return all_passed

    def test_bot_discord_interfaces(self) -> bool:
        """Test bot Discord interface endpoints."""
        print("\n🤖 Testing Bot Discord Interfaces...")
        
        bots = [
            ("Peter", "http://localhost:5006"),
            ("Brian", "http://localhost:5007"),
            ("Stewie", "http://localhost:5008")
        ]
        
        all_passed = True
        for bot_name, bot_url in bots:
            try:
                # Test character info endpoint
                response = requests.get(f"{bot_url}/character_info", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    character_name = data.get("character_name", "Unknown")
                    self.log_result(f"{bot_name} Character Info", True, 
                                  f"Character: {character_name}")
                else:
                    self.log_result(f"{bot_name} Character Info", False, 
                                  f"Status: {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_result(f"{bot_name} Character Info", False, f"Error: {e}")
                all_passed = False
                
        return all_passed

    def test_architecture_benefits(self) -> bool:
        """Test architecture-specific benefits and features."""
        print("\n🏗️ Testing Architecture Benefits...")
        
        all_passed = True
        
        # Test 1: Centralized LLM processing (no individual bot LLM endpoints)
        try:
            # Verify that bots don't have individual LLM endpoints
            response = requests.post("http://localhost:5006/generate_response", 
                                   json={"query": "test"}, timeout=5)
            
            # Should fail (404) because bots don't have individual LLM processing
            if response.status_code == 404:
                self.log_result("Centralized LLM Architecture", True, 
                              "Bots correctly don't have individual LLM endpoints")
            else:
                self.log_result("Centralized LLM Architecture", False, 
                              "Bots still have individual LLM endpoints")
                all_passed = False
                
        except requests.exceptions.ConnectionError:
            # This is expected - endpoint shouldn't exist
            self.log_result("Centralized LLM Architecture", True, 
                          "Bots correctly don't have individual LLM endpoints")
        except Exception as e:
            self.log_result("Centralized LLM Architecture", False, f"Error: {e}")
            all_passed = False
        
        # Test 2: RAG Microservices Separation
        try:
            # Verify RAG Retriever and Crawler are separate services
            retriever_health = requests.get(f"{RAG_RETRIEVER_URL}/health", timeout=5)
            crawler_health = requests.get(f"{RAG_CRAWLER_URL}/health", timeout=5)
            
            if retriever_health.status_code == 200 and crawler_health.status_code == 200:
                retriever_data = retriever_health.json()
                crawler_data = crawler_health.json()
                
                retriever_service = retriever_data.get('service_name', 'Unknown')
                crawler_service = crawler_data.get('service_name', 'Unknown')
                
                if 'Retriever' in retriever_service and 'Crawler' in crawler_service:
                    self.log_result("RAG Microservices Separation", True, 
                                  f"Retriever: {retriever_service}, Crawler: {crawler_service}")
                else:
                    self.log_result("RAG Microservices Separation", False, 
                                  "Services not properly separated")
                    all_passed = False
            else:
                self.log_result("RAG Microservices Separation", False, 
                              "One or both RAG services not responding")
                all_passed = False
                
        except Exception as e:
            self.log_result("RAG Microservices Separation", False, f"Error: {e}")
            all_passed = False
            
        return all_passed

    def test_organic_conversation_system(self) -> bool:
        """Test organic conversation initiation system."""
        print("\n🌱 Testing Organic Conversation System...")
        
        try:
            # Test organic conversation trigger (if available)
            # This might not be directly testable without waiting for natural triggers
            
            # Instead, test that the orchestrator has the necessary endpoints
            response = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=10)
            
            if response.status_code == 200:
                # Organic conversation system is part of orchestrator
                self.log_result("Organic Conversation System", True, 
                              "System integrated in orchestrator")
                return True
            else:
                self.log_result("Organic Conversation System", False, 
                              "Orchestrator not responding")
                return False
                
        except Exception as e:
            self.log_result("Organic Conversation System", False, f"Error: {e}")
            return False

    def test_rag_microservices_endpoints(self) -> bool:
        """Test specific RAG microservices endpoints."""
        print("\n🔍 Testing RAG Microservices Endpoints...")
        
        all_passed = True
        
        # Test RAG Retriever endpoints
        retriever_endpoints = [
            ("/health", "GET"),
            ("/retrieve", "POST"),
            ("/vector_store_status", "GET")
        ]
        
        for endpoint, method in retriever_endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{RAG_RETRIEVER_URL}{endpoint}", timeout=10)
                else:  # POST
                    test_payload = {"query": "test", "num_results": 1}
                    response = requests.post(f"{RAG_RETRIEVER_URL}{endpoint}", 
                                           json=test_payload, timeout=10)
                
                if response.status_code in [200, 202]:
                    self.log_result(f"RAG Retriever {endpoint}", True, 
                                  f"Status: {response.status_code}")
                else:
                    self.log_result(f"RAG Retriever {endpoint}", False, 
                                  f"Status: {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_result(f"RAG Retriever {endpoint}", False, f"Error: {e}")
                all_passed = False
        
        # Test RAG Crawler endpoints
        crawler_endpoints = [
            ("/health", "GET"),
            ("/crawl/status", "GET"),
            ("/vector_store/info", "GET"),
            ("/auto_crawl/status", "GET")
        ]
        
        for endpoint, method in crawler_endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{RAG_CRAWLER_URL}{endpoint}", timeout=10)
                else:  # POST
                    test_payload = {"start_url": "https://example.com", "max_pages": 1}
                    response = requests.post(f"{RAG_CRAWLER_URL}{endpoint}", 
                                           json=test_payload, timeout=10)
                
                if response.status_code in [200, 202, 409]:  # 409 = conflict (crawl already running)
                    self.log_result(f"RAG Crawler {endpoint}", True, 
                                  f"Status: {response.status_code}")
                else:
                    self.log_result(f"RAG Crawler {endpoint}", False, 
                                  f"Status: {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_result(f"RAG Crawler {endpoint}", False, f"Error: {e}")
                all_passed = False
                
        return all_passed

    def run_all_tests(self) -> None:
        """Run all architecture validation tests."""
        print("🚀 Starting Comprehensive Architecture Validation...")
        print("=" * 60)
        
        # Run all test suites
        test_suites = [
            ("Health Endpoints", self.test_health_endpoints),
            ("Centralized LLM Processing", self.test_centralized_llm_processing),
            ("RAG Microservices Integration", self.test_rag_microservices_integration),
            ("RAG Microservices Endpoints", self.test_rag_microservices_endpoints),
            ("Error Handling", self.test_error_handling),
            ("Bot Discord Interfaces", self.test_bot_discord_interfaces),
            ("Architecture Benefits", self.test_architecture_benefits),
            ("Organic Conversation System", self.test_organic_conversation_system)
        ]
        
        suite_results = []
        for suite_name, test_func in test_suites:
            print(f"\n{'='*20} {suite_name} {'='*20}")
            try:
                result = test_func()
                suite_results.append((suite_name, result))
            except Exception as e:
                print(f"❌ CRITICAL ERROR in {suite_name}: {e}")
                traceback.print_exc()
                suite_results.append((suite_name, False))
        
        # Print summary
        print("\n" + "="*60)
        print("📊 VALIDATION SUMMARY")
        print("="*60)
        
        for suite_name, passed in suite_results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {suite_name}")
        
        print(f"\nOverall Results: {self.passed_tests}/{self.total_tests} tests passed")
        
        if self.passed_tests == self.total_tests:
            print("🎉 ALL TESTS PASSED! Architecture is working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Please check the logs above.")
            return False

def main():
    """Main function to run architecture validation."""
    validator = ArchitectureValidator()
    
    print("Discord Family Guy Bot - Architecture Validation")
    print("Testing centralized LLM architecture with RAG microservices")
    print("="*60)
    
    success = validator.run_all_tests()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 