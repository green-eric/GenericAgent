#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机抽查5只股票的财务数据准确性
从JSON报告中取5只，对比NeoData API原始数据
"""
import os, re, json, sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

_ND_TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".workbuddy", ".neodata_token")
_ND_ENDPOINT = "https://copilot.tencent.com/agenttool/v1/neodata"

def read_token():
    try:
        with open(_ND_TOKEN_FILE, 'r') as f:
            t = f.read().strip()
            if t: return t
    except: pass
    return ""

token = read_token()
headers = {"Content-Type":"application/json", "Authorization":f"Bearer {token}"}

# Load JSON report
with open('股票分析数据_20260425_225222.json','r',encoding='utf-8') as f:
    report = json.load(f)

# The JSON structure changed - check if it's the old format (list) or new format (dict with stocks key)
if isinstance(report, list):
    stocks_data = report
else:
    stocks_data = report.get('stocks', report)

# Pick 5 random stocks: top 1, middle 2, bottom 2
total = len(stocks_data)
indices = [0, total//4, total//2, total*3//4, total-1]
selected = [(i, stocks_data[i]) for i in indices]

print(f"JSON报告共 {total} 只股票，抽查 {len(selected)} 只\n")

for idx, stock in selected:
    ts_code = stock['ts_code']
    name = stock['name']
    
    print(f"{'='*60}")
    print(f"[{idx+1}/{total}] {name} ({ts_code})")
    print(f"{'='*60}")
    
    # Query API
    query = f"{ts_code} {name} 年报"
    payload = {"query":query, "channel":"neodata", "sub_channel":"workbuddy", "data_type":"api"}
    
    try:
        resp = requests.post(_ND_ENDPOINT, headers=headers, json=payload, timeout=50)
        data = resp.json()
        recalls = data.get("data", {}).get("apiData", {}).get("apiRecall", [])
        full_text = "\n".join(r.get("content", "") for r in recalls)
        
        # Find latest annual block
        annual_header_pat = re.compile(r'统计截止日期为(\d{4})1231的年报')
        blocks = list(annual_header_pat.finditer(full_text))
        
        if not blocks:
            print("  API无年报数据\n")
            continue
        
        # Take the first (latest) annual block
        m = blocks[0]
        year = m.group(1)
        start = m.start()
        next_section = re.search(r'统计截止日期为', full_text[start + 1:])
        end = start + 1 + next_section.start() if next_section else len(full_text)
        block = full_text[start:end]
        
        print(f"  API最新年报: {year}1231")
        print(f"  JSON报告日期: {stock.get('annual_report_date', 'N/A')}")
        print()
        
        # Extract key metrics from API block for comparison
        api_values = {}
        
        # ROE
        roe_m = re.search(r'加权净资产收益率ROE\s*([\d.]+)%', block)
        if roe_m: api_values['ROE'] = float(roe_m.group(1))
        
        # 毛利率
        gm_m = re.search(r'销售毛利率\s*([\d.]+)%', block)
        if gm_m: api_values['毛利率'] = float(gm_m.group(1))
        
        # 净利率
        nm_m = re.search(r'销售净利率\s*([\d.]+)%', block)
        if nm_m: api_values['净利率'] = float(nm_m.group(1))
        
        # 资产负债率
        dr_m = re.search(r'资产负债率\s*([\d.]+)%', block)
        if dr_m: api_values['资产负债率'] = float(dr_m.group(1))
        
        # 营收同比
        ry_m = re.search(r'营业收入同比增长\s*([\d.]+)%', block)
        if ry_m: api_values['营收同比'] = float(ry_m.group(1))
        
        # 净利润同比
        py_m = re.search(r'归母净利润同比增长\s*([\d.]+)%', block)
        if py_m: api_values['净利润同比'] = float(py_m.group(1))
        
        # 净利润 (bare)
        np_m = re.search(r'^净利润\s*([\d.]+)\s*元', block, re.MULTILINE)
        if not np_m:
            np_m = re.search(r'净利润([\d.]+)元', block)
        if np_m: api_values['净利润(元)'] = float(np_m.group(1))
        
        # 扣非净利润
        dp_m = re.search(r'扣非净利润\s*([\d.]+)\s*元', block)
        if not dp_m:
            dp_m = re.search(r'扣非净利润([\d.]+)元', block)
        if dp_m: api_values['扣非净利润(元)'] = float(dp_m.group(1))
        
        # 经营现金流
        ocf_m = re.search(r'经营活动产生的现金流量净额\s*([\d.]+)\s*元', block)
        if not ocf_m:
            ocf_m = re.search(r'经营活动产生的现金流量净额\s*([\d.]+)\s*亿元', block)
            if ocf_m: api_values['经营现金流(亿元)'] = float(ocf_m.group(1))
        else:
            api_values['经营现金流(元)'] = float(ocf_m.group(1))
        
        # Compare
        json_mapping = {
            'ROE': stock.get('annual_roe'),
            '毛利率': stock.get('annual_gross_margin'),
            '净利率': stock.get('annual_net_margin'),
            '资产负债率': stock.get('annual_debt_ratio'),
            '营收同比': stock.get('annual_revenue_yoy'),
            '净利润同比': stock.get('annual_profit_yoy'),
        }
        
        print(f"  {'指标':<12} {'API原始值':>15} {'JSON报告值':>15} {'状态':>6}")
        print(f"  {'-'*52}")
        
        for key in ['ROE', '毛利率', '净利率', '资产负债率', '营收同比', '净利润同比']:
            api_val = api_values.get(key, 'N/A')
            json_val = json_mapping.get(key, 'N/A')
            
            if isinstance(api_val, float) and isinstance(json_val, float):
                match = abs(api_val - json_val) < 0.02
                status = '✓' if match else '✗'
            elif api_val == json_val:
                status = '✓'
            else:
                status = '?'
            
            print(f"  {key:<12} {str(api_val):>15} {str(json_val):>15} {status:>6}")
        
        # Check net profit separately
        api_np = api_values.get('净利润(元)')
        json_np = stock.get('annual_net_profit')
        if api_np and json_np:
            np_match = abs(api_np - json_np) < 1
            print(f"  {'净利润(元)':<12} {api_np:>15.2f} {json_np:>15.2f} {'✓' if np_match else '✗':>6}")
        else:
            print(f"  {'净利润(元)':<12} {str(api_np):>15} {str(json_np):>15} {'N/A':>6}")
        
        # OCF/净利润
        api_ocf = api_values.get('经营现金流(元)')
        json_ocf = stock.get('annual_ocf_abs')
        json_ocf_ratio = stock.get('annual_ocf_to_profit')
        if api_ocf and json_ocf:
            ocf_match = abs(api_ocf - json_ocf) < 1
            print(f"  {'经营现金流':<12} {api_ocf:>15.2f} {json_ocf:>15.2f} {'✓' if ocf_match else '✗':>6}")
        else:
            print(f"  {'经营现金流':<12} {str(api_ocf):>15} {str(json_ocf):>15} {'N/A':>6}")
        
        if json_ocf_ratio:
            print(f"  {'OCF/净利润':<12} {'(计算值)':>15} {json_ocf_ratio:>15.4f}")
        
        print()
        
    except Exception as e:
        print(f"  查询异常: {e}\n")
