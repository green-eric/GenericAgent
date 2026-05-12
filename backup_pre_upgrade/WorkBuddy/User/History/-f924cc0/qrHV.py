"""
快速验证：用 akshare 查几只重点股票的行业
"""
import sys, json, os
import akshare as ak

# 申万行业代码
sw_codes = {
    "农林牧渔": "801010", "基础化工": "801030", "钢铁": "801040",
    "有色金属": "801050", "电子": "801080", "家用电器": "801090",
    "食品饮料": "801120", "纺织服饰": "801130", "轻工制造": "801140",
    "医药生物": "801150", "公用事业": "801160", "交通运输": "801170",
    "房地产": "801180", "商贸零售": "801200", "社会服务": "801210",
    "机械设备": "801890", "电力设备": "801030", "汽车": "801730",
    "国防军工": "801740", "计算机": "801750", "传媒": "801760",
    "通信": "801770", "银行": "801100", "非银金融": "801790",
    "建筑材料": "801710", "建筑装饰": "801720", "煤炭": "801060",
    "石油石化": "801070", "环保": "801190",
}

# 测试股票：宏和科技 + 旧映射中可能有问题的
test_stocks = [
    ("603256", "宏和科技"),
    ("002466", "天齐锂业"),
    ("300398", "飞凯材料"),
    ("601677", "明泰铝业"),
    ("002281", "光迅科技"),
]

print("--- akshare 申万行业查询 ---")
for code, name in test_stocks:
    found = False
    for ind_name, ind_code in sw_codes.items():
        try:
            df = ak.index_stock_cons(symbol=ind_code)
            col = "品种代码"
            if code in df[col].astype(str).values:
                print(f"  {name}({code}): {ind_name}")
                found = True
                break
        except:
            continue
    if not found:
        print(f"  {name}({code}): 未找到")

# 新旧映射对比
print("\n--- 新旧映射对比(部分) ---")
old_map_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "industry_map.json")
with open(old_map_file, encoding="utf-8") as f:
    old_map = json.load(f)

for code, name in test_stocks:
    old_ind = old_map.get(code, old_map.get(f"{code}.SH", old_map.get(f"{code}.SZ", "无")))
    print(f"  {name}({code}): 旧映射={old_ind}")
