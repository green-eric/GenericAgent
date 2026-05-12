import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

d = json.load(open('industry_map.json', 'r', encoding='utf-8'))

# 查宏和科技
for key in ['603256', '603256.SH', '603256.SZ']:
    if key in d:
        print(f"{key}: {d[key]}")
        break
else:
    print("603256 不在映射表中")

# 查 xuan.txt 中所有股票的行业
xuan_file = 'xuan.txt'
codes = []
with open(xuan_file, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            parts = line.replace('\t', ' ').split()
            if parts:
                codes.append(parts[0])

print(f"\nxuan.txt 共 {len(codes)} 只股票:")
ind_counts = {}
for c in codes:
    code_short = c.replace('.SH', '').replace('.SZ', '')
    ind = d.get(code_short, d.get(c, '未知'))
    ind_counts[ind] = ind_counts.get(ind, 0) + 1
    print(f"  {c}: {ind}")

print(f"\n行业分布:")
for ind, cnt in sorted(ind_counts.items(), key=lambda x: -x[1]):
    print(f"  {ind}: {cnt}只")
