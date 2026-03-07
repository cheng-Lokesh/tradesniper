#!/usr/bin/env python3
"""
TradeSniper Basic Health Check
"""

import os
import json
import sys

def test_basic():
    print("=== TradeSniper Program Basic Test ===")
    
    # Ensure we are in project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    print(f"Project Root: {project_root}")

    # 1. Check required files
    print("\n1. Check required files:")
    required_files = [
        '.env', 
        'src/core/engine.py', 
        'src/core/sniper.py',
        'src/ui/app.py',
        'src/config/settings.py'
    ]
    # state.json is optional if not logged in
    if os.path.exists('state.json'):
        required_files.append('state.json')
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"   OK: {file} exists")
        else:
            print(f"   ERROR: {file} missing")
            missing.append(file)
    
    if missing:
        print(f"   WARNING: {len(missing)} required files are missing!")

    # 2. Check .env config
    print("\n2. Check .env config:")
    if os.path.exists('.env'):
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                env_content = f.read()
            print("   OK: .env file readable")
            
            # Check key configs
            required_keys = ['DEEPSEEK_API_KEY', 'SERVER_CHAN_KEY']
            found_keys = []
            for line in env_content.split('\n'):
                if '=' in line and not line.strip().startswith('#'):
                    key = line.split('=')[0].strip()
                    if key in required_keys:
                        found_keys.append(key)
            
            for key in required_keys:
                if key in found_keys:
                    print(f"   OK: Found config: {key}")
                else:
                    print(f"   WARNING: Missing config: {key}")
        except Exception as e:
            print(f"   ERROR: Failed to read .env: {e}")
    else:
        print("   WARNING: .env file missing (use .env.example as template)")
    
    # 3. Check state.json
    print("\n3. Check state.json:")
    if os.path.exists('state.json'):
        try:
            with open('state.json', 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            print(f"   OK: state.json is valid JSON")
            print(f"   OK: Cookies count: {len(state_data.get('cookies', []))}")
        except Exception as e:
            print(f"   ERROR: Failed to read state.json: {e}")
    else:
        print("   INFO: state.json not found (run scripts/get_token.py to generate)")
    
    # 4. Check Python dependencies
    print("\n4. Check Python dependencies:")
    try:
        import playwright
        from playwright.sync_api import sync_playwright
        print(f"   OK: playwright installed")
    except ImportError:
        print("   ERROR: playwright not installed")
    
    try:
        import dotenv
        print("   OK: python-dotenv installed")
    except ImportError:
        print("   ERROR: python-dotenv not installed")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_basic()
