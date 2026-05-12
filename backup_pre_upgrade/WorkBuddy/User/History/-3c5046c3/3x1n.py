#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证修复后的解析器对真实API数据的处理
"""
import os, re, json, sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Import the fixed parser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stock_analyzer import parse_financial_all

_ND_TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".workbuddy", ".neodata_token")
_ND_ENDPOINT = "https://copilot.tencent.com/agenttool/v1/neodata"

def read_token():
    try:
        with open(_ND_TOKEN_FILE, 'r') as f:
            t = f.read().strip()
            if t: return t
    except: pass
    return ""

token = read_token()
headers = {"Content-Type":"application/json", "Authorization":f"Bearer {token}"}

# Test with 3 stocks that had null net_profit
test_stocks = [
    ("300251.SZ", "光线传媒"),
    ("600867.SH", "通化东宝"),
    ("001316.SZ", "润贝航科"),
    ("601868.SH", "中国能建"),
    ("001236.SZ", "弘业期货"),
]

print("验证修复后的解析器\n")

for ts_code, name in test_stocks:
    print(f"{'='*50}")
    print(f"{name} ({ts_code})")
    print(f"{'='*50}")
    
    query = f"{ts_code} {name} 年报"
    payload = {"query":query, "channel":"neodata", "sub_channel":"workbuddy", "data_type":"api"}
    
    resp = requests.post(_ND_ENDPOINT, headers=headers, json=payload, timeout=50)
    data = resp.json()
    recalls = data.get("data", {}).get("apiData", {}).get("apiRecall", [])
    full_text = "\n".join(r.get("content", "") for r in recalls)
    
    result = parse_financial_all(full_text)
    
    print(f"  报告日期: {result.get('annual_report_date')}")
    print(f"  ROE: {result.get('annual_roe')}%")
    print(f"  毛利率: {result.get('annual_gross_margin')}%")
    print(f"  净利率: {result.get('annual_net_margin')}%")
    print(f"  营收同比: {result.get('annual_revenue_yoy')}%")
    print(f"  净利润同比: {result.get('annual_profit_yoy')}%")
    print(f"  资产负债率: {result.get('annual_debt_ratio')}%")
    print(f"  净利润(元): {result.get('annual_net_profit')}")
    print(f"  扣非净利润(元): {result.get('annual_deducted_profit')}")
    print(f"  经营现金流(元): {result.get('annual_ocf_abs')}")
    print(f"  OCF/净利润: {result.get('annual_ocf_to_profit')}")
    print(f"  总资产周转率: {result.get('total_asset_turnover')}")
    print(f"  应收账款周转率: {result.get('ar_turnover')}")
    
    # Verify OCF/净利润 calculation
    np_val = result.get('annual_net_profit')
    ocf_val = result.get('annual_ocf_abs')
    ratio = result.get('annual_ocf_to_profit')
    if np_val and ocf_val and np_val != 0:
        expected_ratio = ocf_val / np_val
        if ratio is not None:
            match = abs(ratio - expected_ratio) < 0.01
            print(f"  OCF/净利润验算: {ocf_val}/{np_val}={expected_ratio:.4f} vs {ratio:.4f} {'✓' if match else '✗'}")
        else:
            print(f"  OCF/净利润验算: 应为 {expected_ratio:.4f} 但得到 None ✗")
    print()
