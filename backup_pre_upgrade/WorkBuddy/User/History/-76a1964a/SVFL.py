#!/usr/bin/env python3
"""
立即同步测试脚本
"""

import os
import json
import sys
import datetime
import requests
from pathlib import Path

# 配置路径
CONFIG_DIR = Path.home() / ".config" / "ima"
CLIENT_ID_FILE = CONFIG_DIR / "client_id"
API_KEY_FILE = CONFIG_DIR / "api_key"

# IMA API 端点
IMA_BASE_URL = "https://ima.qq.com/openapi"
CREATE_NOTE_URL = f"{IMA_BASE_URL}/note/v1/create_note"

def load_credentials():
    """加载 IMA API 凭证"""
    if not CLIENT_ID_FILE.exists():
        raise FileNotFoundError(f"Client ID 文件不存在: {CLIENT_ID_FILE}")
    if not API_KEY_FILE.exists():
        raise FileNotFoundError(f"API Key 文件不存在: {API_KEY_FILE}")
    
    with open(CLIENT_ID_FILE, 'r', encoding='utf-8') as f:
        client_id = f.read().strip()
    
    with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
        api_key = f.read().strip()
    
    return client_id, api_key

def test_api_connection(client_id, api_key):
    """测试 IMA API 连接"""
    headers = {
        'ima-openapi-clientid': client_id,
        'ima-openapi-apikey': api_key,
        'ima-openapi-ctx': 'skill_version=1.1.3',
        'Content-Type': 'application/json'
    }
    
    # 测试列出笔记本
    list_url = f"{IMA_BASE_URL}/note/v1/list_notebook"
    payload = {"cursor": "0", "limit": 10}
    
    try:
        response = requests.post(list_url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"API 错误: {result.get('message', '未知错误')}")
        
        notebooks = result.get("data", {}).get("notebooks", [])
        print(f"连接成功! 发现 {len(notebooks)} 个笔记本:")
        for nb in notebooks:
            print(f"  - {nb.get('name')} (ID: {nb.get('notebook_id')})")
        
        return True
        
    except Exception as e:
        print(f"连接测试失败: {e}")
        return False

def sync_today_memory(client_id, api_key):
    """同步今日工作记忆"""
    workspace_root = Path(__file__).parent
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    memory_file = workspace_root / ".workbuddy" / "memory" / f"{today}.md"
    
    if not memory_file.exists():
        print(f"今日记忆文件不存在: {memory_file}")
        return None
    
    with open(memory_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        print("记忆文件内容为空")
        return None
    
    title = f"WorkBuddy 工作记忆 - {today}"
    
    headers = {
        'ima-openapi-clientid': client_id,
        'ima-openapi-apikey': api_key,
        'ima-openapi-ctx': 'skill_version=1.1.3',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "title": title,
        "content": content,
        "content_type": "markdown"
    }
    
    try:
        response = requests.post(CREATE_NOTE_URL, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"创建笔记失败: {result.get('message', '未知错误')}")
        
        note_id = result.get("data", {}).get("note_id")
        print(f"同步成功! 笔记ID: {note_id}")
        print(f"标题: {title}")
        print(f"内容长度: {len(content)} 字符")
        
        return note_id
        
    except Exception as e:
        print(f"同步失败: {e}")
        return None

def main():
    print("=== IMA微信小程序同步测试 ===")
    print(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 加载凭证
        client_id, api_key = load_credentials()
        print("1. 凭证加载: 成功")
        
        # 测试连接
        print("2. API连接测试...")
        if not test_api_connection(client_id, api_key):
            return
        
        # 同步今日记忆
        print("3. 同步今日工作记忆...")
        note_id = sync_today_memory(client_id, api_key)
        
        if note_id:
            print()
            print("=== 同步完成 ===")
            print("您可以在微信IMA小程序中查看同步的内容:")
            print("1. 打开微信，搜索'IMA小程序'")
            print("2. 使用相同账户登录")
            print("3. 在'我的笔记'中查找标题为 'WorkBuddy 工作记忆 - 2026-04-18' 的笔记")
            print()
            print("注意: 如果已存在相同标题的笔记，可能会创建新笔记")
        else:
            print("同步未完成")
            
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()