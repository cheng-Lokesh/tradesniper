#!/usr/bin/env python3
"""
修复trade_engine.py文件中的编码问题
"""

import re

def fix_file_encoding(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换常见的表情符号
    replacements = {
        "🕵️‍♂️": "Agent",
        "⚠️": "Warning",
        "⏰": "Time",
        "✅": "OK",
        "❌": "Error",
        "🌊": "Searching",
        "⏳": "Waiting",
        "📸": "Screenshot",
        "🏁": "Done",
        "💰": "Price",
        "🎯": "Target",
        "🚨": "Alert",
        "📱": "Phone",
        "🔍": "Search",
        "📊": "Stats",
        "⚙️": "Config",
        "🔗": "Link",
        "📝": "Note",
        "🔔": "Notify",
        "🤖": "AI"
    }
    
    for emoji, text in replacements.items():
        content = content.replace(emoji, text)
    
    # 替换一些可能的中文错误信息为英文
    chinese_to_english = {
        "缺少有效的state.json": "Missing valid state.json",
        "缺少 state.json": "Missing state.json",
        "请先运行 get_token.py 生成登录态": "Please run get_token.py first to generate login state",
        "缺少必要环境变量": "Missing required environment variables",
        "为空，请至少提供一个关键词": "is empty, please provide at least one keyword",
        "Agent 已经潜伏在暗处，准备巡逻": "Agent is lurking in the dark, ready to patrol",
        "巡逻打卡": "Patrol check-in",
        "Playwright 初始化失败，已切换 HTTP 模式": "Playwright initialization failed, switched to HTTP mode",
        "Agent 启动：正在验证真身令牌": "Agent starting: verifying identity token",
        "正在携带令牌潜入目标水域": "Carrying token to infiltrate target waters",
        "正在等待商品数据渲染": "Waiting for product data to render",
        "咔嚓！现场照片已拍下": "Click! Scene photo taken",
        "成功突入！当前页面标题是": "Successfully breached! Current page title is",
        "巡逻结束，Agent 安全撤离": "Patrol ended, Agent safely evacuated"
    }
    
    for chinese, english in chinese_to_english.items():
        content = content.replace(chinese, english)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed encoding issues in {file_path}")

if __name__ == "__main__":
    fix_file_encoding("trade_engine.py")
    fix_file_encoding("web_sniper.py")
    print("Encoding fixes applied successfully!")