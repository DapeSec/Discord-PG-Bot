#!/usr/bin/env python3
"""
Wait for services to be ready before starting dependent services.
This is a Python implementation of wait-for-it functionality.
"""

import socket
import time
import argparse
import sys
import requests
from urllib.parse import urlparse


def wait_for_port(host, port, timeout=60):
    """Wait for a port to be open on a host."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"✓ {host}:{port} is available")
                return True
        except socket.gaierror:
            pass
        except Exception as e:
            print(f"Error checking {host}:{port}: {e}")
        
        print(f"⏳ Waiting for {host}:{port}...")
        time.sleep(2)
    
    print(f"✗ Timeout waiting for {host}:{port}")
    return False


def wait_for_health(url, timeout=60):
    """Wait for a health endpoint to return 200."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {url} is healthy")
                return True
            else:
                print(f"⏳ {url} returned {response.status_code}, waiting...")
        except requests.exceptions.RequestException:
            print(f"⏳ Waiting for {url} to be healthy...")
        
        time.sleep(5)
    
    print(f"✗ Timeout waiting for {url} to be healthy")
    return False


def main():
    parser = argparse.ArgumentParser(description='Wait for services to be ready')
    parser.add_argument('--host', required=True, help='Host to check')
    parser.add_argument('--port', type=int, help='Port to check')
    parser.add_argument('--health-url', help='Health endpoint URL to check')
    parser.add_argument('--timeout', type=int, default=60, help='Timeout in seconds')
    
    args = parser.parse_args()
    
    if args.port:
        if not wait_for_port(args.host, args.port, args.timeout):
            sys.exit(1)
    
    if args.health_url:
        if not wait_for_health(args.health_url, args.timeout):
            sys.exit(1)
    
    print("All services are ready!")


if __name__ == '__main__':
    main() 