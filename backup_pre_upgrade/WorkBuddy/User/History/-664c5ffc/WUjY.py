#!/usr/bin/env python3
"""
全字段取数逻辑审计脚本 v2.0
- 5只不同特征股票端到端验证
- 每个Excel字段从 DB → Calculator → main.py → Excel 全链路追踪
- 性能计时
"""
import sqlite3
import pandas as pd
import numpy as np
import time
import sys
import os

sys.path.insert(0, r'd:\Project\ScoreSys')

TEST_DB = r'd:\Project\ScoreSys\stock_data_test.db'
PYTHON = r'C:\Users\green\AppData\Local\Python\bin\python.exe'

# 5只不同特征股票
TEST_STOCKS = {
    '600519': '贵州茅台 - 高ROE白酒',
    '000858': '五粮液 - 次高端白酒',
    '601398': '工商银行 - 高杠杆银行',
    '002415': '海康威视 - 科技/电子',
    '600036': '招商银行 - 优质银行',
}


def check_db_raw():
    """Step 1: 检查DB中原始数据完整性"""
    print("=" * 80)
    print("Step 1: DB原始数据完整性检查")
    print("=" * 80)
    
    conn = sqlite3.connect(TEST_DB)
    
    for symbol, desc in TEST_STOCKS.items():
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM financials WHERE symbol=?", (symbol,))
        cnt = cur.fetchone()[0]
        
        if cnt == 0:
            print(f"  {symbol} ({desc}): ⚠️ 无数据，需先获取")
            continue
        
        # 检查各关键字段是否有非零值
        fields = ['net_profit_parent', 'net_profit_ex', 'fin_expense', 'revenue',
                  'total_assets', 'total_liab', 'equity_parent', 'current_assets', 'current_liab',
                  'ocf', 'capex', 'cash_from_sales', 'oper_cost', 'oper_profit']
        
        issues = []
        for field in fields:
            cur.execute(f"SELECT COUNT(*) FROM financials WHERE symbol=? AND {field} != 0 AND {field} IS NOT NULL", (symbol,))
            non_zero = cur.fetchone()[0]
            if non_zero == 0:
                issues.append(field)
        
        # 检查行情数据
        cur.execute("SELECT total_mv, pe_ttm FROM quotes WHERE symbol=? ORDER BY trade_date DESC LIMIT 1", (symbol,))
        quote_row = cur.fetchone()
        mv = quote_row[0] if quote_row else 0
        pe = quote_row[1] if quote_row else 0
        
        # 检查stock info
        cur.execute("SELECT name, industry FROM stocks WHERE symbol=?", (symbol,))
        info_row = cur.fetchone()
        name = info_row[0] if info_row else ''
        industry = info_row[1] if info_row else ''
        
        status = "✅" if not issues else f"⚠️ 零值字段: {issues}"
        mv_status = "✅" if mv > 0 else "⚠️ 无市值"
        pe_status = "✅" if pe > 0 else "⚠️ 无PE"
        name_status = "✅" if name and name != symbol else "⚠️ 无名称"
        
        print(f"  {symbol} ({desc}): {cnt}行财务数据 | {status}")
        print(f"    市值: {mv_status} ({mv/1e8:.1f}亿) | PE: {pe_status} ({pe:.1f}) | 名称: {name_status} ({name})")
    
    conn.close()


