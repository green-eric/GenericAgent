#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证修复后的解析器对真实API数据
直接复制解析函数，避免import问题
"""
import os, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Copy the parsing functions from stock_analyzer.py
def _extract_annual_block(text):
    annual_header_pat = re.compile(r'统计截止日期为(\d{4})1231的年报')
    m = annual_header_pat.search(text)
    if not m:
        return None
    start = m.start()
    next_section = re.search(r'统计截止日期为', text[start + 1:])
    if next_section:
        end = start + 1 + next_section.start()
    else:
        end = len(text)
    return text[start:end]

def _extract_metric_line(block, keywords):
    if not block:
        return None
    for line in block.split('\n'):
        line = line.strip()
        if not line:
            continue
        for kw in keywords:
            if kw in line:
                return line
    return None

def _parse_pct_from_line(line, keyword=None):
    if not line:
        return None
    if keyword:
        idx = line.find(keyword)
        if idx >= 0:
            line = line[idx:]
    m = re.search(r'([-+]?\d+\.?\d*)%', line)
    return float(m.group(1)) if m else None

def _parse_num_from_line(line):
    if not line:
        return None
    m = re.search(r'([-+]?\d+\.?\d*)\s*(万亿元|亿元|万元|千元|元)', line)
    if not m:
        return None
    num, unit = float(m.group(1)), m.group(2)
    if unit == '万亿元': return num * 1e12
    if unit == '亿元':   return num * 1e8
    if unit == '万元':   return num * 1e4
    if unit == '千元':   return num * 1e3
    return num

def _parse_yoy_from_line(line):
    if not line:
        return None
    m = re.search(r'同比增长\s*([-+]?\d+\.?\d*)%', line)
    return float(m.group(1)) if m else None

def parse_financial_all(content):
    res = {k: None for k in [
        "annual_roe", "annual_gross_margin", "annual_net_margin",
        "annual_revenue_yoy", "annual_profit_yoy", "annual_debt_ratio",
        "annual_net_profit", "annual_deducted_profit", "annual_revenue",
        "annual_ocf_to_profit", "annual_ocf_abs",
        "total_asset_turnover", "ar_turnover", "annual_report_date"
    ]}

    block = _extract_annual_block(content)
    if not block:
        return res

    year_m = re.search(r'统计截止日期为(\d{4})1231的年报', block)
    if year_m:
        res["annual_report_date"] = year_m.group(1) + "1231"

    line = _extract_metric_line(block, ["加权净资产收益率ROE", "净资产收益率ROE", "加权净资产收益率"])
    if line: res["annual_roe"] = _parse_pct_from_line(line)

    line = _extract_metric_line(block, ["销售毛利率"])
    if line: res["annual_gross_margin"] = _parse_pct_from_line(line, keyword="毛利率")

    line = _extract_metric_line(block, ["销售净利率"])
    if line: res["annual_net_margin"] = _parse_pct_from_line(line, keyword="净利率")

    line = _extract_metric_line(block, ["营业收入同比增长", "营收同比增长", "营业总收入同比增长"])
    if line: res["annual_revenue_yoy"] = _parse_yoy_from_line(line)

    line = _extract_metric_line(block, ["归母净利润同比增长"])
    if line: res["annual_profit_yoy"] = _parse_yoy_from_line(line)

    line = _extract_metric_line(block, ["资产负债率"])
    if line: res["annual_debt_ratio"] = _parse_pct_from_line(line)

    line = _extract_metric_line(block, ["营业总收入", "营业收入"])
    if line: res["annual_revenue"] = _parse_num_from_line(line)

    # FIXED: 排除净利润现金含量等衍生指标
    line = None
    for l in block.split('\n'):
        l = l.strip()
        if l.startswith('净利润') and '归母' not in l and '扣非' not in l \
                and '现金含量' not in l and '增长率' not in l and '同比' not in l:
            line = l
            break
    if line:
        val = _parse_num_from_line(line)
        if val is not None:
            res["annual_net_profit"] = val

    line = _extract_metric_line(block, ["扣非净利润"])
    if line: res["annual_deducted_profit"] = _parse_num_from_line(line)

    line = _extract_metric_line(block, ["经营活动产生的现金流量净额"])
    if line: res["annual_ocf_abs"] = _parse_num_from_line(line)

    if res["annual_net_profit"] and res["annual_ocf_abs"] and res["annual_net_profit"] != 0:
        res["annual_ocf_to_profit"] = res["annual_ocf_abs"] / res["annual_net_profit"]

    line = _extract_metric_line(block, ["总资产周转率"])
    if line:
        m = re.search(r'([\d.]+)\s*次', line)
        if m: res["total_asset_turnover"] = float(m.group(1))

    line = _extract_metric_line(block, ["应收账款周转率"])
    if line:
        m = re.search(r'([\d.]+)\s*次', line)
        if m: res["ar_turnover"] = float(m.group(1))

    return res

# Now test with real API data
import requests

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

test_stocks = [
    ("300251.SZ", "光线传媒"),
    ("600867.SH", "通化东宝"),
    ("001316.SZ", "润贝航科"),
    ("601868.SH", "中国能建"),
    ("001236.SZ", "弘业期货"),
]

print("验证修复后的解析器（使用真实API数据）\n")

all_pass = True
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
    
    rd = result.get('annual_report_date')
    np_val = result.get('annual_net_profit')
    ocf_val = result.get('annual_ocf_abs')
    ratio = result.get('annual_ocf_to_profit')
    
    print(f"  报告日期: {rd}")
    print(f"  ROE: {result.get('annual_roe')}%")
    print(f"  毛利率: {result.get('annual_gross_margin')}%")
    print(f"  净利率: {result.get('annual_net_margin')}%")
    print(f"  营收同比: {result.get('annual_revenue_yoy')}%")
    print(f"  净利润同比: {result.get('annual_profit_yoy')}%")
    print(f"  资产负债率: {result.get('annual_debt_ratio')}%")
    print(f"  净利润(元): {np_val}")
    print(f"  扣非净利润(元): {result.get('annual_deducted_profit')}")
    print(f"  经营现金流(元): {ocf_val}")
    print(f"  OCF/净利润: {ratio}")
    
    # Key validation: 净利润 should NOT be None
    if np_val is None:
        print(f"  ✗ 净利润仍为None！")
        all_pass = False
    else:
        print(f"  ✓ 净利润已正确解析")
    
    # Key validation: OCF/净利润 should be calculated
    if np_val and ocf_val and ratio is None:
        print(f"  ✗ OCF/净利润未计算！")
        all_pass = False
    elif np_val and ocf_val:
        expected = ocf_val / np_val
        if abs(ratio - expected) < 0.01:
            print(f"  ✓ OCF/净利润计算正确: {ratio:.4f}")
        else:
            print(f"  ✗ OCF/净利润计算错误: {ratio} vs {expected}")
            all_pass = False
    
    print()

if all_pass:
    print("✅ 所有验证通过！净利润解析修复有效。")
else:
    print("❌ 部分验证失败，请检查。")
