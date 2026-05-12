"""
测试 akshare 申万行业分类接口的可用性
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("测试 akshare 申万行业分类接口")
print("=" * 60)

# 1. 检查 akshare 是否安装
try:
    import akshare as ak
    print(f"\n✅ akshare 已安装, 版本: {ak.__version__}")
except ImportError:
    print("\n❌ akshare 未安装")
    print("安装命令: pip install akshare")
    sys.exit(1)

# 2. 测试申万一级行业列表接口
print("\n📋 测试1: 获取申万一级行业列表")
try:
    df = ak.sw_index_first_info()
    print(f"  成功! 获取到 {len(df)} 个申万一级行业")
    print(f"  列名: {list(df.columns)}")
    print(f"  前5行:")
    print(df.head().to_string(index=False))
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 3. 测试获取某行业的成分股（以机械设备为例）
print("\n📋 测试2: 获取申万一级行业成分股（801890 机械设备）")
try:
    df = ak.index_stock_cons(symbol="801890")
    print(f"  成功! 获取到 {len(df)} 只成分股")
    print(f"  列名: {list(df.columns)}")
    print(f"  前5行:")
    print(df.head().to_string(index=False))
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 4. 测试获取单只股票的申万行业（宏和科技 603256）
print("\n📋 测试3: 获取单只股票申万行业分类（宏和科技 603256）")
try:
    # 方法A: 通过行业成分股反查
    df = ak.index_stock_cons(symbol="801890")
    code_col = "品种代码" if "品种代码" in df.columns else df.columns[0]
    if "603256" in df[code_col].astype(str).values:
        row = df[df[code_col].astype(str) == "603256"]
        name_col = "品种名称" if "品种名称" in df.columns else df.columns[1]
        print(f"  ✅ 宏和科技在申万一级行业【机械设备】中")
        print(f"  信息: {row.iloc[0].to_dict()}")
    else:
        print(f"  ⚠️ 宏和科技不在机械设备行业中，尝试其他行业...")
        # 遍历主要行业
        industries = {
            "801890": "机械设备",
            "801030": "电力设备",
            "801780": "电子",
            "801790": "计算机",
            "801880": "汽车",
            "801110": "家用电器",
            "801120": "食品饮料",
            "801130": "纺织服饰",
            "801140": "轻工制造",
            "801150": "医药生物",
            "801160": "公用事业",
            "801170": "交通运输",
            "801180": "房地产",
            "801200": "商贸零售",
            "801210": "社会服务",
            "801050": "有色金属",
            "801710": "建筑材料",
            "801720": "建筑装饰",
            "801730": "汽车",
            "801740": "国防军工",
            "801750": "计算机",
            "801760": "传媒",
            "801770": "通信",
            "801010": "农林牧渔",
            "801020": "基础化工",
            "801040": "钢铁",
            "801060": "煤炭",
            "801070": "石油石化",
            "801080": "电子",
            "801090": "家用电器",
            "801100": "银行",
        }
        found = False
        for code, name in industries.items():
            try:
                df2 = ak.index_stock_cons(symbol=code)
                code_col2 = "品种代码" if "品种代码" in df2.columns else df2.columns[0]
                if "603256" in df2[code_col2].astype(str).values:
                    print(f"  ✅ 宏和科技在申万一级行业【{name}({code})】中")
                    found = True
                    break
            except:
                continue
        if not found:
            print(f"  ❌ 未找到宏和科技的申万行业分类")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 5. 测试批量获取（模拟实际使用场景）
print("\n📋 测试4: 批量获取多个行业成分股（性能测试）")
import time
start = time.time()
test_industries = ["801890", "801030", "801780", "801790", "801880"]
total_stocks = 0
for ind_code in test_industries:
    try:
        df = ak.index_stock_cons(symbol=ind_code)
        total_stocks += len(df)
    except Exception as e:
        print(f"  行业{ind_code}获取失败: {e}")
elapsed = time.time() - start
print(f"  5个行业共 {total_stocks} 只成分股, 耗时 {elapsed:.2f}秒")
print(f"  平均每行业: {elapsed/5:.2f}秒")

# 6. 检查与现有 xuan.txt 股票列表的覆盖度
print("\n📋 测试5: 覆盖度检查")
xuan_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xuan.txt")
if os.path.exists(xuan_file):
    with open(xuan_file, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    print(f"  xuan.txt 共 {len(lines)} 只股票")
    # 提取代码
    codes = []
    for l in lines:
        parts = l.replace("\t", " ").split()
        if parts:
            codes.append(parts[0])
    print(f"  前5个代码: {codes[:5]}")
else:
    print(f"  xuan.txt 不存在")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
