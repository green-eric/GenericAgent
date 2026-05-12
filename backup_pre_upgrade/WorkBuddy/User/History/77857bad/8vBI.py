import requests
import json
import re

# Load token
with open(r'C:\Users\green\.workbuddy\.neodata_token', 'r') as f:
    token = f.read().strip()

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Test with a stock from xuan.txt
test_stocks = [
    ("002466.SZ", "天齐锂业"),
    ("600186.SH", "莲花控股"),
]

for ts_code, name in test_stocks:
    query = f"{ts_code} {name} 年报"
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    
    resp = requests.post(url, json={"query": query}, headers=headers, timeout=50)
    data = resp.json()
    
    # Parse like the script does
    d = data.get("data", {})
    api_data = d.get("apiData", {}) if isinstance(d, dict) else {}
    recalls = api_data.get("apiRecall", []) if isinstance(api_data, dict) else []
    
    print(f"apiRecall count: {len(recalls)}")
    
    if recalls:
        for i, r in enumerate(recalls[:2]):
            content = r.get("content", "")
            print(f"\n  Recall[{i}] type={r.get('type','?')}, content len={len(content)}")
            print(f"  Content preview: {content[:300]}")
            
            # Test the parsing functions
            pattern = r"统计截止日期为([0-9]{4}(?:0331|0630|0930))的Q[123]单季报"
            matches = list(re.finditer(pattern, content))
            print(f"  Quarterly matches: {len(matches)}")
            
            annual_matches = list(re.finditer(r"统计截止日期为([0-9]{4})1231的年报", content))
            print(f"  Annual matches: {len(annual_matches)}")
    else:
        print("  No apiRecall found!")
        # Check docData
        doc_data = d.get("docData", {})
        doc_recalls = doc_data.get("docRecall", []) if isinstance(doc_data, dict) else []
        print(f"  docRecall count: {len(doc_recalls)}")
        if doc_recalls:
            for i, r in enumerate(doc_recalls[:2]):
                content = r.get("content", "") or r.get("text", "") or str(r)
                print(f"  DocRecall[{i}] preview: {content[:300]}")
