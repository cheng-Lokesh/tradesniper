#!/usr/bin/env python3
"""
测试环境变量读取
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("Testing environment variables...")
print(f"SERVER_CHAN_KEY: {os.getenv('SERVER_CHAN_KEY')}")
print(f"DEEPSEEK_API_KEY: {os.getenv('DEEPSEEK_API_KEY')}")
print(f"SEARCH_KEYWORDS: {os.getenv('SEARCH_KEYWORDS')}")

# 检查是否为空
if not os.getenv('SERVER_CHAN_KEY'):
    print("ERROR: SERVER_CHAN_KEY is empty!")
if not os.getenv('DEEPSEEK_API_KEY'):
    print("ERROR: DEEPSEEK_API_KEY is empty!")
if not os.getenv('SEARCH_KEYWORDS'):
    print("ERROR: SEARCH_KEYWORDS is empty!")

print("\nChecking state.json...")
if os.path.exists("state.json"):
    import json
    with open("state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
    print(f"state.json exists, cookies: {len(state.get('cookies', []))}, origins: {len(state.get('origins', []))}")
else:
    print("ERROR: state.json does not exist!")

print("\nAll checks completed.")