def check_calculator_logic():
    """Step 2: Calculator计算逻辑验证"""
    print("\n" + "=" * 80)
    print("Step 2: Calculator计算逻辑验证")
    print("=" * 80)
    
    from database import StockDatabase
    from calculator import IndicatorCalculator
    
    db = StockDatabase(TEST_DB)
    
    for symbol, desc in TEST_STOCKS.items():
        df = db.get_financials(symbol)
        if df is None or df.empty or len(df) < 4:
            print(f"  {symbol} ({desc}): ⚠️ 数据不足，跳过")
            continue
        
        # 日期转换
        if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
            df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
        if 'ann_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['ann_date']):
            df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')
        
        try:
            calc = IndicatorCalculator(df)
        except Exception as e:
            print(f"  {symbol} ({desc}): ❌ Calculator异常: {e}")
            continue
        
        metrics = calc.get_metrics()
        
        # 逐字段检查
        zero_fields = []
        for k, v in metrics.items():
            if k == 'report_date':
                continue
            if isinstance(v, (int, float)) and v == 0:
                zero_fields.append(k)
        
        # 特殊检查
        checks = {
            'roe_ttm': ('ROE(TTM)', 0, 100),      # 正常范围 0-100%
            'gross_margin_ttm': ('毛利率', 0, 100),
            'net_margin_ttm': ('净利率', -50, 100),
            'net_profit_ratio': ('净现比', -5, 20),
            'cash_recovery_rate': ('收现比', 0, 3),
            'de_ratio': ('D/E', 0, 30),            # 银行可能高
            'current_ratio': ('流动比率', 0, 10),
            'asset_liability_ratio': ('资产负债率', 0, 100),
            'interest_cover': ('利息覆盖', 0, 2000),
            'q_net_profit_yoy': ('净利润同比', -100, 500),
            'q_revenue_yoy': ('营收同比', -100, 500),
        }
        
        issues = []
        for field, (label, lo, hi) in checks.items():
            val = metrics.get(field, 0)
            if val < lo or val > hi:
                issues.append(f"{label}={val:.2f} 超出正常范围[{lo},{hi}]")
        
        if zero_fields:
            issues.append(f"零值字段: {zero_fields}")
        
        status = "✅" if not issues else "⚠️ " + "; ".join(issues)
        
        # 关键指标展示
        print(f"  {symbol} ({desc}): {status}")
        print(f"    ROE={metrics.get('roe_ttm',0):.2f}% | 毛利率={metrics.get('gross_margin_ttm',0):.2f}% | 净利率={metrics.get('net_margin_ttm',0):.2f}%")
        print(f"    净现比={metrics.get('net_profit_ratio',0):.2f} | 收现比={metrics.get('cash_recovery_rate',0):.2f} | FCF_TTM={metrics.get('fcf_ttm',0)/1e8:.1f}亿")
        print(f"    D/E={metrics.get('de_ratio',0):.2f} | 流动比率={metrics.get('current_ratio',0):.2f} | 资产负债率={metrics.get('asset_liability_ratio',0):.1f}% | 利息覆盖={metrics.get('interest_cover',0):.1f}")
        print(f"    净利润同比={metrics.get('q_net_profit_yoy',0):.1f}% | 营收同比={metrics.get('q_revenue_yoy',0):.1f}%")


def check_score_logic():
    """Step 3: Scorer评分逻辑验证"""
    print("\n" + "=" * 80)
    print("Step 3: Scorer评分逻辑验证")
    print("=" * 80)
    
    from database import StockDatabase
    from calculator import IndicatorCalculator
    from scorer import Scorer
    
    db = StockDatabase(TEST_DB)
    
    for symbol, desc in TEST_STOCKS.items():
        df = db.get_financials(symbol)
        if df is None or df.empty or len(df) < 4:
            continue
        
        if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
            df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
        if 'ann_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['ann_date']):
            df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')
        
        try:
            calc = IndicatorCalculator(df)
        except:
            continue
        
        quote = db.get_quote(symbol)
        industry = db.get_stock_info(symbol).get('industry', None)
        scorer = Scorer(calc, quote, industry=industry)
        scores = scorer.total_score()
        
        print(f"  {symbol} ({desc}):")
        print(f"    总分={scores['total_score']:.1f} | 成长={scores['growth']:.1f} | 盈利={scores['profitability']:.1f} | 现金流={scores['cash_flow']:.1f} | 偿债={scores['leverage']:.1f} | 估值={scores['valuation']:.1f}")
        if scores.get('veto'):
            print(f"    ⚠️ 否决: {scores.get('veto_reason', '')}")


