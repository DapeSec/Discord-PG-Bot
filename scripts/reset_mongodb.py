#!/usr/bin/env python3
"""
MongoDB Reset Script for Discord Bot Project
Provides multiple options to reset MongoDB data safely.
"""

import sys
import os
import subprocess
import time
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def check_docker_status():
    """Check if Docker is running and what containers are active."""
    print("🐳 CHECKING DOCKER STATUS")
    print("=" * 50)
    
    try:
        # Check if Docker is running
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Docker is running")
            
            # Check for MongoDB container
            if 'mongodb' in result.stdout or 'mongo' in result.stdout:
                print("📊 MongoDB container found:")
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'mongodb' in line.lower() or 'mongo' in line.lower():
                        print(f"   {line}")
                return True
            else:
                print("⚠️ No MongoDB container currently running")
                return False
        else:
            print("❌ Docker is not running or not accessible")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Docker command timed out")
        return False
    except FileNotFoundError:
        print("❌ Docker not found. Is Docker installed?")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker: {e}")
        return False

def stop_mongodb_container():
    """Stop the MongoDB container."""
    print("\n🛑 STOPPING MONGODB CONTAINER")
    print("=" * 50)
    
    try:
        # Stop MongoDB container
        result = subprocess.run(['docker-compose', 'stop', 'mongodb'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ MongoDB container stopped successfully")
            return True
        else:
            print(f"⚠️ Error stopping MongoDB: {result.stderr}")
            
            # Try alternative method
            print("🔄 Trying alternative stop method...")
            result2 = subprocess.run(['docker', 'stop', 'mongodb'], 
                                   capture_output=True, text=True, timeout=30)
            if result2.returncode == 0:
                print("✅ MongoDB container stopped with alternative method")
                return True
            else:
                print(f"❌ Failed to stop MongoDB container: {result2.stderr}")
                return False
                
    except subprocess.TimeoutExpired:
        print("❌ Stop command timed out")
        return False
    except Exception as e:
        print(f"❌ Error stopping MongoDB: {e}")
        return False

def remove_mongodb_container():
    """Remove the MongoDB container completely."""
    print("\n🗑️ REMOVING MONGODB CONTAINER")
    print("=" * 50)
    
    try:
        # Remove MongoDB container
        result = subprocess.run(['docker-compose', 'rm', '-f', 'mongodb'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ MongoDB container removed successfully")
            return True
        else:
            print(f"⚠️ Error removing MongoDB: {result.stderr}")
            
            # Try alternative method
            print("🔄 Trying alternative removal method...")
            result2 = subprocess.run(['docker', 'rm', '-f', 'mongodb'], 
                                   capture_output=True, text=True, timeout=30)
            if result2.returncode == 0:
                print("✅ MongoDB container removed with alternative method")
                return True
            else:
                print(f"❌ Failed to remove MongoDB container: {result2.stderr}")
                return False
                
    except subprocess.TimeoutExpired:
        print("❌ Remove command timed out")
        return False
    except Exception as e:
        print(f"❌ Error removing MongoDB: {e}")
        return False

def remove_mongodb_volumes():
    """Remove MongoDB data volumes."""
    print("\n💾 REMOVING MONGODB VOLUMES")
    print("=" * 50)
    
    try:
        # List volumes first
        result = subprocess.run(['docker', 'volume', 'ls'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            volumes = result.stdout
            mongodb_volumes = []
            
            # Look for MongoDB-related volumes
            for line in volumes.split('\n'):
                if 'mongodb' in line.lower() or 'mongo' in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        mongodb_volumes.append(parts[-1])
            
            if mongodb_volumes:
                print(f"📊 Found MongoDB volumes: {mongodb_volumes}")
                
                for volume in mongodb_volumes:
                    print(f"🗑️ Removing volume: {volume}")
                    remove_result = subprocess.run(['docker', 'volume', 'rm', volume], 
                                                 capture_output=True, text=True, timeout=10)
                    
                    if remove_result.returncode == 0:
                        print(f"✅ Volume {volume} removed successfully")
                    else:
                        print(f"⚠️ Failed to remove volume {volume}: {remove_result.stderr}")
                
                return True
            else:
                print("📊 No MongoDB volumes found")
                return True
        else:
            print(f"❌ Failed to list volumes: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error removing volumes: {e}")
        return False

def start_fresh_mongodb():
    """Start a fresh MongoDB container."""
    print("\n🚀 STARTING FRESH MONGODB")
    print("=" * 50)
    
    try:
        # Start MongoDB with docker-compose
        result = subprocess.run(['docker-compose', 'up', '-d', 'mongodb'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Fresh MongoDB container started successfully")
            
            # Wait a moment for MongoDB to initialize
            print("⏳ Waiting for MongoDB to initialize...")
            time.sleep(10)
            
            # Check if it's running
            check_result = subprocess.run(['docker', 'ps'], 
                                        capture_output=True, text=True, timeout=10)
            
            if 'mongodb' in check_result.stdout:
                print("✅ MongoDB is running and ready")
                return True
            else:
                print("⚠️ MongoDB started but may not be ready yet")
                return True
        else:
            print(f"❌ Failed to start MongoDB: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Start command timed out")
        return False
    except Exception as e:
        print(f"❌ Error starting MongoDB: {e}")
        return False

def reset_via_python():
    """Reset MongoDB data using Python MongoDB client."""
    print("\n🐍 RESETTING DATA VIA PYTHON CLIENT")
    print("=" * 50)
    
    try:
        from app.orchestrator.server import mongo_client, conversations_collection
        
        if not mongo_client:
            print("❌ MongoDB client not available")
            return False
        
        # Test connection
        mongo_client.admin.command('ping')
        print("✅ Connected to MongoDB")
        
        # Get database
        db = mongo_client.discord_bot_conversations
        
        # List all collections
        collections = db.list_collection_names()
        print(f"📊 Found collections: {collections}")
        
        # Drop each collection
        for collection_name in collections:
            db.drop_collection(collection_name)
            print(f"🗑️ Dropped collection: {collection_name}")
        
        print("✅ All data reset successfully via Python client")
        return True
        
    except ImportError:
        print("❌ Cannot import MongoDB client (orchestrator not running?)")
        return False
    except Exception as e:
        print(f"❌ Error resetting data: {e}")
        return False

def backup_current_data():
    """Create a backup of current MongoDB data."""
    print("\n💾 CREATING BACKUP OF CURRENT DATA")
    print("=" * 50)
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"mongodb_backup_{timestamp}"
        
        # Create backup using mongodump
        result = subprocess.run([
            'docker', 'exec', 'mongodb', 'mongodump', 
            '--db', 'discord_bot_conversations',
            '--out', f'/tmp/{backup_dir}'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ Backup created: {backup_dir}")
            
            # Copy backup to host
            copy_result = subprocess.run([
                'docker', 'cp', f'mongodb:/tmp/{backup_dir}', f'./{backup_dir}'
            ], capture_output=True, text=True, timeout=30)
            
            if copy_result.returncode == 0:
                print(f"✅ Backup copied to host: ./{backup_dir}")
                return True
            else:
                print(f"⚠️ Backup created but failed to copy to host: {copy_result.stderr}")
                return True
        else:
            print(f"❌ Failed to create backup: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return False

def main():
    """Main function with interactive menu."""
    print("🔄 MONGODB RESET TOOL")
    print("=" * 50)
    print("⚠️  WARNING: This will delete all conversation history and bot data!")
    print()
    
    while True:
        print("📋 Reset Options:")
        print("1. 🔍 Check current status")
        print("2. 💾 Backup current data first")
        print("3. 🐍 Soft reset (clear data, keep container)")
        print("4. 🔄 Medium reset (restart container)")
        print("5. 🗑️ Full reset (remove container and volumes)")
        print("6. 🚀 Start fresh MongoDB")
        print("7. 🛠️ Complete reset workflow")
        print("8. 🚪 Exit")
        
        choice = input("\nSelect an option (1-8): ").strip()
        
        if choice == "1":
            check_docker_status()
            
        elif choice == "2":
            backup_current_data()
            
        elif choice == "3":
            if reset_via_python():
                print("\n✅ Soft reset completed!")
            else:
                print("\n❌ Soft reset failed!")
                
        elif choice == "4":
            stop_mongodb_container()
            time.sleep(2)
            start_fresh_mongodb()
            
        elif choice == "5":
            confirm = input("⚠️ This will permanently delete all data. Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                stop_mongodb_container()
                remove_mongodb_container()
                remove_mongodb_volumes()
                print("\n✅ Full reset completed!")
            else:
                print("❌ Full reset cancelled")
                
        elif choice == "6":
            start_fresh_mongodb()
            
        elif choice == "7":
            confirm = input("⚠️ This will do a complete reset. Continue? (yes/no): ")
            if confirm.lower() == 'yes':
                print("\n🔄 Starting complete reset workflow...")
                
                # Step 1: Backup (optional)
                backup_choice = input("Create backup first? (y/n): ")
                if backup_choice.lower() == 'y':
                    backup_current_data()
                
                # Step 2: Stop and remove
                stop_mongodb_container()
                remove_mongodb_container()
                remove_mongodb_volumes()
                
                # Step 3: Start fresh
                start_fresh_mongodb()
                
                print("\n🎉 Complete reset workflow finished!")
                print("✅ MongoDB is now fresh and ready to use")
                print("🔧 You may need to restart the orchestrator to reconnect")
            else:
                print("❌ Complete reset cancelled")
                
        elif choice == "8":
            print("👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please select 1-8.")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    main() 