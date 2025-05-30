#!/usr/bin/env python3
"""
Comprehensive test suite for the new microservices architecture.
Tests all services individually and their integration.
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, Any

# Service URLs
SERVICES = {
    "llm_service": "http://localhost:5001",
    "character_config": "http://localhost:5006", 
    "message_router": "http://localhost:5005",
    "rag_retriever": "http://localhost:5007",
    "rag_crawler": "http://localhost:5009",
    "peter_discord": "http://localhost:5011",
    "brian_discord": "http://localhost:5012",
    "stewie_discord": "http://localhost:5013"
}

class MicroservicesArchitectureTester:
    """Test suite for the microservices architecture."""
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test results."""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
        
        print(f"{status} | {test_name}: {message}")
        self.test_results[test_name] = {
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def test_service_health(self, service_name: str, service_url: str) -> bool:
        """Test if a service is healthy."""
        try:
            response = requests.get(f"{service_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "unknown")
                self.log_test(f"{service_name}_health", 
                             status in ["healthy", "degraded"], 
                             f"Status: {status}")
                return status in ["healthy", "degraded"]
            else:
                self.log_test(f"{service_name}_health", False, 
                             f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test(f"{service_name}_health", False, str(e))
            return False
    
    def test_llm_service_functionality(self) -> bool:
        """Test LLM service functionality."""
        try:
            # Test simple generation
            response = requests.post(f"{SERVICES['llm_service']}/generate", 
                                   json={
                                       "prompt": "You are Peter Griffin. Say hello in character.",
                                       "settings": {"temperature": 0.8}
                                   }, 
                                   timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if "response" in data and len(data["response"]) > 0:
                    self.log_test("llm_service_generation", True, 
                                 f"Generated {len(data['response'])} chars")
                    return True
                else:
                    self.log_test("llm_service_generation", False, "Empty response")
                    return False
            else:
                self.log_test("llm_service_generation", False, 
                             f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("llm_service_generation", False, str(e))
            return False
    
    def test_character_config_functionality(self) -> bool:
        """Test character config service functionality."""
        try:
            # Test getting character prompts
            characters = ["Peter", "Brian", "Stewie"]
            all_success = True
            
            for character in characters:
                response = requests.get(f"{SERVICES['character_config']}/llm_prompt/{character}", 
                                      timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if "llm_prompt" in data and "llm_settings" in data:
                        self.log_test(f"character_config_{character.lower()}", True, 
                                     f"Prompt length: {len(data['llm_prompt'])}")
                    else:
                        self.log_test(f"character_config_{character.lower()}", False, 
                                     "Missing prompt or settings")
                        all_success = False
                else:
                    self.log_test(f"character_config_{character.lower()}", False, 
                                 f"HTTP {response.status_code}")
                    all_success = False
            
            return all_success
        except Exception as e:
            self.log_test("character_config_functionality", False, str(e))
            return False
    
    def test_message_router_orchestration(self) -> bool:
        """Test message router orchestration functionality."""
        try:
            # Test full orchestration flow
            test_data = {
                "character_name": "Peter",
                "input_text": "Hello, how are you doing today?",
                "conversation_history": [],
                "channel_id": "test_channel_123"
            }
            
            response = requests.post(f"{SERVICES['message_router']}/orchestrate", 
                                   json=test_data, 
                                   timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "data" in data:
                    response_data = data["data"]
                    if "response" in response_data and len(response_data["response"]) > 0:
                        self.log_test("message_router_orchestration", True, 
                                     f"Generated response: {len(response_data['response'])} chars")
                        return True
                    else:
                        self.log_test("message_router_orchestration", False, 
                                     "Empty response in orchestration")
                        return False
                else:
                    self.log_test("message_router_orchestration", False, 
                                 f"Orchestration failed: {data.get('error', 'Unknown error')}")
                    return False
            else:
                self.log_test("message_router_orchestration", False, 
                             f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("message_router_orchestration", False, str(e))
            return False
    
    def test_service_integration(self) -> bool:
        """Test integration between services."""
        try:
            # Test that message router can communicate with all required services
            response = requests.get(f"{SERVICES['message_router']}/services/health", 
                                  timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                services_status = data.get("services", {})
                
                required_services = ["llm_service", "character_config", "rag_retriever"]
                all_healthy = True
                
                for service in required_services:
                    if service in services_status:
                        status = services_status[service].get("status", "unknown")
                        if status == "healthy":
                            self.log_test(f"integration_{service}", True, "Service reachable")
                        else:
                            self.log_test(f"integration_{service}", False, f"Status: {status}")
                            all_healthy = False
                    else:
                        self.log_test(f"integration_{service}", False, "Service not found")
                        all_healthy = False
                
                return all_healthy
            else:
                self.log_test("service_integration", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("service_integration", False, str(e))
            return False
    
    def test_caching_functionality(self) -> bool:
        """Test caching functionality across services."""
        try:
            # Test LLM service caching
            test_prompt = "You are Peter Griffin. Say 'Nyeheheh' exactly."
            
            # First request
            start_time = time.time()
            response1 = requests.post(f"{SERVICES['llm_service']}/generate", 
                                    json={"prompt": test_prompt}, 
                                    timeout=30)
            first_duration = time.time() - start_time
            
            if response1.status_code != 200:
                self.log_test("caching_functionality", False, "First request failed")
                return False
            
            # Second identical request (should be cached)
            start_time = time.time()
            response2 = requests.post(f"{SERVICES['llm_service']}/generate", 
                                    json={"prompt": test_prompt}, 
                                    timeout=30)
            second_duration = time.time() - start_time
            
            if response2.status_code != 200:
                self.log_test("caching_functionality", False, "Second request failed")
                return False
            
            data2 = response2.json()
            if data2.get("cached", False):
                self.log_test("caching_functionality", True, 
                             f"Cache hit detected (1st: {first_duration:.2f}s, 2nd: {second_duration:.2f}s)")
                return True
            else:
                self.log_test("caching_functionality", False, "No cache hit detected")
                return False
                
        except Exception as e:
            self.log_test("caching_functionality", False, str(e))
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling and fail-fast behavior."""
        try:
            # Test invalid character name
            response = requests.post(f"{SERVICES['message_router']}/orchestrate", 
                                   json={
                                       "character_name": "InvalidCharacter",
                                       "input_text": "Test message",
                                       "conversation_history": [],
                                       "channel_id": "test_channel"
                                   }, 
                                   timeout=30)
            
            if response.status_code == 400:  # Should fail gracefully
                data = response.json()
                if not data.get("success", True):
                    self.log_test("error_handling_invalid_character", True, 
                                 "Properly rejected invalid character")
                    return True
                else:
                    self.log_test("error_handling_invalid_character", False, 
                                 "Should have rejected invalid character")
                    return False
            else:
                self.log_test("error_handling_invalid_character", False, 
                             f"Unexpected status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("error_handling", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all tests in the test suite."""
        print("🧪 Starting Microservices Architecture Test Suite")
        print("=" * 60)
        
        # Test 1: Service Health Checks
        print("\n📋 Phase 1: Service Health Checks")
        for service_name, service_url in SERVICES.items():
            self.test_service_health(service_name, service_url)
        
        # Test 2: Core Service Functionality
        print("\n🔧 Phase 2: Core Service Functionality")
        self.test_llm_service_functionality()
        self.test_character_config_functionality()
        
        # Test 3: Integration Tests
        print("\n🔗 Phase 3: Service Integration")
        self.test_message_router_orchestration()
        self.test_service_integration()
        
        # Test 4: Performance and Caching
        print("\n⚡ Phase 4: Performance and Caching")
        self.test_caching_functionality()
        
        # Test 5: Error Handling
        print("\n🛡️ Phase 5: Error Handling")
        self.test_error_handling()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        
        if self.failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! Microservices architecture is working correctly.")
        else:
            print(f"\n⚠️ {self.failed_tests} tests failed. Please check the services and try again.")
        
        return self.failed_tests == 0

def main():
    """Main test execution."""
    tester = MicroservicesArchitectureTester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open("microservices_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": tester.total_tests,
                "passed_tests": tester.passed_tests,
                "failed_tests": tester.failed_tests,
                "success_rate": (tester.passed_tests/tester.total_tests)*100,
                "overall_success": success
            },
            "detailed_results": tester.test_results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: microservices_test_results.json")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 