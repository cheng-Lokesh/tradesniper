#!/usr/bin/env python3
"""
检查虚拟环境中的包
"""

import subprocess
import sys

def check_venv():
    # 虚拟环境的Python路径
    venv_python = r"C:\Users\clf04\TradeSniper\.venv\Scripts\python.exe"
    
    print("Checking virtual environment packages...")
    
    # 检查playwright
    try:
        result = subprocess.run([venv_python, "-c", "import playwright; print('playwright: OK')"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print("playwright: NOT installed")
    except Exception as e:
        print(f"Error checking playwright: {e}")
    
    # 检查dotenv
    try:
        result = subprocess.run([venv_python, "-c", "import dotenv; print('dotenv: OK')"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print("dotenv: NOT installed")
    except Exception as e:
        print(f"Error checking dotenv: {e}")
    
    # 列出所有已安装的包
    print("\nInstalled packages in virtual environment:")
    try:
        result = subprocess.run([venv_python, "-m", "pip", "list"], 
                              capture_output=True, text=True)
        print(result.stdout)
    except Exception as e:
        print(f"Error listing packages: {e}")

if __name__ == "__main__":
    check_venv()