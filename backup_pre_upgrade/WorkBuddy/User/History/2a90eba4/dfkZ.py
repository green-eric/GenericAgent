#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 akshare 验证2025年报数据
"""
import akshare as ak
import warnings
warnings.filterwarnings("ignore")

# Excel中的数据
excel = {
    "603350.SH": {
        "name": "安乃达",
        "ROE(%)": 8.67,
        "毛利率(%)": 15.53,
        "净利率(%)": 5.7,
        "营收同比(%)": 31.14,
        "净利润同比(%)": 4.62,
        "资产负债率(%)": 44.59,
        "净利润(元)": 115036375.06,
        "经营现金流(元)": -1455064.26,
        "OCF/净利润(%)": -1.26,
        "总分": 54.04,
        "评级": "C",
    },
    "000852.SZ": {
        "name": "石化机械",
        "ROE(%)": 0.35,
        "毛利率(%)": 14.09,
        "净利率(%)": 0.43,
        "营收同比(%)": -10.37,
        "净利润同比(%)": -88.79,
        "资产负债率(%)": 68.27,
        "净利润(元)": 10858163.44,
        "经营现金流(元)": 591141237.03,
        "OCF/净利润(%)": 5444.21,
        "总分": 31.61,
        "评级": "D",
    },
}

stocks = [
    ("603350", "603350.SH"),
    ("000852", "000852.SZ"),
]

for code, ts_code in stocks:
    name = excel[ts_code]["name"]
    print(f"\n{'='*70}")
    print(f"验证: {ts_code} {name}")
    print(f"{'='*70}")
    
    print(f"\n  [Excel 2025年报数据]")
    for k, v in excel[ts_code].items():
        print(f"    {k}: {v}")
    
    # akshare 财务指标 (2025年报)
    print(f"\n  [akshare 财务指标 2025年报]")
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2025")
        if df is not None and len(df) > 0:
            # 找2025年报行
            for idx, row in df.iterrows():
                date_val = str(row.get("日期", ""))
                if "2025" in date_val and "1231" in date_val:
                    print(f"    日期: {date_val}")
                    key_cols = ["净资产收益率(%)", "销售毛利率(%)", "销售净利率(%)", 
                               "主营业务收入增长率(%)", "净利润增长率(%)", "资产负债率(%)"]
                    for col in key_cols:
                        if col in df.columns:
                            print(f"    {col}: {row[col]}")
                    break
            else:
                # 打印所有行
                print(f"    未找到2025年报，可用数据:")
                for idx, row in df.iterrows():
                    print(f"    行{idx}: 日期={row.get('日期', 'N/A')}")
                    for col in ["净资产收益率(%)", "销售净利率(%)", "资产负债率(%)"]:
                        if col in df.columns:
                            print(f"      {col}: {row[col]}")
        else:
            print("    无数据")
    except Exception as e:
        print(f"    错误: {e}")
    
    # akshare 利润表
    print(f"\n  [akshare 新浪利润表 2025年报]")
    try:
        df2 = ak.stock_financial_report_sina(stock=ts_code, symbol="利润表")
        if df2 is not None and len(df2) > 0:
            date_col = df2.columns[0]
            for idx, row in df2.iterrows():
                date_val = str(row[date_col])
                if "2025" in date_val and "1231" in date_val:
                    print(f"    报表日期: {date_val}")
                    for c in df2.columns[1:8]:
                        v = row[c]
                        if v is not None and str(v).strip() and str(v) != "nan":
                            print(f"      {c}: {v}")
                    break
            else:
                print(f"    未找到2025年报，可用日期:")
                for idx, row in df2.head(5).iterrows():
                    print(f"      {row[date_col]}")
        else:
            print("    无数据")
    except Exception as e:
        print(f"    错误: {e}")

print(f"\n{'='*70}")
print("验证完成")
