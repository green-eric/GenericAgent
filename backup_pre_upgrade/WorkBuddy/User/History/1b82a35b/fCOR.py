#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 akshare 利润表接口验证"""
import akshare as ak
import warnings
warnings.filterwarnings("ignore")

stocks = [
    ("603350", "603350.SH", "安乃达"),
    ("000852", "000852.SZ", "石化机械"),
]

# Excel中的数据
excel_data = {
    "603350.SH": {
        "ROE(%)": 8.67, "毛利率(%)": 15.53, "净利率(%)": 5.7,
        "营收同比(%)": 31.14, "净利润同比(%)": 4.62,
        "资产负债率(%)": 44.59, "净利润(元)": 115036375.06,
        "经营现金流(元)": -1455064.26,
    },
    "000852.SZ": {
        "ROE(%)": 0.35, "毛利率(%)": 14.09, "净利率(%)": 0.43,
        "营收同比(%)": -10.37, "净利润同比(%)": -88.79,
        "资产负债率(%)": 68.27, "净利润(元)": 10858163.44,
        "经营现金流(元)": 591141237.03,
    },
}

for code, ts_code, name in stocks:
    print(f"\n{'='*60}")
    print(f"验证: {ts_code} {name}")
    print(f"{'='*60}")
    
    excel = excel_data[ts_code]
    
    print(f"\n  [Excel数据]")
    for k, v in excel.items():
        print(f"    {k}: {v}")
    
    # 方法1: 新浪财经利润表
    print(f"\n  [akshare 新浪利润表]")
    try:
        df = ak.stock_financial_report_sina(stock=ts_code, symbol="利润表")
        if df is not None and len(df) > 0:
            print(f"    列名: {list(df.columns)[:10]}")
            # 打印前几行
            for idx, row in df.head(3).iterrows():
                print(f"    行{idx}: {dict(list(row.items())[:8])}")
        else:
            print("    无数据")
    except Exception as e:
        print(f"    错误: {e}")
    
    # 方法2: 主要财务指标
    print(f"\n  [akshare 主要财务指标]")
    try:
        df2 = ak.stock_financial_analysis_indicator(symbol=code, start_year="2024")
        if df2 is not None and len(df2) > 0:
            print(f"    列名: {list(df2.columns)}")
            for col in df2.columns:
                val = df2[col].iloc[0]
                if val is not None and str(val).strip():
                    print(f"    {col}: {val}")
        else:
            print("    无数据")
    except Exception as e:
        print(f"    错误: {e}")

print(f"\n{'='*60}")
print("验证完成")
