#!/usr/bin/env python3
"""
每日工作记忆同步脚本
将当天的 .workbuddy/memory/YYYY-MM-DD.md 同步到 IMA 笔记
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

def get_today_memory_file(workspace_root):
    """获取今日记忆文件路径"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    memory_dir = workspace_root / ".workbuddy" / "memory"
    memory_file = memory_dir / f"{today}.md"
    
    if not memory_file.exists():
        print(f"警告: 今日记忆文件不存在: {memory_file}")
        return None
    
    return memory_file

def read_memory_content(memory_file):
    """读取记忆文件内容"""
    with open(memory_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        print("警告: 记忆文件内容为空")
    
    return content

def create_ima_note(client_id, api_key, title, content):
    """创建 IMA 笔记"""
    headers = {
        'ima-openapi-clientid': client_id,
        'ima-openapi-apikey': api_key,
        'ima-openapi-ctx': 'skill_version=1.1.3',
        'Content-Type': 'application/json'
    }
    
    # 确定笔记本 ID（默认为第一个笔记本，或使用已知的笔记本）
    # 这里简单起见，不指定笔记本，让 API 使用默认笔记本
    payload = {
        "title": title,
        "content": content,
        "content_type": "markdown"
    }
    
    try:
        response = requests.post(
            CREATE_NOTE_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"IMA API 错误: {result.get('message', '未知错误')}")
        
        note_id = result.get("data", {}).get("note_id")
        if not note_id:
            raise Exception("创建笔记失败: 未返回 note_id")
        
        return note_id
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        raise Exception(f"响应解析失败: {e}")

def main():
    """主函数"""
    try:
        # 获取工作区根目录（脚本所在目录的父目录）
        workspace_root = Path(__file__).parent
        
        # 加载凭证
        client_id, api_key = load_credentials()
        print("✅ IMA 凭证加载成功")
        
        # 获取今日记忆文件
        memory_file = get_today_memory_file(workspace_root)
        if not memory_file:
            print("❌ 没有找到今日记忆文件，跳过同步")
            sys.exit(0)
        
        # 读取内容
        content = read_memory_content(memory_file)
        if not content:
            print("❌ 记忆文件内容为空，跳过同步")
            sys.exit(0)
        
        # 生成笔记标题
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        title = f"WorkBuddy 工作记忆 - {today}"
        
        # 创建 IMA 笔记
        print(f"正在同步今日工作记忆到 IMA: {title}")
        note_id = create_ima_note(client_id, api_key, title, content)
        
        print(f"✅ 同步成功！笔记 ID: {note_id}")
        print(f"📅 日期: {today}")
        print(f"📝 内容长度: {len(content)} 字符")
        
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()