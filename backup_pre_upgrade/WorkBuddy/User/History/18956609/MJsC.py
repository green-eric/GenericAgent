#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试结构化 API 获取年报财务指标"""

import json, os, re, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN_FILE = Path.home() / ".workbuddy" / ".neodata_token"
FINANCE_API = "https://www.codebuddy.cn/v2/tool/financedata"

def read_token():
    try:
        return TOKEN_FILE.read_text().strip()
    except:
        return None

def call_finance_api(api_name, params, fields=""):
    """调用结构化金融数据 API"""
    import urllib.request
    token = read_token()
    if not token:
        print("ERROR: No token found")
        return None
    
    body = json.dumps({"api_name": api_name, "params": params, "fields": fields}).encode()
    req = urllib.request.Request(
        FINANCE_API,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        raw = resp.read().decode('utf-8')
        # 清理 PowerShell CLIXML
        raw = re.sub(r'#< CLIXML\r?\n?', '', raw)
        raw = re.sub(r'<Objs[\s\S]*?</Objs>', '', raw)
        raw = raw.strip()
        return json.loads(raw)
    except Exception as e:
        print(f"API call failed: {e}")
        return None

def test_fina_indicator(ts_code, period):
    """测试财务指标接口"""
    print(f"\n=== fina_indicator: {ts_code} @ {period} ===")
    result = call_finance_api("fina_indicator", {"ts_code": ts_code, "period": period})
    if not result:
        print("  FAILED")
        return None
    print(f"  code: {result.get('code')}")
    if result.get('code') == 0:
        data = result.get('data', {})
        fields = data.get('fields', [])
        items = data.get('items', [])
        print(f"  fields: {fields}")
        for item in items:
            print(f"  values: {item}")
            # 构建字段映射
            row = dict(zip(fields, item))
            print(f"  映射: {json.dumps(row, ensure_ascii=False, default=str)}")
    else:
        print(f"  msg: {result.get('msg')}")
    return result

def test_income(ts_code, period):
    """测试利润表接口"""
    print(f"\n=== income: {ts_code} @ {period} ===")
    result = call_finance_api("income", {"ts_code": ts_code, "period": period})
    if not result:
        print("  FAILED")
        return None
    print(f"  code: {result.get('code')}")
    if result.get('code') == 0:
        data = result.get('data', {})
        fields = data.get('fields', [])
        items = data.get('items', [])
        print(f"  fields: {fields}")
        for item in items:
            row = dict(zip(fields, item))
            # 只打印关键字段
            key_fields = ['end_date', 'total_revenue', 'revenue', 'operate_profit', 'total_profit', 'n_income', 'n_income_attr_p', 'basic_eps']
            for k in key_fields:
                if k in row:
                    print(f"    {k}: {row[k]}")
    else:
        print(f"  msg: {result.get('msg')}")
    return result

def test_cashflow(ts_code, period):
    """测试现金流量表接口"""
    print(f"\n=== cashflow: {ts_code} @ {period} ===")
    result = call_finance_api("cashflow", {"ts_code": ts_code, "period": period})
    if not result:
        print("  FAILED")
        return None
    print(f"  code: {result.get('code')}")
    if result.get('code') == 0:
        data = result.get('data', {})
        fields = data.get('fields', [])
        items = data.get('items', [])
        for item in items:
            row = dict(zip(fields, item))
            key_fields = ['end_date', 'net_profit', 'n_cashflow_act']
            for k in key_fields:
                if k in row:
                    print(f"    {k}: {row[k]}")
    else:
        print(f"  msg: {result.get('msg')}")
    return result

def test_balancesheet(ts_code, period):
    """测试资产负债表接口"""
    print(f"\n=== balancesheet: {ts_code} @ {period} ===")
    result = call_finance_api("balancesheet", {"ts_code": ts_code, "period": period})
    if not result:
        print("  FAILED")
        return None
    print(f"  code: {result.get('code')}")
    if result.get('code') == 0:
        data = result.get('data', {})
        fields = data.get('fields', [])
        items = data.get('items', [])
        for item in items:
            row = dict(zip(fields, item))
            key_fields = ['end_date', 'total_assets', 'total_liab', 'total_hldr_eqy_exc_min_int']
            for k in key_fields:
                if k in row:
                    print(f"    {k}: {row[k]}")
    else:
        print(f"  msg: {result.get('msg')}")
    return result

if __name__ == "__main__":
    ts_code = "300308.SZ"
    period = "20251231"
    
    print("=" * 60)
    print("结构化 API 测试 - 中际旭创 300308.SZ 2025年报")
    print("=" * 60)
    
    # 1. 财务指标
    test_fina_indicator(ts_code, period)
    
    # 2. 利润表
    test_income(ts_code, period)
    
    # 3. 现金流量表
    test_cashflow(ts_code, period)
    
    # 4. 资产负债表
    test_balancesheet(ts_code, period)
    
    print("\n" + "=" * 60)
    print("测试完成")
