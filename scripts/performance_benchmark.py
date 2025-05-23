#!/usr/bin/env python3
"""
Performance benchmark script for Discord Family Guy Bots
Measures response times and resource usage of the centralized LLM architecture
"""

import requests
import time
import statistics
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTester:
    def __init__(self, orchestrator_url="http://localhost:5003"):
        self.orchestrator_url = orchestrator_url
        self.results = []
        
    def test_single_request(self, character, query, test_id):
        """Test a single request and measure response time."""
        start_time = time.time()
        
        payload = {
            "user_query": query,
            "channel_id": "benchmark_channel",
            "initiator_bot_name": character,
            "initiator_mention": f"<@{character.lower()}_id>",
            "human_user_display_name": "BenchmarkUser"
        }
        
        try:
            response = requests.post(
                f"{self.orchestrator_url}/orchestrate",
                json=payload,
                timeout=30
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            result = {
                "test_id": test_id,
                "character": character,
                "query": query,
                "response_time": response_time,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "timestamp": start_time
            }
            
            if response.status_code == 200:
                logger.info(f"✅ {character} response in {response_time:.2f}s")
            else:
                logger.warning(f"❌ {character} failed with status {response.status_code}")
                
            return result
            
        except requests.exceptions.Timeout:
            end_time = time.time()
            response_time = end_time - start_time
            logger.error(f"⏰ {character} timeout after {response_time:.2f}s")
            
            return {
                "test_id": test_id,
                "character": character,
                "query": query,
                "response_time": response_time,
                "status_code": 408,
                "success": False,
                "timestamp": start_time,
                "error": "timeout"
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            logger.error(f"💥 {character} error: {e}")
            
            return {
                "test_id": test_id,
                "character": character,
                "query": query,
                "response_time": response_time,
                "status_code": 500,
                "success": False,
                "timestamp": start_time,
                "error": str(e)
            }
    
    def run_sequential_test(self, num_requests=10):
        """Run sequential requests to measure baseline performance."""
        logger.info(f"🔄 Running {num_requests} sequential requests...")
        
        characters = ["Peter", "Brian", "Stewie"]
        queries = [
            "Tell me a joke",
            "What's your opinion on Family Guy?",
            "How are you feeling today?",
            "What's your favorite memory?"
        ]
        
        results = []
        for i in range(num_requests):
            character = characters[i % len(characters)]
            query = queries[i % len(queries)]
            
            result = self.test_single_request(character, query, f"seq_{i}")
            results.append(result)
            
            # Small delay between requests
            time.sleep(0.5)
            
        return results
    
    def run_concurrent_test(self, num_requests=10, max_workers=3):
        """Run concurrent requests to test load handling."""
        logger.info(f"⚡ Running {num_requests} concurrent requests with {max_workers} workers...")
        
        characters = ["Peter", "Brian", "Stewie"]
        queries = [
            "Tell me something interesting",
            "What do you think about this?",
            "How would you handle this situation?",
            "Give me your perspective"
        ]
        
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all requests
            futures = []
            for i in range(num_requests):
                character = characters[i % len(characters)]
                query = queries[i % len(queries)]
                
                future = executor.submit(self.test_single_request, character, query, f"con_{i}")
                futures.append(future)
            
            # Collect results as they complete
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
        return results
    
    def analyze_results(self, results, test_type):
        """Analyze and report performance results."""
        logger.info(f"\n📊 {test_type.upper()} TEST RESULTS")
        logger.info("=" * 50)
        
        if not results:
            logger.warning("No results to analyze")
            return
        
        # Basic stats
        total_requests = len(results)
        successful_requests = sum(1 for r in results if r["success"])
        success_rate = (successful_requests / total_requests) * 100
        
        # Response time stats
        response_times = [r["response_time"] for r in results if r["success"]]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            if len(response_times) > 1:
                stdev_response_time = statistics.stdev(response_times)
            else:
                stdev_response_time = 0
        else:
            avg_response_time = median_response_time = min_response_time = max_response_time = stdev_response_time = 0
        
        # Character breakdown
        character_stats = {}
        for character in ["Peter", "Brian", "Stewie"]:
            char_results = [r for r in results if r["character"] == character]
            char_success = sum(1 for r in char_results if r["success"])
            char_total = len(char_results)
            char_success_rate = (char_success / char_total * 100) if char_total > 0 else 0
            
            char_times = [r["response_time"] for r in char_results if r["success"]]
            char_avg_time = statistics.mean(char_times) if char_times else 0
            
            character_stats[character] = {
                "success_rate": char_success_rate,
                "avg_response_time": char_avg_time,
                "total_requests": char_total
            }
        
        # Print results
        logger.info(f"Total Requests: {total_requests}")
        logger.info(f"Successful Requests: {successful_requests}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info(f"Average Response Time: {avg_response_time:.2f}s")
        logger.info(f"Median Response Time: {median_response_time:.2f}s")
        logger.info(f"Min Response Time: {min_response_time:.2f}s")
        logger.info(f"Max Response Time: {max_response_time:.2f}s")
        logger.info(f"Response Time Std Dev: {stdev_response_time:.2f}s")
        
        logger.info("\n📈 CHARACTER BREAKDOWN:")
        for character, stats in character_stats.items():
            logger.info(f"{character}: {stats['success_rate']:.1f}% success, "
                       f"{stats['avg_response_time']:.2f}s avg, "
                       f"{stats['total_requests']} total")
        
        return {
            "test_type": test_type,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "median_response_time": median_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time,
            "stdev_response_time": stdev_response_time,
            "character_stats": character_stats
        }
    
    def run_full_benchmark(self):
        """Run complete performance benchmark suite."""
        logger.info("🚀 STARTING PERFORMANCE BENCHMARK")
        logger.info("=" * 60)
        
        # Test orchestrator health first
        try:
            health_response = requests.get(f"{self.orchestrator_url}/health", timeout=10)
            if health_response.status_code != 200:
                logger.error("❌ Orchestrator health check failed")
                return
                
            logger.info("✅ Orchestrator health check passed")
        except Exception as e:
            logger.error(f"❌ Cannot connect to orchestrator: {e}")
            return
        
        # Run sequential test
        sequential_results = self.run_sequential_test(num_requests=5)
        sequential_analysis = self.analyze_results(sequential_results, "sequential")
        
        # Wait between tests
        time.sleep(2)
        
        # Run concurrent test
        concurrent_results = self.run_concurrent_test(num_requests=6, max_workers=3)
        concurrent_analysis = self.analyze_results(concurrent_results, "concurrent")
        
        # Final summary
        logger.info("\n🏁 BENCHMARK SUMMARY")
        logger.info("=" * 60)
        
        if sequential_analysis and concurrent_analysis:
            seq_avg = sequential_analysis['avg_response_time']
            con_avg = concurrent_analysis['avg_response_time']
            
            logger.info(f"Sequential Average: {seq_avg:.2f}s")
            logger.info(f"Concurrent Average: {con_avg:.2f}s")
            
            if con_avg > 0 and seq_avg > 0:
                slowdown = (con_avg / seq_avg - 1) * 100
                logger.info(f"Concurrent Slowdown: {slowdown:.1f}%")
            
            seq_success = sequential_analysis['success_rate']
            con_success = concurrent_analysis['success_rate']
            
            logger.info(f"Sequential Success Rate: {seq_success:.1f}%")
            logger.info(f"Concurrent Success Rate: {con_success:.1f}%")
            
        logger.info("\n✨ Performance benchmark completed!")

def main():
    """Main benchmark execution."""
    tester = PerformanceTester()
    tester.run_full_benchmark()

if __name__ == "__main__":
    main() 