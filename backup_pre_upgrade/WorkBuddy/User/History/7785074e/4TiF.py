import requests
import json

with open(r'C:\Users\green\.workbuddy\.neodata_token', 'r') as f:
    token = f.read().strip()

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

query = "000001.SZ 平安银行 年报"
resp = requests.post(url, json={"query": query}, headers=headers, timeout=50)
data = resp.json()

# Show the structure
print("Top-level keys:", list(data.keys()))
print("'data' type:", type(data.get("data")))
print("'data' keys:", list(data["data"].keys()) if isinstance(data.get("data"), dict) else "N/A")

# Check if 'text' field exists
if isinstance(data.get("data"), dict):
    d = data["data"]
    print("\nFields in data['data']:")
    for k, v in d.items():
        if isinstance(v, str):
            print(f"  {k}: string (len={len(v)})")
        elif isinstance(v, dict):
            print(f"  {k}: dict with keys {list(v.keys())[:5]}")
        elif isinstance(v, list):
            print(f"  {k}: list (len={len(v)})")
        else:
            print(f"  {k}: {type(v).__name__} = {v}")

    # Check apiData
    api_data = d.get("apiData", {})
    print("\napiData keys:", list(api_data.keys()) if isinstance(api_data, dict) else "N/A")
    if isinstance(api_data, dict):
        for k, v in api_data.items():
            if isinstance(v, list) and len(v) > 0:
                print(f"  apiData['{k}']: list[{len(v)}], first item keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
                if isinstance(v[0], dict) and 'content' in v[0]:
                    content_preview = v[0]['content'][:200] if isinstance(v[0]['content'], str) else str(v[0]['content'])[:200]
                    print(f"    content preview: {content_preview}")
