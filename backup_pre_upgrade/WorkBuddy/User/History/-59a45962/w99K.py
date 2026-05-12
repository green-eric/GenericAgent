import requests
import re

# Load token
with open(r'C:\Users\green\.workbuddy\.neodata_token', 'r') as f:
    token = f.read().strip()

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def run_neodata(query, token):
    for attempt in range(3):
        try:
            resp = requests.post(url, json={"query": query}, headers=headers, timeout=50)
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
            print(f"  Error attempt {attempt}: {e}")
    return ""

import json

# Test single stock
ts_code = "002466.SZ"
name = "天齐锂业"
query = f"{ts_code} {name} 年报"

print(f"Query: {query}")
text = run_neodata(query, token)
print(f"Text length: {len(text)}")
print(f"Text preview:\n{text[:500]}")

# Test parsing
pattern = r"统计截止日期为([0-9]{4}(?:0331|0630|0930))的Q[123]单季报"
matches = list(re.finditer(pattern, text))
print(f"\nQuarterly matches: {len(matches)}")

annual_pattern = r"统计截止日期为([0-9]{4})1231的年报"
annual_matches = list(re.finditer(annual_pattern, text))
print(f"Annual matches: {len(annual_matches)}")
