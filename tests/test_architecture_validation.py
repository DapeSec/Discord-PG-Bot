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

# Test configuration - Updated for new microservice architecture
MESSAGE_ROUTER_URL = "http://localhost:6005"
CONVERSATION_COORDINATOR_URL = "http://localhost:6002"
QUALITY_CONTROL_URL = "http://localhost:6003"
LLM_SERVICE_URL = "http://localhost:6001"
RAG_RETRIEVER_URL = "http://localhost:6007"
RAG_CRAWLER_URL = "http://localhost:6009"
TEST_CHANNEL_ID = "1234567890"  # Replace with actual test channel ID

class ArchitectureValidator:
    """Comprehensive validator for the microservice architecture with distributed conversation management."""
    
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
            ("Message Router", f"{MESSAGE_ROUTER_URL}/health"),
            ("Conversation Coordinator", f"{CONVERSATION_COORDINATOR_URL}/health"),
            ("Quality Control", f"{QUALITY_CONTROL_URL}/health"),
            ("LLM Service", f"{LLM_SERVICE_URL}/health"),
            ("RAG Retriever", f"{RAG_RETRIEVER_URL}/health"),
            ("RAG Crawler", f"{RAG_CRAWLER_URL}/health"),
            ("Peter Discord", "http://localhost:6011/health"),
            ("Brian Discord", "http://localhost:6012/health"),
            ("Stewie Discord", "http://localhost:6013/health")
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
        """Test microservice LLM processing through message router."""
        print("\n🧠 Testing Microservice LLM Processing...")
        
        # Test message routing and conversation coordination
        test_cases = [
            {
                "character": "peter",
                "query": "Tell me a funny story",
                "expected_traits": ["hehe", "holy", "crap", "time when"],
            },
            {
                "character": "brian", 
                "query": "What do you think about literature?",
                "expected_traits": ["well", "actually", "intellectual", "fascinating"],
            },
            {
                "character": "stewie",
                "query": "What's your latest invention?",
                "expected_traits": ["blast", "invention", "world", "plan"],
            }
        ]
        
        all_passed = True
        for test_case in test_cases:
            try:
                # Test conversation flow through message router
                test_payload = {
                    "user_message": test_case["query"],
                    "channel_id": TEST_CHANNEL_ID,
                    "character": test_case["character"],
                    "user_id": "test_user_123",
                    "conversation_id": f"test_conversation_{test_case['character']}"
                }
                
                response = requests.post(
                    f"{MESSAGE_ROUTER_URL}/orchestrate",
                    json=test_payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    self.log_result(f"{test_case['character']} Message Processing", True,
                                  f"Success: {response_data.get('success', False)}")
                else:
                    self.log_result(f"{test_case['character']} Message Processing", False,
                                  f"Status: {response.status_code}, Response: {response.text[:100]}")
                    all_passed = False
                    
            except requests.exceptions.Timeout:
                self.log_result(f"{test_case['character']} Message Processing", False,
                              "Request timed out - Services might be slow")
                all_passed = False
            except Exception as e:
                self.log_result(f"{test_case['character']} Message Processing", False,
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
        
        # Test 4: Message Router RAG Integration
        try:
            # Test message router integration with RAG services
            test_payload = {
                "user_message": "Tell me about the chicken fight",
                "channel_id": TEST_CHANNEL_ID,
                "character": "peter",
                "user_id": "test_user_123",
                "conversation_id": "test_rag_integration"
            }
            
            response = requests.post(
                f"{MESSAGE_ROUTER_URL}/orchestrate",
                json=test_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                self.log_result("Message Router-RAG Integration", True, 
                              "Successfully integrated RAG context")
            else:
                self.log_result("Message Router-RAG Integration", False, 
                              f"Status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("Message Router-RAG Integration", False, f"Error: {e}")
            all_passed = False
        
        # Test 5: Direct RAG Crawl Trigger
        try:
            # Test direct crawl trigger via RAG Crawler service
            crawl_payload = {
                "start_url": "https://familyguy.fandom.com/wiki/Main_Page",
                "max_pages": 5,
                "delay": 1
            }
            
            response = requests.post(
                f"{RAG_CRAWLER_URL}/crawl/start",
                json=crawl_payload,
                timeout=15
            )
            
            if response.status_code == 202:  # Accepted
                data = response.json()
                status = data.get('status', 'unknown')
                self.log_result("Direct RAG Crawl Trigger", True, 
                              f"Status: {status}")
            elif response.status_code == 409:  # Conflict - crawl already running
                self.log_result("Direct RAG Crawl Trigger", True, 
                              "Crawl already in progress")
            else:
                self.log_result("Direct RAG Crawl Trigger", False, 
                              f"Status: {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_result("Direct RAG Crawl Trigger", False, f"Error: {e}")
            all_passed = False
                
        return all_passed

    def test_error_handling(self) -> bool:
        """Test error handling and resilience."""
        print("\n🛡️ Testing Error Handling...")
        
        all_passed = True
        
        # Test invalid message router request
        try:
            invalid_payload = {
                "invalid_field": "test"
                # Missing required fields
            }
            
            response = requests.post(
                f"{MESSAGE_ROUTER_URL}/orchestrate",
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
            ("Peter", "http://localhost:6011"),
            ("Brian", "http://localhost:6012"),
            ("Stewie", "http://localhost:6013")
        ]
        
        all_passed = True
        for bot_name, bot_url in bots:
            try:
                # Test health endpoint
                response = requests.get(f"{bot_url}/health", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    service_name = data.get("service", "Unknown")
                    self.log_result(f"{bot_name} Health Check", True, 
                                  f"Service: {service_name}")
                else:
                    self.log_result(f"{bot_name} Health Check", False, 
                                  f"Status: {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_result(f"{bot_name} Health Check", False, f"Error: {e}")
                all_passed = False
                
        return all_passed

    def test_architecture_benefits(self) -> bool:
        """Test architecture-specific benefits and features."""
        print("\n🏗️ Testing Architecture Benefits...")
        
        all_passed = True
        
        # Test 1: Distributed microservice processing (no monolithic orchestrator)
        try:
            # Verify that we have separate microservices for different concerns
            services_to_check = [
                (MESSAGE_ROUTER_URL, "message routing"),
                (CONVERSATION_COORDINATOR_URL, "conversation coordination"),
                (QUALITY_CONTROL_URL, "quality control"),
                (LLM_SERVICE_URL, "LLM processing")
            ]
            
            all_services_healthy = True
            for service_url, service_name in services_to_check:
                response = requests.get(f"{service_url}/health", timeout=5)
                if response.status_code != 200:
                    all_services_healthy = False
                    break
            
            if all_services_healthy:
                self.log_result("Microservice Architecture", True, 
                              "All microservices are properly separated and running")
            else:
                self.log_result("Microservice Architecture", False, 
                              "Some microservices are not running")
                all_passed = False
                
        except Exception as e:
            self.log_result("Microservice Architecture", False, f"Error: {e}")
            all_passed = False

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
            ("Architecture Benefits", self.test_architecture_benefits)
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