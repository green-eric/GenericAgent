#!/usr/bin/env python3
"""冒烟测试：用10只股票验证全链路"""
import sys, os
sys.path.insert(0, r'd:\Project\ScoreSys')
os.chdir(r'd:\Project\ScoreSys')

from datetime import datetime
from main import batch_evaluate, save_to_excel

# 取stock_pool前10只
with open('stock_pool.txt', 'r', encoding='utf-8') as f:
    symbols = [line.strip().split()[0] for line in f if line.strip() and not line.startswith('#')][:10]

print(f"冒烟测试：{len(symbols)} 只股票")
print(f"股票列表: {symbols}")

eval_date = datetime.today()
results = batch_evaluate(symbols, eval_date, mock=False, db=None, workers=5, rate_limit=0.1)

if results:
    save_to_excel(results, 'smoke_test.xlsx')
    print(f"\n成功: {len(results)} 只")
else:
    print("\n无结果！")
