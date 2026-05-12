#!/usr/bin/env python3

# 读取原始文件内容（不包含IndicatorCalculator类）
with open('d:/Project/QAScorer/qa_scorer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到fetch_quarterly_data函数开始的位置
start_idx = None
for i, line in enumerate(lines):
    if 'def fetch_quarterly_data(' in line:
        start_idx = i
        break

if start_idx is None:
    print("未找到fetch_quarterly_data函数")
    exit(1)

# 找到IndicatorCalculator类的开始位置
end_idx = None
for i in range(start_idx + 1, len(lines)):
    if 'class IndicatorCalculator:' in lines[i]:
        end_idx = i
        break

if end_idx is None:
    print("未找到IndicatorCalculator类")
    # 如果没有找到，使用文件末尾
    end_idx = len(lines)

# 只保留到fetch_quarterly_data函数之前的部分
original_lines = lines[:start_idx]

# 添加修复后的get_combined_financials函数
get_combined_financials_code = '''
def get_combined_financials(symbol):
    """获取股票三大报表数据并合并"""
    try:
        import pandas as pd
        import akshare as ak

        # 获取利润表
        income_df = ak.stock_financial_analysis_indicator(symbol, "income")
        if not income_df.empty:
            income_df = income_df[['report_date', '营业收入', '营业成本', '营业利润', '净利润',
                                 '营业收入同比增长', '净利润同比增长']].copy()
            income_df.columns = ['report_date', 'revenue', 'operating_cost', 'oper_profit', 'net_profit',
                               'revenue_yoy', 'profit_yoy']

            # 获取资产负债表
            balance_df = ak.stock_financial_analysis_indicator(symbol, "balancesheet")
            if not balance_df.empty:
                balance_df = balance_df[['report_date', '资产总计', '负债合计', '股东权益合计']].copy()
                balance_df.columns = ['report_date', 'total_assets', 'total_liabilities', 'equity_parent']

            # 获取现金流量表
            cashflow_df = ak.stock_financial_analysis_indicator(symbol, "cashflow")
            if not cashflow_df.empty:
                cashflow_df = cashflow_df[['report_date', '经营活动产生的现金流量净额']].copy()
                cashflow_df.columns = ['report_date', 'ocf_abs']

            # 合并数据
            merged = income_df.copy()
            if not balance_df.empty:
                merged = merged.merge(balance_df, on='report_date', how='left')
            if not cashflow_df.empty:
                merged = merged.merge(cashflow_df, on='report_date', how='left')

            return merged.sort_values('report_date', ascending=False).reset_index(drop=True)

        return pd.DataFrame()
    except Exception as e:
        print(f"获取{symbol}财务数据失败: {e}")
        return pd.DataFrame()

'''

# 添加修复后的fetch_quarterly_data函数
fetch_quarterly_data_start = '''def fetch_quarterly_data(
    ts_code: str,
    name: str,
    token: str
) -> Dict[str, Any]:
    """
    获取单只股票季报数据，返回：
    - TTM指标（盈利、现金流）
    - 最新单季指标（成长性、偿债风险）

    V7.0: 优先读取缓存DB，无有效缓存时调用API
    """
    # 1. 先检查缓存
    cached = _load_quarterly_from_db(ts_code)
    if cached:
        logger.debug(f"使用季报缓存 {ts_code}")
        return {
            "ttm_metrics": {
                "roe_ttm": cached.get("roe_ttm"),
                "gross_margin_ttm": cached.get("gross_margin_ttm"),
                "net_margin_ttm": cached.get("net_margin_ttm"),
                "ocf_ratio_ttm": cached.get("ocf_ratio_ttm"),
                "revenue_ttm": cached.get("revenue_ttm"),
                "cost_ttm": cached.get("operating_cost_ttm"),
                "net_profit_ttm": cached.get("net_profit_ttm"),
                "ocf_abs_ttm": cached.get("ocf_abs_ttm"),
                "net_assets_ttm": cached.get("net_assets_ttm"),
            },
            "latest_quarterly": {
                "revenue_yoy": cached.get("revenue_yoy_latest"),
                "profit_yoy": cached.get("profit_yoy_latest"),
                "debt_ratio": cached.get("debt_ratio_latest"),
                "total_assets": cached.get("total_assets_latest"),
                "total_liabilities": cached.get("total_liabilities_latest"),
            },
            "content": "",
            "fetch_success": True,
            "quarter_count": cached.get("quarter_count", 0),
            "latest_quarter": cached.get("latest_quarter", ""),
        }

    # 2. 调用AkShare获取财务数据
    try:
        df_fin = get_combined_financials(ts_code)
        if df_fin.empty:
            logger.warning(f"获取 {ts_code} 财务数据失败：返回空DataFrame")
            return {
                "ttm_metrics": {},
                "latest_quarterly": {},
                "content": "",
                "fetch_success": False,
                "quarter_count": 0,
                "latest_quarter": "",
            }
'''

# 合并所有部分
final_lines = original_lines + [get_combined_financials_code] + [fetch_quarterly_data_start] + lines[end_idx:]

# 写入修复后的文件
with open('d:/Project/QAScorer/qa_scorer.py', 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

print("文件重建完成")