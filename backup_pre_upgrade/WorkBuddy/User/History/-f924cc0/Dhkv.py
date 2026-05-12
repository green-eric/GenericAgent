"""
测试 akshare 批量获取申万行业分类的可行性
重点：性能 + 覆盖度
"""
import sys, time, json, os
import akshare as ak

xuan_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xuan.txt")

# 读取 xuan.txt 的股票代码
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
print(f"前10个: {codes[:10]}")

# 方法A: 获取所有申万一级行业成分股，构建 code->industry 映射
print("\n--- 方法A: 全量获取申万一级行业成分股 ---")
t0 = time.time()
industry_map_new = {}  # code -> industry_name

try:
    df_info = ak.sw_index_first_info()
    print(f"申万一级行业数: {len(df_info)}, 获取耗时: {time.time()-t0:.2f}s")
    
    for _, row in df_info.iterrows():
        ind_code = row["行业代码"].split(".")[0]
        ind_name = row["行业名称"]
        try:
            df_cons = ak.index_stock_cons(symbol=ind_code)
            code_col = "品种代码"
            for _, stock in df_cons.iterrows():
                code = str(stock[code_col])
                if code not in industry_map_new:  # 只记录首次出现
                    industry_map_new[code] = ind_name
        except Exception as e:
            print(f"  {ind_name}({ind_code}) 获取失败: {e}")
    
    elapsed = time.time() - t0
    print(f"总耗时: {elapsed:.2f}s")
    print(f"覆盖股票数: {len(industry_map_new)}")
    
    # 检查 xuan.txt 的覆盖度
    covered = sum(1 for c in codes if c in industry_map_new)
    print(f"xuan.txt 覆盖度: {overed}/{len(codes)} = {covered/len(codes)*100:.1f}%")
    
    # 显示未覆盖的股票
    missing = [c for c in codes if c not in industry_map_new]
    if missing:
        print(f"未覆盖({len(missing)}只): {missing[:20]}...")
    
    # 检查宏和科技
    print(f"\n宏和科技(603256)行业: {industry_map_new.get('603256', '未找到')}")
    
    # 对比旧映射表
    old_map_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "industry_map.json")
    if os.path.exists(old_map_file):
        with open(old_map_file, encoding="utf-8") as f:
            old_map = json.load(f)
        
        # 统计差异
        diff_count = 0
        diff_samples = []
        for c in codes:
            old_ind = old_map.get(c, old_map.get(f"{c}.SH", old_map.get(f"{c}.SZ", "未知")))
            new_ind = industry_map_new.get(c, "未知")
            if old_ind != new_ind:
                diff_count += 1
                if len(diff_samples) < 10:
                    diff_samples.append(f"  {c}: {old_ind} → {new_ind}")
        
        print(f"\n新旧映射差异: {diff_count}/{len(codes)} 只行业不同")
        for s in diff_samples:
            print(s)

except Exception as e:
    print(f"失败: {e}")
    import traceback
    traceback.print_exc()
