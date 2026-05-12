"""
基于已有结果分析 + 新旧对比（不重复获取全量数据）
"""
import sys, json, os
import akshare as ak

xuan_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xuan.txt")

codes = []
with open(xuan_file, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            parts = line.replace("\t", " ").split()
            if parts:
                code = parts[0].replace(".SH", "").replace(".SZ", "")
                codes.append(code)

print(f"xuan.txt 共 {len(codes)} 只股票: {codes}")

# 只获取需要的几个行业（而非全量31个）
# 先查 xuan.txt 中各股票当前映射表里的行业
old_map_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "industry_map.json")
with open(old_map_file, encoding="utf-8") as f:
    old_map = json.load(f)

# 获取旧映射中涉及的行业代码
old_industries = set()
for c in codes:
    ind = old_map.get(c, old_map.get(f"{c}.SH", old_map.get(f"{c}.SZ", None)))
    if ind:
        old_industries.add(ind)

print(f"\n旧映射涉及行业: {old_industries}")

# 获取申万行业代码映射
print("\n--- 申万一级行业代码 ---")
df_info = ak.sw_index_first_info()
sw_code_map = {}  # industry_name -> sw_code
for _, row in df_info.iterrows():
    code = row["行业代码"].split(".")[0]
    name = row["行业名称"]
    sw_code_map[name] = code
    print(f"  {name}: {code}")

# 只获取旧映射中涉及的行业 + 几个重点行业
target_industries = old_industries.copy()
target_industries.update(["建筑材料", "电子", "机械设备", "基础化工", "电力设备"])

print(f"\n--- 获取目标行业成分股 ---")
industry_map_new = {}
for ind_name in target_industries:
    if ind_name in sw_code_map:
        code = sw_code_map[ind_name]
        try:
            df_cons = ak.index_stock_cons(symbol=code)
            col = "品种代码"
            for _, stock in df_cons.iterrows():
                sc = str(stock[col])
                if sc not in industry_map_new:
                    industry_map_new[sc] = ind_name
            print(f"  {ind_name}({code}): {len(df_cons)}只")
        except Exception as e:
            print(f"  {ind_name}({code}): 失败 {e}")

# 覆盖度
covered = sum(1 for c in codes if c in industry_map_new)
missing = [c for c in codes if c not in industry_map_new]
print(f"\n覆盖度: {covered}/{len(codes)} = {covered/len(codes)*100:.1f}%")
if missing:
    print(f"未覆盖: {missing}")

# 新旧对比
print(f"\n--- 新旧行业对比 ---")
for c in codes:
    old_ind = old_map.get(c, old_map.get(f"{c}.SH", old_map.get(f"{c}.SZ", "无")))
    new_ind = industry_map_new.get(c, "无")
    mark = "⚠️" if old_ind != new_ind else "✅"
    print(f"  {mark} {c}: {old_ind} → {new_ind}")

# 特别检查宏和科技
print(f"\n宏和科技(603256):")
print(f"  旧映射: {old_map.get('603256', old_map.get('603256.SH', '无'))}")
print(f"  新映射: {industry_map_new.get('603256', '无')}")
print(f"  NeoData: 建筑材料(玻璃玻纤)")
