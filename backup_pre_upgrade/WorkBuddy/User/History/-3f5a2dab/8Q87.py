"""
确认 akshare 返回的行业级别（一级 vs 二级）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

import akshare as ak

# 1. 申万一级行业列表
print("=== 申万一级行业 (sw_index_first_info) ===")
df1 = ak.sw_index_first_info()
print(f"数量: {len(df1)}")
print(f"列名: {list(df1.columns)}")
print(df1[["行业代码", "行业名称"]].to_string(index=False))

# 2. 申万二级行业列表
print("\n=== 申万二级行业 (sw_index_second_info) ===")
try:
    df2 = ak.sw_index_second_info()
    print(f"数量: {len(df2)}")
    print(f"列名: {list(df2.columns)}")
    if "行业代码" in df2.columns and "行业名称" in df2.columns:
        print(df2[["行业代码", "行业名称"]].head(20).to_string(index=False))
except Exception as e:
    print(f"失败: {e}")

# 3. 确认 index_stock_cons 用的是哪个级别
print("\n=== index_stock_cons 返回级别验证 ===")
# 用几个已知行业代码测试
test_codes = [
    ("801010", "一级-农林牧渔"),
    ("801030", "一级-基础化工"),
    ("801710", "一级-建筑材料"),
    ("801890", "一级-机械设备"),
]
for code, name in test_codes:
    try:
        df = ak.index_stock_cons(symbol=code)
        print(f"{name}({code}): {len(df)}只成分股, 列名={list(df.columns)}")
    except Exception as e:
        print(f"{name}({code}): 失败 {e}")

# 4. 检查宏和科技(603256)在哪个一级行业中
print("\n=== 宏和科技(603256)行业归属验证 ===")
for _, row in df1.iterrows():
    ind_code = str(row["行业代码"]).split(".")[0]
    ind_name = row["行业名称"]
    try:
        df = ak.index_stock_cons(symbol=ind_code)
        col = "品种代码"
        if "603256" in df[col].astype(str).values:
            print(f"  ✅ 603256 在 【{ind_name}({ind_code})】 中")
    except:
        pass

# 5. 检查是否有二级行业代码（通常801xxx是一级，802xxx是二级）
print("\n=== 申万行业代码规则 ===")
print("一级行业代码: 801xxx (如 801010=农林牧渔)")
print("二级行业代码: 802xxx (如 802010=种植业)")
