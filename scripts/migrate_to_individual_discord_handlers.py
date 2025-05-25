#!/usr/bin/env python3
"""
Migration script for separating Discord handlers into individual services.

This script helps migrate from the single discord-handler service to 
individual Discord handler services for Peter, Brian, and Stewie.
"""

import os
import shutil
from pathlib import Path

def backup_env_file():
    """Create a backup of the current .env file."""
    env_path = Path('.env')
    if env_path.exists():
        backup_path = Path('.env.backup')
        shutil.copy2(env_path, backup_path)
        print(f"✅ Created backup: {backup_path}")
        return True
    return False

def update_env_file():
    """Update .env file with new Discord handler URLs."""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ .env file not found. Please create one first.")
        return False
    
    # Read current .env file
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Track what we need to add/update
    new_lines = []
    found_vars = set()
    
    # Process existing lines
    for line in lines:
        line = line.strip()
        
        # Skip old Discord handler URL if it exists
        if line.startswith('DISCORD_HANDLER_URL='):
            print(f"🔄 Removing old: {line}")
            continue
        
        # Skip old individual bot Discord URLs if they exist
        if any(line.startswith(f'{bot}_BOT_DISCORD_SEND_API_URL=') for bot in ['PETER', 'BRIAN', 'STEWIE']):
            print(f"🔄 Removing old: {line}")
            continue
        
        # Keep all other lines
        new_lines.append(line)
        
        # Track which new variables we already have
        if line.startswith('PETER_DISCORD_URL='):
            found_vars.add('PETER_DISCORD_URL')
        elif line.startswith('BRIAN_DISCORD_URL='):
            found_vars.add('BRIAN_DISCORD_URL')
        elif line.startswith('STEWIE_DISCORD_URL='):
            found_vars.add('STEWIE_DISCORD_URL')
    
    # Add new Discord handler URLs if not already present
    new_vars = {
        'PETER_DISCORD_URL': 'http://peter-discord:5011/send_message',
        'BRIAN_DISCORD_URL': 'http://brian-discord:5012/send_message', 
        'STEWIE_DISCORD_URL': 'http://stewie-discord:5013/send_message'
    }
    
    # Add section header for new Discord handlers
    if any(var not in found_vars for var in new_vars.keys()):
        new_lines.append('')
        new_lines.append('# Individual Discord Handler URLs (New Architecture)')
    
    for var, default_value in new_vars.items():
        if var not in found_vars:
            new_lines.append(f'{var}={default_value}')
            print(f"✅ Added: {var}={default_value}")
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        for line in new_lines:
            f.write(line + '\n')
    
    print("✅ .env file updated successfully!")
    return True

def show_migration_summary():
    """Show summary of changes made."""
    print("\n" + "="*60)
    print("🎉 MIGRATION COMPLETE!")
    print("="*60)
    print("\nChanges made:")
    print("1. ✅ Created individual Discord handler services:")
    print("   - peter-discord (port 5011)")
    print("   - brian-discord (port 5012)")
    print("   - stewie-discord (port 5013)")
    print("\n2. ✅ Updated environment variables:")
    print("   - PETER_DISCORD_URL=http://peter-discord:5011/send_message")
    print("   - BRIAN_DISCORD_URL=http://brian-discord:5012/send_message")
    print("   - STEWIE_DISCORD_URL=http://stewie-discord:5013/send_message")
    print("\n3. ✅ Updated orchestrator to use individual handlers")
    print("\n4. ✅ Each Discord bot now runs in its own isolated process")
    
    print("\n" + "="*60)
    print("🚀 NEXT STEPS:")
    print("="*60)
    print("1. Stop any running containers:")
    print("   docker-compose down")
    print("\n2. Rebuild and start with new architecture:")
    print("   docker-compose up --build")
    print("\n3. Verify all services are healthy:")
    print("   curl http://localhost:5011/health  # Peter Discord")
    print("   curl http://localhost:5012/health  # Brian Discord")
    print("   curl http://localhost:5013/health  # Stewie Discord")
    print("   curl http://localhost:5003/health  # Orchestrator")
    
    print("\n" + "="*60)
    print("✨ BENEFITS OF NEW ARCHITECTURE:")
    print("="*60)
    print("• 🔧 Eliminates threading conflicts")
    print("• 🛡️  Better fault tolerance (if one bot fails, others continue)")
    print("• 🔍 Easier debugging (separate logs per bot)")
    print("• 📈 Better scalability (can scale bots independently)")
    print("• 🎯 Simpler architecture (one Discord client per service)")

def main():
    """Main migration function."""
    print("🔄 Discord Handler Migration Script")
    print("="*50)
    print("This script migrates from single discord-handler to individual Discord handlers.")
    print()
    
    # Create backup
    if backup_env_file():
        print("📁 Backup created successfully")
    else:
        print("⚠️  No .env file found to backup")
    
    # Update environment file
    if update_env_file():
        show_migration_summary()
    else:
        print("❌ Migration failed. Please check your .env file.")
        return False
    
    return True

if __name__ == "__main__":
    main() 