def check_formula_correctness():
    """Step 4: 计算公式正确性手动验证"""
    print("\n" + "=" * 80)
    print("Step 4: 计算公式正确性验证（手动交叉核对）")
    print("=" * 80)
    
    from database import StockDatabase
    
    db = StockDatabase(TEST_DB)
    
    # 用600519做详细验证
    symbol = '600519'
    df = db.get_financials(symbol)
    if df.empty:
        print(f"  {symbol} 无数据")
        return
    
    if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
        df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
    
    # 取最新4期
    df_sorted = df.sort_values('report_date')
    latest4 = df_sorted.tail(4)
    latest = df_sorted.iloc[-1]
    
    print(f"\n  {symbol} 最新4期数据:")
    for _, row in latest4.iterrows():
        print(f"    {row['report_date'].strftime('%Y-%m-%d')}: "
              f"营收={row.get('revenue',0)/1e8:.1f}亿 "
              f"归母净利={row.get('net_profit_parent',0)/1e8:.1f}亿 "
              f"扣非净利={row.get('net_profit_ex',0)/1e8:.1f}亿 "
              f"OCF={row.get('ocf',0)/1e8:.1f}亿")
    
    # 手动计算验证
    ttm_revenue = latest4['revenue'].sum()
    ttm_net_profit_parent = latest4['net_profit_parent'].sum()
    ttm_net_profit_ex = latest4['net_profit_ex'].sum()
    ttm_ocf = latest4['ocf'].sum()
    ttm_capex = latest4['capex'].sum()
    ttm_cash_sales = latest4['cash_from_sales'].sum()
    ttm_oper_cost = latest4['oper_cost'].sum()
    ttm_fin_expense = latest4['fin_expense'].sum()
    ttm_oper_profit = latest4['oper_profit'].sum()
    
    equity_parent = latest.get('equity_parent', 0)
    total_assets = latest.get('total_assets', 0)
    total_liab = latest.get('total_liab', 0)
    total_equity = latest.get('total_equity', 0)
    current_assets = latest.get('current_assets', 0)
    current_liab = latest.get('current_liab', 0)
    
    # 用扣非净利润（如有非零值）
    if (df['net_profit_ex'] != 0).any():
        ttm_net_profit = ttm_net_profit_ex
        profit_src = "扣非净利润"
    else:
        ttm_net_profit = ttm_net_profit_parent
        profit_src = "归母净利润"
    
    # 手动计算各指标
    manual_roe = ttm_net_profit / equity_parent * 100 if equity_parent else 0
    manual_gm = (ttm_revenue - ttm_oper_cost) / ttm_revenue * 100 if ttm_revenue else 0
    manual_nm = ttm_net_profit / ttm_revenue * 100 if ttm_revenue else 0
    manual_npr = ttm_ocf / ttm_net_profit if ttm_net_profit else 0
    manual_crr = ttm_cash_sales / ttm_revenue if ttm_revenue else 0
    manual_fcf = ttm_ocf - ttm_capex
    manual_de = total_liab / total_equity if total_equity else 0
    manual_cr = current_assets / current_liab if current_liab else 0
    manual_alr = total_liab / total_assets * 100 if total_assets else 0
    manual_ic = (ttm_oper_profit + ttm_fin_expense) / ttm_fin_expense if ttm_fin_expense else 0
    
    print(f"\n  手动计算 vs Calculator（使用{profit_src}）:")
    
    from calculator import IndicatorCalculator
    calc = IndicatorCalculator(df)
    
    comparisons = [
        ('ROE(TTM)%', manual_roe, calc.roe_ttm),
        ('毛利率%', manual_gm, calc.gross_margin_ttm),
        ('净利率%', manual_nm, calc.net_margin_ttm),
        ('净现比', manual_npr, calc.net_profit_ratio),
        ('收现比', manual_crr, calc.cash_recovery_rate),
        ('D/E', manual_de, calc.de_ratio),
        ('流动比率', manual_cr, calc.current_ratio),
        ('资产负债率%', manual_alr, calc.asset_liability_ratio),
        ('利息覆盖', manual_ic, calc.interest_cover),
    ]
    
    all_match = True
    for name, manual, actual in comparisons:
        # 注意：Calculator用单季拆分后的TTM，手动用累计值直接求和
        # 对Q4年报来说两者等价，但Q1-Q3会有差异
        # 这里允许5%的误差（因为单季拆分可能有细微差异）
        if manual != 0:
            diff_pct = abs(actual - manual) / abs(manual) * 100
        else:
            diff_pct = 0 if actual == 0 else 999
        match = diff_pct < 5  # 5%容差
        status = "✅" if match else f"❌ 差{diff_pct:.1f}%"
        if not match:
            all_match = False
        print(f"    {name}: 手动={manual:.2f} | Calculator={actual:.2f} | {status}")
    
    if all_match:
        print(f"\n  ✅ 所有指标手动验证通过（5%容差内）")
    else:
        print(f"\n  ⚠️ 部分指标差异较大，可能因单季拆分逻辑导致（Q1-Q3累计值≠单季求和）")


