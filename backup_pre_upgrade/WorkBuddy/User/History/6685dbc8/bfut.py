"""Test failed stocks"""
import requests
import json

with open(r'C:\Users\green\.workbuddy\.neodata_token', 'r') as f:
    token = f.read().strip()

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Test stocks that likely failed
test_stocks = [
    ("002466.SZ", "天齐锂业"),
    ("603115.SH", "海星股份"),
    ("002033.SZ", "丽江股份"),
    ("002957.SZ", "科瑞技术"),
    ("003022.SZ", "联泓新科"),
    ("600338.SH", "西藏珠峰"),
]

for ts_code, name in test_stocks:
    query = f"{ts_code} {name} 年报"
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    
    resp = requests.post(url, json={"query": query}, headers=headers, timeout=50)
    data = resp.json()
    
    d = data.get("data", {})
    print(f"  data type: {type(d).__name__}")
    
    if isinstance(d, dict):
        print(f"  data keys: {list(d.keys())}")
        
        api_data = d.get("apiData", {})
        doc_data = d.get("docData", {})
        
        if isinstance(api_data, dict):
            recalls = api_data.get("apiRecall", [])
            print(f"  apiRecall: {len(recalls) if isinstance(recalls, list) else 'N/A'} items")
            if recalls:
                for i, r in enumerate(recalls[:2]):
                    content_len = len(r.get("content", "")) if isinstance(r, dict) else 0
                    rtype = r.get("type", "?") if isinstance(r, dict) else "?"
                    print(f"    [{i}] type={rtype}, content_len={content_len}")
        
        if isinstance(doc_data, dict):
            doc_recalls = doc_data.get("docRecall", [])
            print(f"  docRecall: {len(doc_recalls) if isinstance(doc_recalls, list) else 'N/A'} items")
            if doc_recalls:
                for i, r in enumerate(doc_recalls[:1]):
                    content = r.get("content", "") or r.get("text", "") or ""
                    if isinstance(content, str):
                        print(f"    [{i}] content_len={len(content)}, preview: {content[:100]}")
    else:
        print(f"  data value: {str(d)[:200]}")
