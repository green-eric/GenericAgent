"""
测试 akshare 批量获取申万行业分类的可行性
重点：性能 + 覆盖度 + 新旧对比
"""
import sys, time, json, os
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

print(f"xuan.txt 共 {len(codes)} 只股票")

# 全量获取申万一级行业成分股
print("\n--- 全量获取申万一级行业成分股 ---")
t0 = time.time()
industry_map_new = {}

df_info = ak.sw_index_first_info()
print(f"申万一级行业数: {len(df_info)}, 列表耗时: {time.time()-t0:.2f}s")

for _, row in df_info.iterrows():
    ind_code = row["行业代码"].split(".")[0]
    ind_name = row["行业名称"]
    t1 = time.time()
    try:
        df_cons = ak.index_stock_cons(symbol=ind_code)
        code_col = "品种代码"
        for _, stock in df_cons.iterrows():
            code = str(stock[code_col])
            if code not in industry_map_new:
                industry_map_new[code] = ind_name
        print(f"  {ind_name}({ind_code}): {len(df_cons)}只, {time.time()-t1:.2f}s")
    except Exception as e:
        print(f"  {ind_name}({ind_code}): 失败 {e}")

elapsed = time.time() - t0
print(f"\n总耗时: {elapsed:.2f}s")
print(f"覆盖股票数: {len(industry_map_new)}")

# xuan.txt 覆盖度
covered = sum(1 for c in codes if c in industry_map_new)
missing = [c for c in codes if c not in industry_map_new]
print(f"\nxuan.txt 覆盖度: {covered}/{len(codes)} = {covered/len(codes)*100:.1f}%")
if missing:
    print(f"未覆盖({len(missing)}只): {missing}")

# 宏和科技
print(f"\n宏和科技(603256)行业: {industry_map_new.get('603256', '未找到')}")

# 新旧对比
old_map_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "industry_map.json")
with open(old_map_file, encoding="utf-8") as f:
    old_map = json.load(f)

print(f"\n--- 新旧映射对比 ---")
diff_count = 0
diff_samples = []
for c in codes:
    old_ind = old_map.get(c, old_map.get(f"{c}.SH", old_map.get(f"{c}.SZ", None)))
    new_ind = industry_map_new.get(c, None)
    if old_ind and new_ind and old_ind != new_ind:
        diff_count += 1
        diff_samples.append(f"  {c}: 旧={old_ind} → 新={new_ind}")
    elif old_ind is None and new_ind:
        print(f"  {c}: 旧=无 → 新={new_ind} (新增)")
    elif old_ind and new_ind is None:
        print(f"  {c}: 旧={old_ind} → 新=无 (丢失)")

print(f"\n行业变更: {diff_count}/{len(codes)} 只")
for s in diff_samples:
    print(s)
