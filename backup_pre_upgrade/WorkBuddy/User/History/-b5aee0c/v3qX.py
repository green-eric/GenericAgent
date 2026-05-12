# -*- coding: utf-8 -*-
"""最终验证：检查Excel中鼎泰高科和金海通的每项指标百分位是否与Excel输出匹配"""
import sys, io, openpyxl
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

wb = openpyxl.load_workbook(r'd:\Project\QAScorer\综合评分_20260426_202924.xlsx')
ws = wb.active

all_stocks = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        break
    all_stocks.append({
        'ts_code': row[0], 'name': row[1],
        'roe': row[8], 'gross_margin': row[9], 'net_margin': row[10],
        'revenue_yoy': row[11], 'profit_yoy': row[12],
        'ocf_to_profit': row[13], 'debt_ratio': row[14],
        'total_score': row[3], 'profit_score': row[5],
        'growth_score': row[6], 'cfsafe_score': row[7],
    })

# 有ROE数据的8只股票
pool8 = [s for s in all_stocks if s['roe'] is not None]

# 有OCF数据的股票
pool_ocf = [s for s in all_stocks if s['ocf_to_profit'] is not None]
pool_debt = [s for s in all_stocks if s['debt_ratio'] is not None]

print(f"有ROE数据: {len(pool8)} 只")
print(f"有OCF数据: {len(pool_ocf)} 只")
print(f"有负债率数据: {len(pool_debt)} 只")

# 打印OCF/利润的排序
print("\nOCF/利润排序（升序）:")
sorted_ocf = sorted(pool_ocf, key=lambda s: s['ocf_to_profit'])
for i, s in enumerate(sorted_ocf):
    print(f"  [{i}] {s['ts_code']} {s['name']} OCF={s['ocf_to_profit']}")

# 打印负债率的排序（降序，越低越好）
print("\n负债率排序（降序，越低分越高）:")
sorted_debt = sorted(pool_debt, key=lambda s: s['debt_ratio'], reverse=True)
for i, s in enumerate(sorted_debt):
    print(f"  [{i}] {s['ts_code']} {s['name']} 负债率={s['debt_ratio']}")

# 反推Excel的百分位值
print("\n=== 反推Excel的百分位值 ===")
for code in ['301377.SZ', '603061.SH']:
    target = next(s for s in all_stocks if s['ts_code'] == code)
    print(f"\n{target['name']} ({code}):")
    
    # 盈利 = roe_s*0.4 + gross_s*0.3 + net_s*0.3 = profit_score
    # 成长 = rev_s*0.4 + prof_s*0.6 = growth_score
    # 现金流 = ocf_s*0.4 + debt_s*0.6 = cfsafe_score
    
    profit_score = target['profit_score']
    growth_score = target['growth_score']
    cfsafe_score = target['cfsafe_score']
    
    # 成长：rev_yoy=None -> rev_s=0, prof_yoy=259/221.54 -> prof_s=100
    # growth = 0*0.4 + 100*0.6 = 60 ✓
    print(f"  成长={growth_score}: rev_s=0 (None), prof_s=100 -> 0*0.4+100*0.6=60 ✓")
    
    # 盈利：需要 roe_s, gross_s, net_s
    # profit = roe_s*0.4 + gross_s*0.3 + net_s*0.3
    # 鼎泰高科: 94.29 = roe_s*0.4 + gross_s*0.3 + net_s*0.3
    # 金海通: 72.86 = roe_s*0.4 + gross_s*0.3 + net_s*0.3
    
    # 现金流：需要 ocf_s, debt_s
    # cfsafe = ocf_s*0.4 + debt_s*0.6
    # 鼎泰高科: 62.86 = ocf_s*0.4 + debt_s*0.6
    # 金海通: 77.14 = ocf_s*0.4 + debt_s*0.6
    
    # 反推鼎泰高科现金流：
    # 如果 debt_s = 85.71 (我的计算), 则 ocf_s*0.4 = 62.86 - 85.71*0.6 = 62.86 - 51.43 = 11.43
    # ocf_s = 28.57
    # 如果 ocf_s = 57.14 (我的计算), 则 debt_s*0.6 = 62.86 - 57.14*0.4 = 62.86 - 22.86 = 40.00
    # debt_s = 66.67
    
    print(f"  现金流={cfsafe_score}:")
    print(f"    如果 ocf_s=57.14, 则 debt_s={(cfsafe_score - 57.14*0.4)/0.6:.2f}")
    print(f"    如果 ocf_s=47.06, 则 debt_s={(cfsafe_score - 47.06*0.4)/0.6:.2f}")
    print(f"    如果 ocf_s=28.57, 则 debt_s={(cfsafe_score - 28.57*0.4)/0.6:.2f}")
    print(f"    如果 debt_s=85.71, 则 ocf_s={(cfsafe_score - 85.71*0.6)/0.4:.2f}")
    print(f"    如果 debt_s=66.67, 则 ocf_s={(cfsafe_score - 66.67*0.6)/0.4:.2f}")
    print(f"    如果 debt_s=100.0, 则 ocf_s={(cfsafe_score - 100.0*0.6)/0.4:.2f}")
    
    print(f"  盈利={profit_score}:")
    print(f"    如果 roe_s=71.43, gross_s=100, net_s=100: {71.43*0.4 + 100*0.3 + 100*0.3:.2f}")
    print(f"    如果 roe_s=85.71, gross_s=100, net_s=100: {85.71*0.4 + 100*0.3 + 100*0.3:.2f}")
    print(f"    如果 roe_s=100, gross_s=100, net_s=100: {100*0.4 + 100*0.3 + 100*0.3:.2f}")
