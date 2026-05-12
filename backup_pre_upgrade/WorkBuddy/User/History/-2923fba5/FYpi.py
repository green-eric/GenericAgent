#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 akshare 验证 Excel 中2只股票的财务数据
"""
import akshare as ak
import warnings
warnings.filterwarnings("ignore")

stocks = [
    ("603350", "安乃达", "603350.SH"),
    ("000852", "石化机械", "000852.SZ"),
]

for code, name, ts_code in stocks:
    print(f"\n{'='*60}")
   验证: {ts_code} {name}")
    print(f"{'='*60}")
    
    try:
        # 获取年报数据
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2024")
        if df is not None and len(df) > 0:
            print(f"\n  akshare 财务指标 (2024年报):")
            # 打印关键列
            key_cols = ["净资产收益率", "总资产净利润率", "销售毛利率", "销售净利率", 
                       "资产负债率", "营业收入同比增长率", "净利润同比增长率"]
            for col in key_cols:
                if col in df.columns:
                    val = df[col].iloc[0]
                    print(f"    {col}: {val}")
        else:
            print("  akshare 无数据")
    except Exception as e:
        print(f"  akshare 错误: {e}")
    
    try:
        # 获取利润表
        df2 = ak.stock_financial_report_sina(stock=ts_code, symbol="利润表")
        if df2 is not None and len(df2) > 0:
            print(f"\n  利润表关键数据:")
            # 找最新年报
            for idx, row in df2.head(5).iterrows():
                date_col = df2.columns[0]
                print(f"    {row[date_col]}: ", end="")
                vals = []
                for c in df2.columns[1:6]:
                    vals.append(f"{c}={row[c]}")
                print(", ".join(vals))
    except Exception as e:
        print(f"  利润表错误: {e}")
