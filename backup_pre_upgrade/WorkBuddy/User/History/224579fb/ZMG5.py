#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Replicate the token reading and API call
_ND_TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".workbuddy", ".neodata_token")
_ND_ENDPOINT = "https://copilot.tencent.com/agenttool/v1/neodata"

def read_token():
    try:
        with open(_ND_TOKEN_FILE, 'r') as f:
            t = f.read().strip()
            if t: return t
    except: pass
    return ""

import requests

token = read_token()
if not token:
    print("No token found")
    sys.exit(1)

headers = {"Content-Type":"application/json", "Authorization":f"Bearer {token}"}

# Query for a stock that has null annual_net_profit: 光线传媒 300251
# Also query one that works: let's try a few
test_stocks = [
    ("300251.SZ", "光线传媒"),
    ("600867.SH", "通化东宝"),
]

for ts_code, name in test_stocks:
    print(f"\n{'='*60}")
    print(f"Querying: {name} ({ts_code})")
    print(f"{'='*60}")
    
    query = f"{ts_code} {name} 年报"
    payload = {"query":query, "channel":"neodata", "sub_channel":"workbuddy", "data_type":"api"}
    
    try:
        resp = requests.post(_ND_ENDPOINT, headers=headers, json=payload, timeout=50)
        data = resp.json()
        
        if data.get("code") != "200":
            print(f"API error: {data}")
            continue
        
        recalls = data.get("data", {}).get("apiData", {}).get("apiRecall", [])
        
        # Find the annual report block
        full_text = "\n".join(r.get("content", "") for r in recalls)
        
        # Find annual block
        annual_header_pat = re.compile(r'统计截止日期为(\d{4})1231的年报')
        m = annual_header_pat.search(full_text)
        
        if m:
            year = m.group(1)
            start = m.start()
            next_section = re.search(r'统计截止日期为', full_text[start + 1:])
            if next_section:
                end = start + 1 + next_section.start()
            else:
                end = len(full_text)
            block = full_text[start:end]
            
            print(f"\n--- Annual block (year={year}) ---")
            # Print lines containing profit-related keywords
            for line in block.split('\n'):
                line = line.strip()
                if any(kw in line for kw in ['净利润', '利润', '净收益']):
                    print(f"  >> {line}")
        else:
            print("No annual block found!")
            # Print first 500 chars
            print(f"First 500 chars of response:")
            print(full_text[:500])
    
    except Exception as e:
        print(f"Error: {e}")
