#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import os
import time

token_file = os.path.expanduser("~/.workbuddy/.neodata_token")
with open(token_file, "r", encoding="utf-8") as f:
    token = f.read().strip()

URL = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def query(query_str):
    payload = {"query": query_str}
    for attempt in range(3):
        try:
            resp = requests.post(URL, json=payload, headers=headers, timeout=50)
            data = resp.json()
            if data.get("code") == "200":
                inner = data.get("data", {})
                return inner.get("content", "")
            print(f"  [尝试{attempt+1}] {data.get('msg', '未知')}")
            time.sleep(3)
        except Exception as e:
            print(f"  [尝试{attempt+1}] 异常: {e}")
            time.sleep(3)
    return None

# 验证2只股票
stocks = [
    ("603350.SH", "安乃达"),
    ("000852.SZ", "石化机械"),
]

for ts_code, name in stocks:
    print(f"\n{'='*60}")
    print(f"验证: {ts_code} {name}")
    print(f"{'='*60}")
    
    content = query(f"{ts_code} {name} 2024年报")
    
    if content:
        for line in content.split("\n"):
            line = line.strip()
            if any(kw in line for kw in ["营业收入", "归母净利润", "毛利率", "净利率", "ROE", "净资产收益率", "资产负债率", "经营活动现金流", "统计截止日期"]):
                print(f"  {line}")
    else:
        print("  查询失败")
    
    time.sleep(2)
