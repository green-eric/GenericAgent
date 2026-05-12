#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, re, json, requests

# 读取token
token_file = os.path.expanduser("~/.workbuddy/.neodata_token")
with open(token_file, "r", encoding="utf-8") as f:
    token = f.read().strip()

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 用代码中的查询方式
query = "300189.SZ 神农种业 最新季报"
payload = {"query": query}

resp = requests.post(url, json=payload, headers=headers, timeout=50)
data = resp.json()

inner = data.get("data", {})
api_data = inner.get("apiData", {})
recall_list = api_data.get("apiRecall", [])

print("Number of recall items: " + str(len(recall_list)))
for idx, item in enumerate(recall_list):
    content = item.get("content", "")
    item_type = item.get("type", "")
    print("\n=== Item " + str(idx) + " (type=" + item_type + ") ===")
    print("Length: " + str(len(content)))
    
    # 搜索59.18和444.78
    for line in content.split('\n'):
        if '59.18' in line:
            print("FOUND 59.18: " + line.strip())
        if '444.78' in line:
            print("FOUND 444.78: " + line.strip())
    
    # 搜索同比
    for line in content.split('\n'):
        if '同比' in line:
            print("YOY: " + line.strip())
    
    # 打印前300字符
    print("First 300 chars:")
    print(content[:300])
    print("...")
