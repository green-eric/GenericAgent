import sys
sys.path.insert(0, r'C:\Users\green\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search')
import subprocess, json

# 用代码中的查询方式
query = "300189.SZ 神农种业 最新季报"
result = subprocess.run(
    ['python', 'scripts/query.py', '--query', query],
    capture_output=True, text=True,
    cwd=r'C:\Users\green\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search'
)
data = json.loads(result.stdout)
content = data['data']['apiData']['apiRecall'][0]['content']

# 搜索59.18和444.78
import re
print("=== Searching for 59.18 ===")
for i, line in enumerate(content.split('\n')):
    if '59.18' in line:
        print("Line " + str(i) + ": " + line.strip())

print("\n=== Searching for 444.78 ===")
for i, line in enumerate(content.split('\n')):
    if '444.78' in line:
        print("Line " + str(i) + ": " + line.strip())

# 搜索所有同比增长
print("\n=== All yoy ===")
for i, line in enumerate(content.split('\n')):
    if '同比' in line:
        print("Line " + str(i) + ": " + line.strip())

# 搜索所有百分比
print("\n=== All percentages ===")
for i, line in enumerate(content.split('\n')):
    matches = re.findall(r'(\d+\.?\d*)%', line)
    if matches:
        print("Line " + str(i) + ": " + line.strip() + " -> " + str(matches))

# 打印前500字符
print("\n=== First 500 chars ===")
print(content[:500])
