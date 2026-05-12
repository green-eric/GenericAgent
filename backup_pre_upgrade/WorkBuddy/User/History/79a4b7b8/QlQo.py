"""模拟脚本的完整数据获取和解析流程"""
import requests
import re
import json
import os
import sys

# Load token
with open(r'C:\Users\green\.workbuddy\.neodata_token', 'r') as f:
    token = f.read().strip()

NEODATA_URL = "https://copilot.tencent.com/agenttool/v1/neodata"
API_TIMEOUT = 50

def run_neodata(query, session):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    for attempt in range(3):
        try:
            resp = session.post(NEODATA_URL, json={"query": query},
                                headers=headers, timeout=API_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            d = data.get("data", {})
            if isinstance(d, dict):
                api_data = d.get("apiData", {})
                if isinstance(api_data, dict):
                    recalls = api_data.get("apiRecall", [])
                    if isinstance(recalls, list) and recalls:
                        parts = []
                        for r in recalls:
                            if isinstance(r, dict) and r.get("content"):
                                parts.append(r["content"])
                        if parts:
                            return "\n".join(parts)
                if d.get("text"):
                    return d["text"]
            if isinstance(d, str):
                return d
            return json.dumps(data, ensure_ascii=False)
        except Exception as e:
            print(f"  API error attempt {attempt}: {e}")
    return ""

def _extract_quarterly_block(text):
    pattern = r"统计截止日期为([0-9]{4}(?:0331|0630|0930))的Q[123]单季报"
    matches = list(re.finditer(pattern, text))
    if not matches:
        pattern2 = r"统计截止日期为([0-9]{4}(?:0331|0630|0930))的(?:单?季报)"
        matches = list(re.finditer(pattern2, text))
        matches = [m for m in matches if m.group(1) != "20251231"]
    if not matches:
        return "", ""
    latest = sorted(matches, key=lambda x: x.group(1), reverse=True)[0]
    report_date = latest.group(1)
    anchor = f"统计截止日期为{report_date}的"
    start = text.find(anchor) + len(anchor)
    for suffix in ["Q1单季报", "Q2单季报", "Q3单季报", "单季报", "季报"]:
        if text[start:start+len(suffix)] == suffix:
            start += len(suffix)
            break
    next_a = text.find("统计截止日期为", start + 1)
    block = text[start:] if next_a == -1 else text[start:next_a]
    return block.strip(), report_date

def _extract_annual_block(text):
    matches = list(re.finditer(r"统计截止日期为([0-9]{4})1231的年报", text))
    if not matches:
        return ""
    last = matches[-1]
    start = text.find(last.group(0))
    if start == -1:
        return ""
    start += len(last.group(0))
    next_a = text.find("统计截止日期为", start + 1)
    return text[start:] if next_a == -1 else text[start:next_a]

def parse_num(text):
    if not text:
        return None
    m = re.search(r"([-+]?[0-9]+[.]?[0-9]*)%", text)
    if m:
        return float(m.group(1))
    m = re.search(r"([-+]?[0-9]+[.]?[0-9]*)", text)
    if m:
        return float(m.group(1))
    return None

def _extract_metric(text, keywords):
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        for kw in keywords:
            if kw in line:
                return parse_num(line)
    return None

def parse_quarterly_finance(block):
    return {
        "gross_margin": _extract_metric(block, ["销售毛利率"]),
        "net_margin": _extract_metric(block, ["销售净利率"]),
        "revenue_yoy": _extract_metric(block, ["营业收入同比增长", "营收同比增长", "营业总收入同比增长"]),
        "profit_yoy": _extract_metric(block, ["归母净利润同比增长"]),
    }

def parse_annual_finance(block):
    return {
        "roe": _extract_metric(block, ["加权净资产收益率ROE", "ROE"]),
        "debt_ratio": _extract_metric(block, ["资产负债率"]),
        "ocf_to_profit": _extract_metric(block, ["净利润现金含量"]),
        "net_profit": _extract_metric(block, ["净利润", "归母净利润"]),
        "ocf_abs": _extract_metric(block, ["经营活动产生的现金流量净额"]),
    }

# Test with one stock
test_stocks = [
    ("002466.SZ", "天齐锂业"),
    ("600186.SH", "莲花控股"),
    ("300398.SZ", "飞凯材料"),
]

session = requests.Session()
from requests.adapters import HTTPAdapter
adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=2)
session.mount("https://", adapter)
session.mount("http://", adapter)

for ts_code, name in test_stocks:
    print(f"\n{'='*60}")
    print(f"Testing: {ts_code} {name}")
    
    query = f"{ts_code} {name} 年报"
    text = run_neodata(query, session)
    
    print(f"Text length: {len(text)}")
    
    if not text:
        print("ERROR: Empty response!")
        continue
    
    annual_block = _extract_annual_block(text)
    quarterly_block, q_date = _extract_quarterly_block(text)
    
    print(f"Annual block length: {len(annual_block)}")
    print(f"Quarterly block length: {len(quarterly_block)}, date: {q_date}")
    
    annual_metrics = parse_annual_finance(annual_block) if annual_block else {}
    quarterly_metrics = parse_quarterly_finance(quarterly_block) if quarterly_block else {}
    
    print(f"Annual metrics: {annual_metrics}")
    print(f"Quarterly metrics: {quarterly_metrics}")
    
    fetch_success = bool(annual_metrics) or bool(quarterly_metrics)
    print(f"fetch_success: {fetch_success}")

session.close()
print("\nDone!")