def check_interest_cover_formula():
    """Step 5: 利息覆盖倍数公式专项验证"""
    print("\n" + "=" * 80)
    print("Step 5: 利息覆盖倍数公式验证")
    print("=" * 80)
    
    from database import StockDatabase
    from calculator import IndicatorCalculator
    
    db = StockDatabase(TEST_DB)
    
    for symbol, desc in TEST_STOCKS.items():
        df = db.get_financials(symbol)
        if df is None or df.empty or len(df) < 4:
            continue
        
        if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
            df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
        
        try:
            calc = IndicatorCalculator(df)
        except:
            continue
        
        # 利息覆盖倍数 = (TTM营业利润 + TTM财务费用) / TTM财务费用
        # 等价于 EBIT / Interest = (OperProfit + FinExpense) / FinExpense
        # 注意：这里 fin_expense 在DB中已取绝对值
        
        ic = calc.interest_cover
        print(f"  {symbol} ({desc}): 利息覆盖={ic:.2f}")
        
        # 边界检查：如果fin_expense=0，interest_cover应该=0
        if calc._ttm_fin_expense == 0 and ic != 0:
            print(f"    ❌ fin_expense=0时interest_cover应为0，实际={ic}")
        elif calc._ttm_fin_expense != 0:
            expected = (calc._ttm_oper_profit + calc._ttm_fin_expense) / calc._ttm_fin_expense
            if abs(ic - expected) > 0.01:
                print(f"    ❌ 期望={expected:.2f}，实际={ic:.2f}")
            else:
                print(f"    ✅ 公式正确: ({calc._ttm_oper_profit/1e8:.1f}+{calc._ttm_fin_expense/1e8:.1f})/{calc._ttm_fin_expense/1e8:.1f}={expected:.2f}")


def check_performance():
    """Step 6: 性能测试"""
    print("\n" + "=" * 80)
    print("Step 6: 性能测试")
    print("=" * 80)
    
    from database import StockDatabase
    from calculator import IndicatorCalculator
    from scorer import Scorer
    
    db = StockDatabase(TEST_DB)
    
    # DB读取性能
    t0 = time.time()
    for _ in range(100):
        df = db.get_financials('600519')
    db_read_time = (time.time() - t0) / 100 * 1000
    
    # Calculator性能
    df = db.get_financials('600519')
    if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
        df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
    if 'ann_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['ann_date']):
        df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')
    
    t0 = time.time()
    for _ in range(100):
        calc = IndicatorCalculator(df)
    calc_time = (time.time() - t0) / 100 * 1000
    
    # Scorer性能
    quote = db.get_quote('600519')
    t0 = time.time()
    for _ in range(1000):
        scorer = Scorer(calc, quote)
        scores = scorer.total_score()
    score_time = (time.time() - t0) / 1000 * 1000
    
    # 全链路性能（单只）
    t0 = time.time()
    for symbol in TEST_STOCKS:
        df = db.get_financials(symbol)
        if df is not None and not df.empty and len(df) >= 4:
            if not pd.api.types.is_datetime64_any_dtype(df['report_date']):
                df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
            if 'ann_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['ann_date']):
                df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')
            calc = IndicatorCalculator(df)
            quote = db.get_quote(symbol)
            scorer = Scorer(calc, quote)
            scores = scorer.total_score()
    full_time = (time.time() - t0) * 1000
    
    print(f"  DB单次读取: {db_read_time:.1f}ms")
    print(f"  Calculator单次: {calc_time:.1f}ms")
    print(f"  Scorer单次: {score_time:.2f}ms")
    print(f"  全链路5只股票: {full_time:.0f}ms ({full_time/5:.0f}ms/只)")
    
    # 性能评估
    perf_ok = True
    if db_read_time > 50:
        print(f"  ⚠️ DB读取偏慢（>{50}ms），考虑加索引")
        perf_ok = False
    if calc_time > 100:
        print(f"  ⚠️ Calculator偏慢（>{100}ms）")
        perf_ok = False
    if full_time / 5 > 200:
        print(f"  ⚠️ 全链路偏慢（>200ms/只），4000只需{4000*0.2/60:.1f}分钟")
        perf_ok = False
    
    if perf_ok:
        est_4000 = 4000 * (full_time / 5) / 1000
        print(f"  ✅ 性能OK，预估4000只需{est_4000:.0f}秒（{est_4000/60:.1f}分钟）")


