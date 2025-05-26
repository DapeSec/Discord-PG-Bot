#!/usr/bin/env python3
"""
Temporary script to lower quality control threshold for cold start issues.
"""

import os
import subprocess

def lower_threshold_temporarily():
    """Lower the quality control threshold temporarily."""
    print("🔧 TEMPORARILY LOWERING QUALITY CONTROL THRESHOLD")
    print("=" * 60)
    
    print("Current threshold: 70.0")
    print("Temporarily lowering to: 60.0 for cold start recovery")
    
    # Set environment variable for the running containers
    commands = [
        "docker exec orchestrator sh -c 'export QUALITY_CONTROL_MIN_RATING=60.0'",
        "docker restart orchestrator"
    ]
    
    for cmd in commands:
        print(f"🔄 Running: {cmd}")
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✅ Success")
            else:
                print(f"⚠️ Warning: {result.stderr}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🎯 RECOMMENDATIONS:")
    print("1. Try asking Brian the same question again")
    print("2. If responses improve, gradually increase threshold back to 70")
    print("3. Monitor response quality for a few interactions")
    print("4. Consider adding 'cold start' detection to automatically lower threshold")

if __name__ == "__main__":
    lower_threshold_temporarily() 