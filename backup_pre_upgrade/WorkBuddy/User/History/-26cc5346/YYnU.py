"""
验证新优先级下各数据源的命中情况
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from annual_scorer import (
    determine_industry,
    load_industry_map,
    load_akshare_industry_map,
)

old_map = load_industry_map()
akshare_map = load_akshare_industry_map()

# 读取 xuan.txt
xuan_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xuan.txt")
codes = []
with open(xuan_file, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            parts = line.replace("\t", " ").split()
            if parts:
                codes.append(parts[0])

# 模拟各优先级的命中（use_api=False 跳过 NeoData）
print(f"{'代码':<12} {'akshare(②)':<12} {'名称推断(③)':<12} {'旧映射(⑤)':<12} {'最终结果':<12}")
print("-" * 62)

hit_akshare = 0
hit_name = 0
hit_old = 0
hit_prefix = 0

for c in codes:
    code_short = c.replace(".SH", "").replace(".SZ", "")

    # 各级命中情况
    ak = akshare_map.get(code_short, "")

    from annual_scorer import infer_industry_from_name
    name_ind = infer_industry_from_name("")  # 无名称，跳过

    old_ind = old_map.get(code_short, old_map.get(c, ""))

    # 最终（无 content, 无 API）
    final = determine_industry(c, "", "", old_map, use_api=False, akshare_map=akshare_map)

    # 统计命中来源
    if ak:
        hit_akshare += 1
    elif old_ind and final == old_ind:
        hit_old += 1
    elif final:
        hit_prefix += 1

    print(f"  {c:<10} {ak or '-':<10} {name_ind or '-':<10} {old_ind or '-':<10} {final or '-':<10}")

print(f"\n命中统计:")
print(f"  ② akshare:    {hit_akshare}/{len(codes)}")
print(f"  ⑤ 旧映射表:   {hit_old}/{len(codes)}")
print(f"  ⑥ 代码前缀:   {hit_prefix}/{len(codes)}")
