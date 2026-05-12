import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# xuan.txt中的股票代码（只取前50只进行演示）
xuan_stocks = [
    "002705", "002718", "002730", "002738", "600103", "600105", "600110", "600114",
    "002752", "600118", "600126", "002787", "600150", "600152", "002796", "600166",
    "600176", "002810", "600183", "600184", "600186", "002821", "600206", "002824",
    "600208", "002843", "600234", "002850", "002866", "002885", "002916", "600330",
    "600331", "600337", "600338", "002937", "600345", "002938", "002940", "002943",
    "002947", "002957", "002975", "002980", "002990", "003018", "003022", "003023",
    "003031", "003036"
]

def query_stock_industry(symbol):
    """查询单只股票的行业分类"""
    exchange_suffix = ".SZ" if symbol.startswith(('0','3')) else ".SH"
    ts_code = symbol + exchange_suffix

    try:
        result = subprocess.run([
            "python", "C:\\Users\\green\\.workbuddy\\plugins\\marketplaces\\cb_teams_marketplace\\plugins\\finance-data\\skills\\neodata-financial-search\\scripts\\query.py",
            "--query", f"{symbol}股票行业分类"
        ], capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get("suc") and data.get("data", {}).get("apiData", {}).get("apiRecall"):
                api_recall = data["data"]["apiData"]["apiRecall"]

                for recall_item in api_recall:
                    content = recall_item.get("content", "")
                    if "所属一级行业" in content or "所属行业" in content:
                        # 提取行业信息
                        if "所属一级行业：" in content:
                            industry = content.split("所属一级行业：")[1].split("，")[0].strip()
                        elif "所属行业：" in content:
                            industry = content.split("所属行业：")[1].split("；")[0].strip()
                        else:
                            continue

                        if industry and industry != "未知":
                            return symbol, industry, "成功"

                return symbol, "未明确", "成功"
            else:
                return symbol, "未找到", "成功"
        else:
            return symbol, "API失败", "失败"

    except Exception as e:
        return symbol, f"错误: {str(e)}", "失败"

print("=== 使用真实API并行获取股票行业分类 ===")
print(f"总共要分析: {len(xuan_stocks)} 只股票")

# 使用线程池并行处理
start_time = time.time()
industry_distribution = {}
results = []

with ThreadPoolExecutor(max_workers=10) as executor:
    # 提交所有任务
    future_to_symbol = {executor.submit(query_stock_industry, symbol): symbol for symbol in xuan_stocks}

    # 收集结果
    completed = 0
    for future in as_completed(future_to_symbol):
        symbol, industry, status = future.result()
        results.append((symbol, industry, status))

        # 更新行业分布统计
        industry_distribution[industry] = industry_distribution.get(industry, 0) + 1

        completed += 1
        if completed % 10 == 0:
            elapsed = time.time() - start_time
            print(f"已完成 {completed}/{len(xuan_stocks)} 只 ({completed/len(xuan_stocks)*100:.1f}%) | 用时: {elapsed:.1f}s")

# 显示结果
print(f"\n=== 真实行业分布统计结果 ===")
print(f"总用时: {time.time() - start_time:.1f}秒")
print(f"成功分析: {sum(1 for r in results if r[2] == '成功')} 只")

sorted_industries = sorted(industry_distribution.items(), key=lambda x: x[1], reverse=True)
for i, (industry, count) in enumerate(sorted_industries):
    percentage = count / len(results) * 100
    print(f"{i+1}. {industry}: {count}只 ({percentage:.1f}%)")

print(f"\n=== 详细结果 (前20只) ===")
successful_results = [r for r in results if r[2] == '成功']
for i, (symbol, industry, _) in enumerate(successful_results[:20]):
    name = symbol.replace('.SZ', '').replace('.SH', '')
    print(f"{i+1:2d}. {name}({symbol}) -> {industry}")

if len(successful_results) > 20:
    print(f"\n... 还有 {len(successful_results) - 20} 只股票的结果")

print(f"\n=== 分析完成 ===")
print(f"成功率: {len([r for r in results if r[2] == '成功'])}/{len(results)} ({len([r for r in results if r[2] == '成功'])/len(results)*100:.1f}%)")