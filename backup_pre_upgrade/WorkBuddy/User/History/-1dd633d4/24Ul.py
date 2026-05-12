"""Debug: check parsing for a successful stock"""
import requests
import re

with open(r'C:\Users\green\.workbuddy\.neodata_token', 'r') as f:
    token = f.read().strip()

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Test with 鼎泰高科 (top scorer)
ts_code = "301377.SZ"
name = "鼎泰高科"
query = f"{ts_code} {name} 年报"

resp = requests.post(url, json={"query": query}, headers=headers, timeout=50)
data = resp.json()

d = data.get("data") or {}
api_data = d.get("apiData", {})
recalls = api_data.get("apiRecall", [])

full_text = "\n".join(r.get("content", "") for r in recalls if isinstance(r, dict))

# Extract annual block
annual_matches = list(re.finditer(r"统计截止日期为([0-9]{4})1231的年报", full_text))
print(f"Annual matches: {len(annual_matches)}")

if annual_matches:
    last = annual_matches[-1]
    start = full_text.find(last.group(0))
    start += len(last.group(0))
    next_a = full_text.find("统计截止日期为", start + 1)
    annual_block = full_text[start:] if next_a == -1 else full_text[start:next_a]
    
    print(f"\nAnnual block ({len(annual_block)} chars):")
    print(annual_block[:1500])
    
    # Check for key metrics
    print("\n--- Key metric search ---")
    for kw in ["加权净资产收益率ROE", "ROE", "资产负债率", "净利润现金含量", "经营活动产生的现金流量净额", "归母净利润"]:
        found = False
        for line in annual_block.split("\n"):
            if kw in line:
                print(f"  Found '{kw}': {line.strip()[:100]}")
                found = True
                break
        if not found:
            print(f"  NOT FOUND: '{kw}'")

# Extract quarterly block
q_matches = list(re.finditer(r"统计截止日期为([0-9]{4}(?:0331|0630|0930))的Q[123]单季报", full_text))
print(f"\nQuarterly matches: {len(q_matches)}")

if q_matches:
    latest = sorted(q_matches, key=lambda x: x.group(1), reverse=True)[0]
    q_date = latest.group(1)
    anchor = f"统计截止日期为{q_date}的"
    start = full_text.find(anchor) + len(anchor)
    for suffix in ["Q1单季报", "Q2单季报", "Q3单季报", "单季报", "季报"]:
        if full_text[start:start+len(suffix)] == suffix:
            start += len(suffix)
            break
    next_a = full_text.find("统计截止日期为", start + 1)
    q_block = full_text[start:] if next_a == -1 else full_text[start:next_a]
    
    print(f"\nQuarterly block ({len(q_block)} chars, date={q_date}):")
    print(q_block[:1000])
    
    print("\n--- Key metric search ---")
    for kw in ["销售毛利率", "销售净利率", "营业收入同比增长", "归母净利润同比增长"]:
        found = False
        for line in q_block.split("\n"):
            if kw in line:
                print(f"  Found '{kw}': {line.strip()[:100]}")
                found = True
                break
        if not found:
            print(f"  NOT FOUND: '{kw}'")
