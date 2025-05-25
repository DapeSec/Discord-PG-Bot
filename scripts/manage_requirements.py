#!/usr/bin/env python3
"""
Service Requirements Management Utility

This script helps manage service-specific requirements files for the Discord Family Guy Bot system.
It provides utilities to check for outdated packages, validate requirements, and generate reports.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Set

# Service requirements mapping
REQUIREMENTS_FILES = {
    'orchestrator': 'requirements-orchestrator.txt',
    'rag-retriever': 'requirements-rag-retriever.txt',
    'discord-handler': 'requirements-discord-handler.txt',
    'bot-config': 'requirements-bot-config.txt',
    'rag-crawler': 'requirements-rag-crawler.txt',
    'testing': 'requirements-testing.txt'
}

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent

def read_requirements(file_path: Path) -> Set[str]:
    """Read requirements from a file and return as a set of package names."""
    if not file_path.exists():
        print(f"Warning: {file_path} does not exist")
        return set()
    
    packages = set()
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Extract package name (before ==, >=, etc.)
                package_name = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0]
                packages.add(package_name.strip())
    
    return packages

def find_duplicates() -> Dict[str, List[str]]:
    """Find packages that appear in multiple requirements files."""
    project_root = get_project_root()
    package_to_files = {}
    
    for service, filename in REQUIREMENTS_FILES.items():
        file_path = project_root / filename
        packages = read_requirements(file_path)
        
        for package in packages:
            if package not in package_to_files:
                package_to_files[package] = []
            package_to_files[package].append(service)
    
    # Find packages that appear in multiple files
    duplicates = {pkg: services for pkg, services in package_to_files.items() if len(services) > 1}
    return duplicates

def check_outdated(service: str = None) -> None:
    """Check for outdated packages in requirements files."""
    project_root = get_project_root()
    
    services_to_check = [service] if service else REQUIREMENTS_FILES.keys()
    
    for svc in services_to_check:
        if svc not in REQUIREMENTS_FILES:
            print(f"Unknown service: {svc}")
            continue
            
        filename = REQUIREMENTS_FILES[svc]
        file_path = project_root / filename
        
        if not file_path.exists():
            print(f"Requirements file not found: {file_path}")
            continue
        
        print(f"\n🔍 Checking outdated packages for {svc}...")
        print(f"Requirements file: {filename}")
        
        try:
            # Create a temporary virtual environment to check packages
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'list', '--outdated', '--format=json'
            ], capture_output=True, text=True, check=True)
            
            if result.stdout.strip():
                print("Outdated packages found (system-wide check):")
                print(result.stdout)
            else:
                print("✅ No outdated packages found")
                
        except subprocess.CalledProcessError as e:
            print(f"Error checking outdated packages: {e}")

def validate_requirements() -> bool:
    """Validate all requirements files for syntax and consistency."""
    project_root = get_project_root()
    all_valid = True
    
    print("🔍 Validating requirements files...")
    
    for service, filename in REQUIREMENTS_FILES.items():
        file_path = project_root / filename
        
        if not file_path.exists():
            print(f"❌ Missing requirements file: {filename}")
            all_valid = False
            continue
        
        print(f"\n📋 Validating {service} ({filename})...")
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Basic validation - check for version specifier
                    if '==' not in line and '>=' not in line and '<=' not in line and '~=' not in line:
                        print(f"⚠️  Line {i}: No version specifier for '{line}'")
            
            print(f"✅ {service} requirements file is valid")
            
        except Exception as e:
            print(f"❌ Error validating {filename}: {e}")
            all_valid = False
    
    return all_valid

def generate_report() -> None:
    """Generate a comprehensive report of all requirements."""
    project_root = get_project_root()
    
    print("📊 Service Requirements Report")
    print("=" * 50)
    
    total_packages = 0
    service_stats = {}
    
    for service, filename in REQUIREMENTS_FILES.items():
        file_path = project_root / filename
        packages = read_requirements(file_path)
        
        service_stats[service] = {
            'file': filename,
            'packages': len(packages),
            'exists': file_path.exists()
        }
        
        total_packages += len(packages)
        
        print(f"\n🔧 {service.upper()}")
        print(f"   File: {filename}")
        print(f"   Packages: {len(packages)}")
        print(f"   Status: {'✅ Exists' if file_path.exists() else '❌ Missing'}")
    
    print(f"\n📈 Summary:")
    print(f"   Total services: {len(REQUIREMENTS_FILES)}")
    print(f"   Total packages (with duplicates): {total_packages}")
    
    # Show duplicates
    duplicates = find_duplicates()
    if duplicates:
        print(f"\n🔄 Shared Dependencies ({len(duplicates)} packages):")
        for package, services in duplicates.items():
            print(f"   {package}: {', '.join(services)}")
    else:
        print("\n✅ No shared dependencies found")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Manage service-specific requirements files')
    parser.add_argument('command', choices=['validate', 'outdated', 'duplicates', 'report'],
                       help='Command to execute')
    parser.add_argument('--service', choices=list(REQUIREMENTS_FILES.keys()),
                       help='Specific service to check (for outdated command)')
    
    args = parser.parse_args()
    
    if args.command == 'validate':
        success = validate_requirements()
        sys.exit(0 if success else 1)
    
    elif args.command == 'outdated':
        check_outdated(args.service)
    
    elif args.command == 'duplicates':
        duplicates = find_duplicates()
        if duplicates:
            print("🔄 Shared dependencies found:")
            for package, services in duplicates.items():
                print(f"   {package}: {', '.join(services)}")
        else:
            print("✅ No shared dependencies found")
    
    elif args.command == 'report':
        generate_report()

if __name__ == '__main__':
    main() 