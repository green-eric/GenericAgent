"""精确查找宏和科技的申万行业分类"""
import sys, time
import akshare as ak

TARGET = "603256"
TARGET_SH = "603256.SH"

# 方法1: stock_industry_clf_hist_sw - 单只股票历史行业
print("--- 方法1: stock_industry_clf_hist_sw ---")
try:
    t0 = time.time()
    df = ak.stock_industry_clf_hist_sw(symbol=TARGET)
    print(f"耗时: {time.time()-t0:.2f}s")
    print(f"列名: {list(df.columns)}")
    print(df.tail(5).to_string())
except Exception as e:
    print(f"失败: {e}")

# 方法2: 用 NeoData API 查行业
print("\n--- 方法2: NeoData API 查行业 ---")
try:
    from annual_scorer import run_neodata, load_token
    token = load_token()
    text = run_neodata("603256.SH 宏和科技 申万一级行业分类", token)
    print(f"NeoData返回: {text[:500] if text else 'None'}")
except Exception as e:
    print(f"失败: {e}")

# 方法3: 直接用东方财富个股行业
print("\n--- 方法3: 东方财富个股行业 ---")
try:
    t0 = time.time()
    df = ak.stock_individual_info_em(symbol=TARGET)
    print(f"耗时: {time.time()-t0:.2f}s")
    print(f"列名: {list(df.columns)}")
    print(df.to_string())
except Exception as e:
    print(f"失败: {e}")
