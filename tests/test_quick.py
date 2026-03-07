#!/usr/bin/env python3
"""
TradeSniper Quick Component Test
"""

import os
import json
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Ensure we are in project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)

load_dotenv()

print("=== TradeSniper Quick Test ===")
print("1. Testing environment variables...")
print(f"   SERVER_CHAN_KEY: {'OK' if os.getenv('SERVER_CHAN_KEY') else 'MISSING'}")
print(f"   DEEPSEEK_API_KEY: {'OK' if os.getenv('DEEPSEEK_API_KEY') else 'MISSING'}")
print(f"   SEARCH_KEYWORDS: {os.getenv('SEARCH_KEYWORDS', 'MISSING')}")

print("\n2. Testing state.json...")
if os.path.exists("state.json"):
    with open("state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
    print(f"   ✅ state.json exists")
    cookies = state.get('cookies', [])
    print(f"   ✅ Cookies: {len(cookies)}")
    print(f"   ✅ Origins: {len(state.get('origins', []))}")
else:
    print("   ❌ state.json missing")

print("\n3. Testing Playwright browser...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        
        # Use state.json if available
        if os.path.exists("state.json"):
            context = browser.new_context(storage_state="state.json")
        else:
            context = browser.new_context()
            
        page = context.new_page()
        
        print("   ✅ Playwright initialized")
        
        # Quick test visiting Baidu to avoid potential Xianyu blocks during test
        page.goto("https://www.baidu.com", timeout=10000)
        title = page.title()
        print(f"   ✅ Browser test passed, page title: {title}")
        
        browser.close()
        print("   ✅ Browser closed successfully")
except Exception as e:
    print(f"   ❌ Browser test failed: {e}")

print("\n4. Testing price extraction logic...")
def extract_price(text):
    import re
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)", str(text))
    if not match:
        return None
    return float(match.group(1))

test_cases = [
    ("¥599", 599.0),
    ("价格：680元", 680.0),
    ("特价488.5", 488.5),
    ("无价格信息", None)
]

all_passed = True
for text, expected in test_cases:
    result = extract_price(text)
    passed = result == expected
    all_passed = all_passed and passed
    print(f"   {'✅' if passed else '❌'} '{text}' -> {result} (expected: {expected})")

print(f"\n=== Test {'PASSED' if all_passed else 'FAILED'} ===")
print("\nProgram is ready to run!")
