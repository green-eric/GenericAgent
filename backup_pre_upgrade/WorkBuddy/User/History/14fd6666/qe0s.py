#!/usr/bin/env python3
"""端到端单股测试：获取→存DB→评分→输出，定位所有问题"""
import sys, os, time, logging
sys.path.insert(0, r'd:\Project\ScoreSys')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger('e2e_test')

SYMBOL = '601088'  # 中国神华，大盘股数据稳定

def test_financials():
    """测试1：获取三大报表"""
    from data_provider import DataProvider
    t0 = time.time()
    df = DataProvider.get_combined_financials(SYMBOL)
    elapsed = time.time() - t0
    if df is None or df.empty:
        log.error(f"[FAIL] 财务数据为空 | {elapsed:.1f}s")
        return None
    log.info(f"[OK] 财务数据：{len(df)}行 | {elapsed:.1f}s")
    print(df.tail(3).to_string())
    return df

def test_stock_info():
    """测试2：获取名称+行业+行情（合并API）"""
    from data_provider import DataProvider, _fetch_stock_info
    t0 = time.time()
    info = _fetch_stock_info(SYMBOL)
    elapsed = time.time() - t0
    log.info(f"[OK] 股票信息：name={info['name']} industry={info['industry']} MV={info['total_mv']:.0f} PE={info['pe_ttm']:.1f} | {elapsed:.1f}s")
    
    t0 = time.time()
    quote = DataProvider.get_stock_quote(SYMBOL)
    elapsed = time.time() - t0
    log.info(f"[OK] 行情：MV={quote['total_mv']:.0f} PE={quote['pe_ttm']:.1f} | {elapsed:.1f}s")
    return info, quote

def test_db_save(df, info, quote):
    """测试3：存DB"""
    from database import StockDatabase
    db = StockDatabase(r'd:\Project\ScoreSys\stock_data_test.db')
    t0 = time.time()
    db.save_financials(SYMBOL, df)
    db.save_stock_info(SYMBOL, info['name'], info['industry'])
    db.save_quote(SYMBOL, quote)
    elapsed = time.time() - t0
    stats = db.get_db_stats()
    log.info(f"[OK] DB写入完成 | {elapsed:.1f}s | 财务记录={stats['financials']} 股票数={stats['symbols_with_fin']}")
    return db

def test_scoring(db):
    """测试4：从DB读取评分"""
    import pandas as pd
    from datetime import datetime
    from calculator import IndicatorCalculator
    from scorer import Scorer
    
    eval_date = pd.Timestamp(datetime.today())
    
    t0 = time.time()
    df = db.get_financials(SYMBOL)
    if df is None or df.empty or len(df) < 4:
        log.error(f"[FAIL] DB读取财务数据不足：{len(df) if df is not None else 0}行")
        return
    
    # ann_date过滤
    if 'ann_date' in df.columns:
        df['ann_date'] = pd.to_datetime(df['ann_date'], errors='coerce')
        df = df[df['ann_date'] <= eval_date].copy()
    if len(df) < 4:
        log.error(f"[FAIL] ann_date过滤后数据不足：{len(df)}行")
        return
    
    calc = IndicatorCalculator(df, eval_date=eval_date)
    
    stock_info = db.get_stock_info(SYMBOL)
    name = stock_info.get('name', SYMBOL) if stock_info else SYMBOL
    industry = stock_info.get('industry', None) if stock_info else None
    quote = db.get_quote(SYMBOL)
    
    scorer = Scorer(calc, quote, industry=industry)
    scores = scorer.total_score()
    
    elapsed = time.time() - t0
    log.info(f"[OK] 评分完成 | {elapsed:.1f}s")
    log.info(f"  {SYMBOL} {name} | 总分={scores['total_score']:.1f} 评级={'A+' if scores['total_score']>=80 else 'A' if scores['total_score']>=70 else 'B+' if scores['total_score']>=60 else 'B' if scores['total_score']>=50 else 'C' if scores['total_score']>=40 else 'D'}")
    log.info(f"  成长={scores['growth']:.1f} 盈利={scores['profitability']:.1f} 现金流={scores['cash_flow']:.1f} 偿债={scores['leverage']:.1f} 估值={scores['valuation']:.1f}")
    if scores.get('veto'):
        log.info(f"  否决：{scores.get('veto_reason')}")

if __name__ == '__main__':
    log.info(f"========== 端到端测试：{SYMBOL} ==========")
    
    # Step1: 财务数据
    df = test_financials()
    if df is None:
        log.error("财务数据获取失败，终止测试")
        sys.exit(1)
    
    # Step2: 股票信息+行情
    info, quote = test_stock_info()
    
    # Step3: 存DB
    db = test_db_save(df, info, quote)
    
    # Step4: 评分
    test_scoring(db)
    
    log.info("========== 端到端测试完成 ==========")
