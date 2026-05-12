#!/usr/bin/env python3
"""
每日工作记忆同步脚本
将当天所有工作区的 .workbuddy/memory/YYYY-MM-DD.md 合并同步到 IMA 笔记
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

# WorkBuddy 工作区根目录
WORKBUDDY_ROOT = Path.home() / "WorkBuddy"

# IMA API 端点
IMA_BASE_URL = "https://ima.qq.com/openapi"
IMPORT_DOC_URL = f"{IMA_BASE_URL}/note/v1/import_doc"


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


def find_today_memory_files(target_date: str):
    """
    自动扫描所有 WorkBuddy 工作区，收集指定日期的记忆文件
    返回 list of (workspace_name, file_path, content)
    """
    results = []

    if not WORKBUDDY_ROOT.exists():
        print(f"警告: WorkBuddy 根目录不存在: {WORKBUDDY_ROOT}")
        return results

    for workspace_dir in sorted(WORKBUDDY_ROOT.iterdir()):
        if not workspace_dir.is_dir():
            continue

        memory_file = workspace_dir / ".workbuddy" / "memory" / f"{target_date}.md"
        if not memory_file.exists():
            continue

        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if content:
                results.append((workspace_dir.name, memory_file, content))
                print(f"  [找到] {workspace_dir.name}: {memory_file.name} ({len(content)} 字符)")
            else:
                print(f"  [跳过] {workspace_dir.name}: 文件为空")
        except Exception as e:
            print(f"  [错误] 读取 {memory_file} 失败: {e}")

    return results


def create_ima_note(client_id, api_key, title, content):
    """创建 IMA 笔记"""
    headers = {
        'ima-openapi-clientid': client_id,
        'ima-openapi-apikey': api_key,
        'ima-openapi-ctx': 'skill_version=1.1.3',
        'Content-Type': 'application/json'
    }

    full_content = f"# {title}\n\n{content}"

    payload = {
        "content_format": 1,
        "content": full_content
    }

    try:
        response = requests.post(
            IMPORT_DOC_URL,
            headers=headers,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        if result.get("code") != 0:
            raise Exception(f"IMA API 错误: {result.get('message', '未知错误')} (code={result.get('code')})")

        note_id = result.get("data", {}).get("note_id") or result.get("data", {}).get("doc_id")
        if not note_id:
            raise Exception(f"创建笔记失败: 未返回 note_id 或 doc_id，响应: {result}")

        return note_id

    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求失败: {e}")
    except json.JSONDecodeError as e:
        raise Exception(f"响应解析失败: {e}")


def main():
    """主函数"""
    # 支持命令行参数指定日期，默认今天
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        print(f"[模式] 指定日期同步: {target_date}")
    else:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")
        print(f"[模式] 今日同步: {target_date}")

    try:
        # 加载凭证
        client_id, api_key = load_credentials()
        print("[OK] IMA 凭证加载成功")

        # 扫描所有工作区的今日记忆文件
        print(f"\n扫描工作区记忆文件 ({WORKBUDDY_ROOT})...")
        memory_entries = find_today_memory_files(target_date)

        if not memory_entries:
            print(f"\n[跳过] 未找到 {target_date} 的记忆文件，无需同步")
            sys.exit(0)

        print(f"\n共找到 {len(memory_entries)} 个工作区的记忆文件")

        # 合并所有工作区内容
        combined_parts = []
        for workspace_name, file_path, content in memory_entries:
            combined_parts.append(f"## 工作区: {workspace_name}\n\n{content}")

        combined_content = "\n\n---\n\n".join(combined_parts)
        title = f"WorkBuddy 工作记忆 - {target_date}"

        # 创建 IMA 笔记
        print(f"\n正在同步到 IMA: {title}")
        note_id = create_ima_note(client_id, api_key, title, combined_content)

        print(f"\n[OK] 同步成功！")
        print(f"  笔记 ID: {note_id}")
        print(f"  日期: {target_date}")
        print(f"  工作区数量: {len(memory_entries)}")
        print(f"  总内容长度: {len(combined_content)} 字符")

    except FileNotFoundError as e:
        print(f"[错误] 配置文件缺失: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[错误] 同步失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
