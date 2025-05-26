#!/usr/bin/env python3
"""
Quick MongoDB Reset Script
Performs a complete reset without interactive prompts.
"""

import subprocess
import time
import sys

def quick_reset():
    """Perform a quick complete reset of MongoDB."""
    print("🔄 QUICK MONGODB RESET")
    print("=" * 50)
    print("⚠️ This will completely reset all MongoDB data!")
    
    steps = [
        ("🛑 Stopping MongoDB container", ['docker-compose', 'stop', 'mongodb']),
        ("🗑️ Removing MongoDB container", ['docker-compose', 'rm', '-f', 'mongodb']),
        ("💾 Removing MongoDB volumes", ['docker', 'volume', 'prune', '-f']),
        ("🚀 Starting fresh MongoDB", ['docker-compose', 'up', '-d', 'mongodb'])
    ]
    
    for step_name, command in steps:
        print(f"\n{step_name}...")
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print(f"✅ {step_name} completed")
            else:
                print(f"⚠️ {step_name} had issues: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"❌ {step_name} timed out")
        except Exception as e:
            print(f"❌ {step_name} failed: {e}")
    
    print("\n⏳ Waiting for MongoDB to initialize...")
    time.sleep(15)
    
    # Check if MongoDB is running
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
        if 'mongodb' in result.stdout:
            print("✅ MongoDB is running and ready!")
            print("🔧 You may need to restart the orchestrator to reconnect")
        else:
            print("⚠️ MongoDB may not be running properly")
    except Exception as e:
        print(f"❌ Error checking MongoDB status: {e}")
    
    print("\n🎉 Quick reset completed!")

if __name__ == "__main__":
    quick_reset() 