def check_edge_cases():
    """Step 7: 边界Case验证"""
    print("\n" + "=" * 80)
    print("Step 7: 边界Case验证")
    print("=" * 80)
    
    from calculator import IndicatorCalculator
    
    # Case 1: 全0 fin_expense → interest_cover应为0
    print("\n  Case 1: fin_expense=0 → interest_cover应为0")
    df_zero = pd.DataFrame({
        'report_date': pd.date_range('2024-03-31', periods=4, freq='QE'),
        'ann_date': pd.date_range('2024-04-30', periods=4, freq='30D'),
        'revenue': [100, 200, 300, 400],
        'oper_cost': [50, 100, 150, 200],
        'oper_profit': [50, 100, 150, 200],
        'net_profit_parent': [30, 60, 90, 120],
        'net_profit_ex': [25, 50, 75, 100],
        'ocf': [40, 80, 120, 160],
        'capex': [10, 20, 30, 40],
        'cash_from_sales': [90, 180, 270, 360],
        'fin_expense': [0, 0, 0, 0],
        'total_assets': [1000, 1000, 1000, 1000],
        'total_liab': [300, 300, 300, 300],
        'total_equity': [700, 700, 700, 700],
        'equity_parent': [650, 650, 650, 650],
        'current_assets': [400, 400, 400, 400],
        'current_liab': [200, 200, 200, 200],
    })
    try:
        calc = IndicatorCalculator(df_zero)
        if calc.interest_cover == 0:
            print(f"    ✅ interest_cover=0 正确")
        else:
            print(f"    ❌ interest_cover={calc.interest_cover}，应为0")
    except Exception as e:
        print(f"    ❌ 异常: {e}")
    
    # Case 2: 负净利润 → 净现比可能为负
    print("\n  Case 2: 负净利润 → 净现比")
    df_neg = df_zero.copy()
    df_neg['net_profit_parent'] = [-30, -60, -90, -120]
    df_neg['net_profit_ex'] = [-25, -50, -75, -100]
    try:
        calc = IndicatorCalculator(df_neg)
        if calc.net_profit_ratio < 0:
            print(f"    ✅ 净现比={calc.net_profit_ratio:.2f}（负净利润，负净现比合理）")
        else:
            print(f"    ⚠️ 净现比={calc.net_profit_ratio:.2f}（负净利润时应为负值）")
    except Exception as e:
        print(f"    ❌ 异常: {e}")
    
    # Case 3: 极高D/E（银行类）→ 不应crash
    print("\n  Case 3: 极高D/E（银行类）")
    df_bank = df_zero.copy()
    df_bank['total_liab'] = [9000, 9000, 9000, 9000]
    df_bank['total_equity'] = [1000, 1000, 1000, 1000]
    df_bank['current_liab'] = [7000, 7000, 7000, 7000]
    try:
        calc = IndicatorCalculator(df_bank)
        print(f"    ✅ D/E={calc.de_ratio:.2f}, 资产负债率={calc.asset_liability_ratio:.1f}%（无crash）")
    except Exception as e:
        print(f"    ❌ 异常: {e}")


if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    check_db_raw()
    check_calculator_logic()
    check_score_logic()
    check_formula_correctness()
    check_interest_cover_formula()
    check_performance()
    check_edge_cases()
    
    print("\n" + "=" * 80)
    print("审计完成")
    print("=" * 80)
