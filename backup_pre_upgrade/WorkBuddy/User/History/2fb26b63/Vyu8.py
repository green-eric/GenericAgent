"""Check scores of all stocks"""
import json
import os

# Find the latest scores file
files = [f for f in os.listdir(r'd:\Project\QAScorer') if f.startswith('综合评分_') and f.endswith('.xlsx')]
if not files:
    print("No Excel file found")
    exit()

latest = sorted(files)[-1]
print(f"Reading: {latest}")

import openpyxl
wb = openpyxl.load_workbook(os.path.join(r'd:\Project\QAScorer', latest))
ws = wb.active

print(f"\n{'代码':<12} {'名称':<10} {'行业':<12} {'总分':>6} {'等级':>4} {'盈利':>6} {'成长':>6} {'现金流':>6} {'ROE':>8} {'毛利率':>8} {'净利率':>8}")
print("-" * 100)

for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        break
    code, name, industry, total, grade, profit, growth, cfsafe = row[:8]
    roe = row[8] if len(row) > 8 else None
    gross = row[9] if len(row) > 9 else None
    net = row[10] if len(row) > 10 else None
    total_s = f"{total:>6}" if total is not None else "  None"
    profit_s = f"{profit:>6}" if profit is not None else "  None"
    growth_s = f"{growth:>6}" if growth is not None else "  None"
    cfsafe_s = f"{cfsafe:>6}" if cfsafe is not None else "  None"
    roe_s = f"{roe:>8}" if roe is not None else "    None"
    gross_s = f"{gross:>8}" if gross is not None else "    None"
    net_s = f"{net:>8}" if net is not None else "    None"
    print(f"{str(code):<12} {str(name):<10} {str(industry):<12} {total_s} {str(grade):>4} {profit_s} {growth_s} {cfsafe_s} {roe_s} {gross_s} {net_s}")
