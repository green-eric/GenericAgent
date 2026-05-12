#!/usr/bin/env python3
"""生成全A股股票池文件 - 多数据源尝试"""
import sys
sys.path.insert(0, r'd:\Project\ScoreSys')

output = r'd:\Project\ScoreSys\stock_pool_all.txt'

# 方案1: AkShare stock_info_a_code_name（轻量级，只拉代码和名称）
print("[方案1] 尝试 AkShare stock_info_a_code_name...")
try:
    import akshare as ak
    df = ak.stock_info_a_code_name()
    print(f"  获取到 {len(df)} 只")
    print(f"  列名: {list(df.columns)}")
    # 过滤ST和退市
    mask_st = df['name'].str.contains('ST|退', na=False)
    df_clean = df[~mask_st]
    # 只保留沪深主板+创业板+科创板
    mask_board = df_clean['code'].str.match(r'^(6|0|3)\d{5}$')
    df_final = df_clean[mask_board]
    print(f"  过滤后: {len(df_final)} 只")
    with open(output, 'w', encoding='utf-8') as f:
        for _, row in df_final.iterrows():
            f.write(f"{row['code']} {row['name']}\n")
    print(f"  ✅ 已写入 {output}, 共 {len(df_final)} 只")
    sys.exit(0)
except Exception as e:
    print(f"  ❌ 失败: [{type(e).__name__}: {e}]")

# 方案2: AkShare stock_zh_a_spot_em（全市场行情）
print("[方案2] 尝试 AkShare stock_zh_a_spot_em...")
try:
    import akshare as ak
    df = ak.stock_zh_a_spot_em()
    print(f"  获取到 {len(df)} 只")
    mask_st = df['名称'].str.contains('ST|退', na=False)
    df_clean = df[~mask_st]
    mask_board = df_clean['代码'].str.match(r'^(6|0|3)\d{5}$')
    df_final = df_clean[mask_board]
    print(f"  过滤后: {len(df_final)} 只")
    with open(output, 'w', encoding='utf-8') as f:
        for _, row in df_final.iterrows():
            f.write(f"{row['代码']} {row['名称']}\n")
    print(f"  ✅ 已写入 {output}, 共 {len(df_final)} 只")
    sys.exit(0)
except Exception as e:
    print(f"  ❌ 失败: [{type(e).__name__}: {e}]")

# 方案3: westock-data search 批量
print("[方案3] 尝试 westock-data board 行业板块...")
try:
    import subprocess
    r = subprocess.run(
        'npx --yes westock-data-skillhub@latest board',
        shell=True, capture_output=True, timeout=30
    )
    print(f"  返回码: {r.returncode}")
    print(f"  输出前200: {r.stdout[:200]}")
except Exception as e:
    print(f"  ❌ 失败: [{type(e).__name__}: {e}]")

print("所有方案均失败，无法生成股票池")
