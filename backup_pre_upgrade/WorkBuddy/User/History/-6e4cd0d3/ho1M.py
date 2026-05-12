"""
调试：查看 API 返回内容中锚点的实际格式
"""
import json, os, re, requests

token_path = os.path.join(os.path.expanduser('~'), '.workbuddy', '.neodata_token')
token = open(token_path).read().strip() if os.path.exists(token_path) else ''
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

payload = {"query": "300139.SZ 晓程科技 年报"}
resp = requests.post(
    "https://copilot.tencent.com/agenttool/v1/neodata",
    headers=headers, json=payload, timeout=30
)
data = resp.json()
content = ''
for item in data.get('data', {}).get('apiRecall', []):
    content += item.get('content', '')

# 查找所有包含"统计截止日期"的行
lines = content.split('\n')
print(f"总字符数: {len(content)}")
print(f"总行数: {len(lines)}")
print("\n包含'统计截止日期'的行:")
for i, line in enumerate(lines):
    if '统计截止日期' in line:
        print(f"  行{i}: [{line.strip()}]")

# 也搜索"季报"
print("\n包含'季报'的行:")
for i, line in enumerate(lines):
    if '季报' in line:
        print(f"  行{i}: [{line.strip()[:100]}]")

# 搜索"年报"
print("\n包含'年报'的行 (前5):")
count = 0
for i, line in enumerate(lines):
    if '年报' in line and count < 5:
        print(f"  行{i}: [{line.strip()[:100]}]")
        count += 1
