#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试修复后的解析器对 300308.SZ 的解析结果"""
import os, json, re, subprocess, sys

os.environ['PYTHONIOENCODING'] = 'utf-8'

# 导入修复后的解析器
sys.path.insert(0, r'C:\Users\green\WorkBuddy\20260424203734\workplace')

# 先获取 API 原始数据
cmd = [
    sys.executable, '-X', 'utf8',
    r'C:\Users\green\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts\query.py',
    '--query', '300308.SZ 中际旭创 年报',
    '--data-type', 'api'
]
result = subprocess.run(cmd, capture_output=True)
raw = result.stdout.decode('utf-8', errors='replace')
raw = re.sub(r'#< CLIXML\r?\n?', '', raw)
raw = re.sub(r'<Objs[\s\S]*?</Objs>', '', raw)
m = re.search(r'\{[\s\S]*\}', raw)
data = json.loads(m.group())
recalls = data['data']['apiData']['apiRecall']
all_content = "\n".join(r.get("content", "") for r in recalls)

# 用修复后的解析器
from stock_analyzer import FinancialReportParser, parse_financial_all

print("=" * 60)
print("【修复后】parse_financial_all 解析 300308.SZ 结果：")
print("=" * 60)

res = parse_financial_all(all_content)

print("年报日期: {}".format(res.get("annual_report_date")))
print("加权ROE(%): {}".format(res.get("annual_roe")))
print("毛利率(%): {}".format(res.get("annual_gross_margin")))
print("净利率(%): {}".format(res.get("annual_net_margin")))
print("营收同比(%): {}".format(res.get("annual_revenue_yoy")))
print("净利润同比(%): {}".format(res.get("annual_profit_yoy")))
print("资产负债率(%): {}".format(res.get("annual_debt_ratio")))
print("净利润(元): {}".format(res.get("annual_net_profit")))
print("OCF(元): {}".format(res.get("annual_ocf_abs")))
print("OCF/净利润: {}".format(res.get("annual_ocf_to_profit")))

print()
print("=" * 60)
print("【预期正确值】来自 API 年报段落：")
print("  加权ROE: 43.84%")
print("  毛利率: 42.04%（年报）而非 46.06%（Q1）")
print("  净利率: 30.28%（年报）而非 29.41%（Q1）")
print("  营收同比: 60.25%")
print("  净利润同比: 108.78%（年报）而非 262.28%（Q1）")
print("  资产负债率: 30.18%")
print("  OCF/净利润: ~1.009（108.96亿/107.97亿）而非 ~0")
print("=" * 60)

# 验证
print()
errors = 0

# 检查毛利率（应该是年报的 42.04，不是 Q1 的 46.06）
gm = res.get("annual_gross_margin")
if gm is not None:
    if abs(gm - 42.04) < 0.5:
        print("[OK] 毛利率 {:.2f}% 接近年报值 42.04%".format(gm))
    elif abs(gm - 46.06) < 0.5:
        print("[FAIL] 毛利率 {:.2f}% 仍是 Q1 值 46.06%，修复未生效！".format(gm))
        errors += 1
    else:
        print("[WARN] 毛利率 {:.2f}% 与预期不符".format(gm))

# 检查净利率（应该是年报的 30.28，不是 Q1 的 29.41）
nm = res.get("annual_net_margin")
if nm is not None:
    if abs(nm - 30.28) < 0.5:
        print("[OK] 净利率 {:.2f}% 接近年报值 30.28%".format(nm))
    elif abs(nm - 29.41) < 0.5:
        print("[FAIL] 净利率 {:.2f}% 仍是 Q1 值 29.41%，修复未生效！".format(nm))
        errors += 1
    else:
        print("[WARN] 净利率 {:.2f}% 与预期不符".format(nm))

# 检查净利润同比（应该是年报的 108.78，不是 Q1 的 262.28）
py = res.get("annual_profit_yoy")
if py is not None:
    if abs(py - 108.78) < 1.0:
        print("[OK] 净利润同比 {:.2f}% 接近年报值 108.78%".format(py))
    elif abs(py - 262.28) < 1.0:
        print("[FAIL] 净利润同比 {:.2f}% 仍是 Q1 值 262.28%，修复未生效！".format(py))
        errors += 1
    else:
        print("[WARN] 净利润同比 {:.2f}% 与预期不符".format(py))

# 检查 OCF/净利润（应该接近 1.0，不是 ~0）
ocf_ratio = res.get("annual_ocf_to_profit")
if ocf_ratio is not None:
    if ocf_ratio > 0.5:
        print("[OK] OCF/净利润 {:.4f} 正常（接近 1.0）".format(ocf_ratio))
    else:
        print("[FAIL] OCF/净利润 {:.4e} 仍接近 0，修复未生效！".format(ocf_ratio))
        errors += 1
else:
    print("[FAIL] OCF/净利润为 None")
    errors += 1

print()
if errors == 0:
    print("===== 全部验证通过！=====")
else:
    print("===== 有 {} 项验证失败 =====".format(errors))
