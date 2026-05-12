"""精确查找宏和科技的申万行业分类"""
import sys, time
import akshare as ak

TARGET = "603256"

# 方法1: 遍历所有申万一级行业
print("--- 方法1: 遍历所有一级行业 ---")
try:
    df_info = ak.sw_index_first_info()
    t0 = time.time()
    found = False
    for _, row in df_info.iterrows():
        ind_code = row["行业代码"].split(".")[0]  # 801010
        ind_name = row["行业名称"]
        try:
            df_cons = ak.index_stock_cons(symbol=ind_code)
            code_col = "品种代码"
            if TARGET in df_cons[code_col].astype(str).values:
                stock_row = df_cons[df_cons[code_col].astype(str) == TARGET]
                print(f"✅ 找到! 申万一级行业: 【{ind_name}({ind_code})】")
                print(f"   成分股信息: {stock_row.to_string()}")
                found = True
                break
        except:
            continue
    if not found:
        print(f"❌ 未在任何申万一级行业中找到 {TARGET}")
    print(f"耗时: {time.time()-t0:.2f}s")
except Exception as e:
    print(f"失败: {e}")

# 方法2: 用 akshare 的股票行业分类接口
print("\n--- 方法2: stock_industry_clf_hist_sw ---")
try:
    t0 = time.time()
    df = ak.stock_industry_clf_hist_sw(symbol=TARGET)
    print(f"耗时: {time.time()-t0:.2f}s")
    print(f"列名: {list(df.columns)}")
    print(df.tail(5).to_string())
except Exception as e:
    print(f"失败: {e}")

# 方法3: 用东方财富行业分类
print("\n--- 方法3: 东方财富行业分类 ---")
try:
    t0 = time.time()
    df = ak.stock_board_industry_name_em()
    print(f"耗时: {time.time()-t0:.2f}s | 共{len(df)}个行业")
    print(f"列名: {list(df.columns)}")
    # 找宏和科技
    for col in df.columns:
        if df[col].astype(str).str.contains("宏和").any():
            print(f"找到: {df[df[col].astype(str).str.contains('宏和')].to_string()}")
            break
except Exception as e:
    print(f"失败: {e}")

# 方法4: 申万二级行业
print("\n--- 方法4: 申万二级行业成分股 ---")
try:
    t0 = time.time()
    df_sw2 = ak.sw_index_second_info()
    print(f"耗时: {time.time()-t0:.2f}s | 共{len(df_sw2)}个二级行业")
    print(f"列名: {list(df_sw2.columns)}")
    print(df_sw2.head(3).to_string())
except Exception as e:
    print(f"失败: {e}")
