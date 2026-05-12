"""最小可行性测试：akshare 申万行业分类"""
import sys, time

# 1. 检查安装
try:
    import akshare as ak
    print(f"akshare {ak.__version__} 已安装")
except ImportError:
    print("akshare 未安装，请先: pip install akshare")
    sys.exit(1)

# 2. 测试申万一级行业列表
print("\n--- 申万一级行业列表 ---")
try:
    t0 = time.time()
    df = ak.sw_index_first_info()
    print(f"耗时: {time.time()-t0:.2f}s | 共{len(df)}个行业")
    print(f"列名: {list(df.columns)}")
    print(df.head(3).to_string())
except Exception as e:
    print(f"失败: {e}")

# 3. 测试获取单行业成分股
print("\n--- 申万一级行业成分股(801890 机械设备) ---")
try:
    t0 = time.time()
    df = ak.index_stock_cons(symbol="801890")
    print(f"耗时: {time.time()-t0:.2f}s | 共{len(df)}只")
    print(f"列名: {list(df.columns)}")
    # 找宏和科技
    for col in df.columns:
        if df[col].astype(str).str.contains("603256").any():
            row = df[df[col].astype(str) == "603256"]
            print(f"宏和科技找到: {row.to_string()}")
            break
    else:
        print("宏和科技不在机械设备行业")
except Exception as e:
    print(f"失败: {e}")

# 4. 性能测试：连续调5个行业
print("\n--- 性能: 连续获取5个行业 ---")
ind_codes = ["801890", "801030", "801780", "801790", "801880"]
t0 = time.time()
total = 0
for c in ind_codes:
    try:
        df = ak.index_stock_cons(symbol=c)
        total += len(df)
    except Exception as e:
        print(f"  {c} 失败: {e}")
print(f"5个行业共{total}只, 耗时{time.time()-t0:.2f}s, 平均{(time.time()-t0)/5:.2f}s/行业")
