import sys, os, re
sys.path.insert(0, r'D:\Project\QAScorer')
from qa_scorer import load_token, run_neodata, _extract_all_quarterly_blocks

token = load_token()
# 取一只股票看完整的季报原文
text = run_neodata("600338.SH 西藏珠峰 最新季报", token)
blocks = _extract_all_quarterly_blocks(text)
print(f"共 {len(blocks)} 个季度段落")
for year, q_date, block in blocks:
    print(f"\n=== {year}{q_date} ===")
    print(block[:2000])
    print("...")
