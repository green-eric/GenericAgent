import requests
import json

# Load token
with open(r'C:\Users\green\.workbuddy\.neodata_token', 'r') as f:
    token = f.read().strip()

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

query = "000001.SZ 平安银行 年报"
print(f"Query: {query}")
print(f"Token (first 20 chars): {token[:20]}...")

resp = requests.post(url, json={"query": query}, headers=headers, timeout=50)
print(f"Status: {resp.status_code}")
print(f"Response (first 500 chars):")
data = resp.json()
print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
