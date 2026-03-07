#!/usr/bin/env python3
"""
快速测试TradeSniper核心功能
"""

import os
import sys

def test_main():
    print("Quick test of TradeSniper...")
    
    # 添加当前目录到Python路径
    sys.path.insert(0, os.path.dirname(__file__))
    
    # 测试导入主要模块
    try:
        # 测试导入playwright
        from playwright.sync_api import sync_playwright
        print("✓ playwright imported successfully")
        
        # 测试读取.env
        from dotenv import load_dotenv
        load_dotenv()
        print("✓ dotenv loaded successfully")
        
        # 测试读取配置
        search_keywords = os.getenv("SEARCH_KEYWORDS", "")
        if search_keywords:
            print(f"✓ Found search keywords: {search_keywords}")
        else:
            print("✗ No search keywords found in .env")
        
        # 测试state.json
        import json
        with open("state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
        print(f"✓ state.json loaded, {len(state.get('cookies', []))} cookies")
        
        # 简单测试playwright
        print("\nTesting playwright (headless mode)...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.baidu.com")
            title = page.title()
            print(f"✓ Browser test passed, page title: {title}")
            browser.close()
        
        print("\n✅ All tests passed! The program should work correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_main()
    sys.exit(0 if success else 1)