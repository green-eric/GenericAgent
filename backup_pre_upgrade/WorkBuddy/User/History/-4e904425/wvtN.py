"""
检查 NeoData API 原始响应
"""
import json, os, requests

token_path = os.path.join(os.path.expanduser('~'), '.workbuddy', '.neodata_token')
token = open(token_path).read().strip() if os.path.exists(token_path) else ''
print(f"Token: {token[:20]}...")

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {"query": "300139.SZ 晓程科技 年报"}

resp = requests.post(
    "https://copilot.tencent.com/agenttool/v1/neodata",
    headers=headers, json=payload, timeout=30
)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Code: {data.get('code')}")
print(f"Msg: {data.get('msg','')}")
print(f"Data keys: {list(data.get('data',{}).keys()) if isinstance(data.get('data'), dict) else type(data.get('data'))}")

# 打印完整响应结构（截断）
raw = json.dumps(data, ensure_ascii=False, indent=2)
print(f"\nFull response (first 3000 chars):\n{raw[:3000]}")
