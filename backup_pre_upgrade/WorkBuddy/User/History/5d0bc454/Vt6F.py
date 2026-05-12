#!/usr/bin/env python3
"""生成全A股股票池文件"""
import akshare as ak
import pandas as pd

# 拉全市场A股实时行情（含代码和名称）
print("正在拉取全市场A股列表...")
df = ak.stock_zh_a_spot_em()
print(f"全市场股票总数: {len(df)}")

# 过滤ST和退市
mask_st = df['名称'].str.contains('ST|退', na=False)
df_clean = df[~mask_st]
print(f"过滤ST/退市后: {len(df_clean)}")

# 只保留沪深主板+创业板+科创板（6/0/3开头），过滤北交所(8/4开头)
mask_board = df_clean['代码'].str.match(r'^(6|0|3)\d{5}$')
df_final = df_clean[mask_board]
print(f"过滤北交所后: {len(df_final)}")

# 写入文件
output = r'd:\Project\ScoreSys\stock_pool_all.txt'
with open(output, 'w', encoding='utf-8') as f:
    for _, row in df_final.iterrows():
        f.write(f"{row['代码']} {row['名称']}\n")
print(f"已写入 {output}, 共 {len(df_final)} 只")
