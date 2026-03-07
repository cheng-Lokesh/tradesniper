#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的测试脚本，检查TradeSniper程序的核心功能
"""

import os
import json
import sys

def test_basic():
    print("=== TradeSniper 程序基本测试 ===")
    
    # 1. 检查必要文件
    print("\n1. 检查必要文件:")
    required_files = ['.env', 'state.json', 'trade_engine.py', 'web_sniper.py']
    for file in required_files:
        if os.path.exists(file):
            print(f"   ✓ {file} 存在")
        else:
            print(f"   ✗ {file} 不存在")
    
    # 2. 检查.env配置
    print("\n2. 检查.env配置:")
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()
        print("   ✓ .env 文件可读取")
        
        # 检查关键配置
        required_keys = ['SEARCH_KEYWORDS', 'MAX_ACCEPT_PRICE']
        for line in env_content.split('\n'):
            if '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                if key in required_keys:
                    print(f"   ✓ 找到配置: {key}")
    except Exception as e:
        print(f"   ✗ 读取.env失败: {e}")
    
    # 3. 检查state.json
    print("\n3. 检查state.json:")
    try:
        with open('state.json', 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        print(f"   ✓ state.json 有效JSON")
        print(f"   ✓ cookies数量: {len(state_data.get('cookies', []))}")
        print(f"   ✓ origins数量: {len(state_data.get('origins', []))}")
    except Exception as e:
        print(f"   ✗ 读取state.json失败: {e}")
    
    # 4. 检查Python依赖
    print("\n4. 检查Python依赖:")
    try:
        import playwright
        print(f"   ✓ playwright 版本: {playwright.__version__}")
    except ImportError:
        print("   ✗ playwright 未安装")
    
    try:
        import dotenv
        print("   ✓ python-dotenv 已安装")
    except ImportError:
        print("   ✗ python-dotenv 未安装")
    
    # 5. 测试网络连接
    print("\n5. 测试网络连接:")
    try:
        import urllib.request
        with urllib.request.urlopen('https://www.baidu.com', timeout=5) as response:
            print(f"   ✓ 网络连接正常 (HTTP {response.status})")
    except Exception as e:
        print(f"   ✗ 网络连接失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    test_basic()