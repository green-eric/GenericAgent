import requests, json, re, os, sys

# 读取token
token_file = os.path.expanduser("~/.workbuddy/.neodata_token")
with open(token_file, "r", encoding="utf-8") as f:
    token = f.read().strip()

url = "https://copilot.tencent.com/agenttool/v1/neodata"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

query = "300189.SZ 神农种业 最新季报"
payload = {"query": query}

resp = requests.post(url, json=payload, headers=headers, timeout=50)
data = resp.json()

# 获取内容
inner = data.get("data", {})
api_data = inner.get("apiData", {})
recall_list = api_data.get("apiRecall", [])

print("Number of recall items: " + str(len(recall_list)))
for idx, item in enumerate(recall_list):
    content = item.get("content", "")
    item_type = item.get("type", "")
    print("\n=== Item " + str(idx) + " (type=" + item_type + ") ===")
    
    # 搜索59.18和444.78
    found_59 = False
    found_444 = False
    for line in content.split('\n'):
        if '59.18' in line:
            print("FOUND 59.18: " + line.strip())
            found_59 = True
        if '444.78' in line:
            print("FOUND 444.78: " + line.strip())
            found_444 = True
    
    if not found_59 and not found_444:
        print("Neither 59.18 nor 444.78 found in this item")
    
    # 搜索所有百分比
    percentages = []
    for line in content.split('\n'):
        matches = re.findall(r'(\d+\.?\d*)%', line)
        if matches:
            percentages.append((line.strip(), matches))
    
    if percentages:
        print("Percentages found:")
        for line, matches in percentages[:10]:
            print("  " + str(matches) + " in: " + line[:80])
    
    # 搜索同比
    for line in content.split('\n'):
        if '同比' in line:
            print("YOY: " + line.strip())
