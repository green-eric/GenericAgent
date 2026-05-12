#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('股票分析数据_20260425_225222.json','r',encoding='utf-8') as f:
    data = json.load(f)

null_net = [r for r in data if r.get('annual_net_profit') is None and r.get('annual_deducted_profit') is not None]
print(f'annual_net_profit为null但有deducted_profit的股票数: {len(null_net)}')

has_date = sum(1 for r in data if r.get('annual_report_date'))
no_date = sum(1 for r in data if not r.get('annual_report_date'))
print(f'有annual_report_date: {has_date}')
print(f'无annual_report_date: {no_date}')

null_ocf = [r for r in data if r.get('annual_ocf_to_profit') is None and r.get('annual_ocf_abs') is not None]
print(f'annual_ocf_to_profit为null但有ocf_abs的股票数: {len(null_ocf)}')

# 有net_profit的例子
for r in data[:100]:
    if r.get('annual_net_profit') is not None:
        print(f'有net_profit: {r["name"]}({r["ts_code"]}): net_profit={r["annual_net_profit"]}, ocf={r.get("annual_ocf_abs")}, ocf_to_profit={r.get("annual_ocf_to_profit")}')
        break

# 看null_net的前5个
print('\n--- annual_net_profit为null的前5只 ---')
for r in null_net[:5]:
    print(f'{r["name"]}({r["ts_code"]}): deducted={r.get("annual_deducted_profit")}, ocf={r.get("annual_ocf_abs")}, report_date={r.get("annual_report_date")}')

# 统计有report_date的
print('\n--- 有report_date的前5只 ---')
count = 0
for r in data:
    if r.get('annual_report_date'):
        print(f'{r["name"]}({r["ts_code"]}): report_date={r["annual_report_date"]}')
        count += 1
        if count >= 5:
            break
