# -*- coding: utf-8 -*-
"""对比 Excel 和数据库中的数据是否一致"""
import sys, io, sqlite3, openpyxl
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 读取 Excel
wb = openpyxl.load_workbook(r'd:\Project\QAScorer\综合评分_20260426_202924.xlsx')
ws = wb.active

excel_data = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        break
    excel_data[row[0]] = {
        'name': row[1], 'total': row[3], 'grade': row[4],
        'profit': row[5], 'growth': row[6], 'cfsafe': row[7],
        'roe': row[8], 'gross': row[9], 'net': row[10],
        'rev_yoy': row[11], 'prof_yoy': row[12],
        'ocf': row[13], 'debt': row[14],
    }

# 读取数据库
conn = sqlite3.connect(r'd:\Project\QAScorer\stock_cache.db')
conn.row_factory = sqlite3.Row

db_annual = {}
cur = conn.execute("SELECT * FROM financial_reports WHERE report_type='annual' AND fetch_success=1")
for row in cur.fetchall():
    if row["ts_code"] not in db_annual:
        db_annual[row["ts_code"]] = dict(row)

db_quarterly = {}
cur = conn.execute("SELECT * FROM financial_reports WHERE report_type='quarterly' AND fetch_success=1")
for row in cur.fetchall():
    if row["ts_code"] not in db_quarterly:
        db_quarterly[row["ts_code"]] = dict(row)

print("对比 Excel vs 数据库:")
print(f"{'代码':<12} {'名称':<8} {'字段':<10} {'Excel':>10} {'数据库':>10} {'一致':>6}")
print("-" * 70)

for code, ed in sorted(excel_data.items()):
    arow = db_annual.get(code, {})
    qrow = db_quarterly.get(code, {})
    
    fields = [
        ('ROE', ed['roe'], arow.get('roe')),
        ('毛利率', ed['gross'], qrow.get('gross_margin')),
        ('净利率', ed['net'], qrow.get('net_margin')),
        ('营收同比', ed['rev_yoy'], qrow.get('revenue_yoy')),
        ('利润同比', ed['prof_yoy'], qrow.get('profit_yoy')),
        ('OCF/利润', ed['ocf'], arow.get('ocf_to_profit')),
        ('负债率', ed['debt'], arow.get('debt_ratio')),
    ]
    
    for name, excel_val, db_val in fields:
        if excel_val is None and db_val is None:
            continue
        if excel_val is not None and db_val is not None:
            match = abs(float(excel_val) - float(db_val)) < 0.01
        else:
            match = False
        if not match:
            print(f"{code:<12} {ed['name']:<8} {name:<10} {str(excel_val):>10} {str(db_val):>10} {'NO':>6}")

conn.close()
