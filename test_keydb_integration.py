#!/usr/bin/env python3
"""
Test script for KeyDB integration in Discord Family Guy Bot.
Run this to verify that KeyDB caching is working properly.
"""

import os
import sys
import time
import requests
import json
from datetime import datetime

# Add src to path for imports
sys.path.append('src')

def test_cache_utilities():
    """Test the cache utilities directly."""
    print("🧪 Testing KeyDB Cache Utilities...")
    
    try:
        from src.app.utils.cache import get_cache, cache_recent_response, get_recent_responses
        
        # Test basic cache operations
        cache = get_cache("test")
        
        # Test set/get
        test_key = "test_key"
        test_value = {"message": "Hello KeyDB!", "timestamp": datetime.now().isoformat()}
        
        print(f"   Setting cache key: {test_key}")
        result = cache.set(test_key, test_value, ttl=60)
        print(f"   Set result: {result}")
        
        print(f"   Getting cache key: {test_key}")
        retrieved = cache.get(test_key)
        print(f"   Retrieved: {retrieved}")
        
        # Test response caching
        print(f"   Testing response caching...")
        cache_result = cache_recent_response("Peter", "This is a test response", max_responses=10)
        print(f"   Cache response result: {cache_result}")
        
        recent = get_recent_responses("Peter", limit=5)
        print(f"   Recent responses: {recent}")
        
        print("✅ Cache utilities test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Cache utilities test failed: {e}")
        return False

def test_service_health_checks():
    """Test health check endpoints of services."""
    print("\n🏥 Testing Service Health Checks...")
    
    services = [
        ("Orchestrator", "http://localhost:5003/health"),
        ("Peter Discord", "http://localhost:5011/health"),
        ("RAG Retriever", "http://localhost:5005/health"),
    ]
    
    results = {}
    
    for service_name, url in services:
        try:
            print(f"   Checking {service_name} at {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                cache_status = data.get('cache', {}).get('status', 'not_reported')
                print(f"   ✅ {service_name}: Healthy (Cache: {cache_status})")
                results[service_name] = {"status": "healthy", "cache": cache_status}
            else:
                print(f"   ⚠️ {service_name}: Status {response.status_code}")
                results[service_name] = {"status": f"status_{response.status_code}", "cache": "unknown"}
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ {service_name}: Service not running")
            results[service_name] = {"status": "not_running", "cache": "unknown"}
        except Exception as e:
            print(f"   ❌ {service_name}: Error - {e}")
            results[service_name] = {"status": "error", "cache": "unknown"}
    
    return results

def test_rag_caching():
    """Test RAG query caching."""
    print("\n🔍 Testing RAG Query Caching...")
    
    try:
        url = "http://localhost:5005/retrieve"
        test_query = {
            "query": "What is Peter Griffin's favorite activity?",
            "num_results": 3
        }
        
        print(f"   Sending test query: {test_query['query']}")
        
        # First request (should be fresh)
        start_time = time.time()
        response1 = requests.post(url, json=test_query, timeout=30)
        first_duration = time.time() - start_time
        
        if response1.status_code == 200:
            data1 = response1.json()
            cached1 = data1.get('cached', False)
            print(f"   ✅ First request: {first_duration:.2f}s (Cached: {cached1})")
            
            # Second request (should be cached)
            start_time = time.time()
            response2 = requests.post(url, json=test_query, timeout=30)
            second_duration = time.time() - start_time
            
            if response2.status_code == 200:
                data2 = response2.json()
                cached2 = data2.get('cached', False)
                print(f"   ✅ Second request: {second_duration:.2f}s (Cached: {cached2})")
                
                if second_duration < first_duration:
                    print(f"   🎯 Cache working! Second request was {first_duration/second_duration:.1f}x faster")
                else:
                    print(f"   ⚠️ No speed improvement detected")
                    
                return True
            else:
                print(f"   ❌ Second request failed: {response2.status_code}")
                return False
        else:
            print(f"   ❌ First request failed: {response1.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ RAG Retriever service not running")
        return False
    except Exception as e:
        print(f"   ❌ RAG caching test failed: {e}")
        return False

def test_docker_keydb():
    """Test if KeyDB is running in Docker."""
    print("\n🐳 Testing KeyDB Docker Container...")
    
    try:
        import subprocess
        
        # Check if KeyDB container is running
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=keydb", "--format", "table {{.Names}}\t{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if "keydb" in output:
                print(f"   ✅ KeyDB container status:")
                for line in output.split('\n'):
                    if line.strip():
                        print(f"      {line}")
                return True
            else:
                print(f"   ❌ KeyDB container not found")
                return False
        else:
            print(f"   ❌ Docker command failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ Docker command timed out")
        return False
    except FileNotFoundError:
        print(f"   ⚠️ Docker not found in PATH")
        return False
    except Exception as e:
        print(f"   ❌ Docker test failed: {e}")
        return False

def main():
    """Run all KeyDB integration tests."""
    print("🚀 KeyDB Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Docker KeyDB Container", test_docker_keydb),
        ("Cache Utilities", test_cache_utilities),
        ("Service Health Checks", test_service_health_checks),
        ("RAG Query Caching", test_rag_caching),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! KeyDB integration is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main()) 