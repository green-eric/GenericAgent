#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 NeoData 批量查询新征程853股票池 2024年报净利润增长率"""

import json
import re
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MDc5NzYzNDEsImlhdCI6MTc3NjkzNDIxOCwiYXV0aF90aW1lIjoxNzc2NDQwMzQyLCJqdGkiOiJhZGYzYzFkNi1kN2FlLTQ4ZGItYjg1Mi1lMTI3YjY2MTVjOGMiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJjYWY4Y2NkZC1hNjE4LTQ3MDEtOGVkZS02ZDhkMTNjZjI5MjAiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiNmNlZjhlOTktYTYzYi00NGM1LWE1NjAtNjY4YWMyNTFjN2E5IiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi6Z2Z5rC05rWB5rexIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTMwNjI4ODQyNTMifQ.h0E0KtMPMZG07c0hpbkolsoEnarS0s2P5QgmClNcIIkDFYemp79_iX_uEV4fKArp1jZZDaMfN03y19EDxf-VfTl_DT-u7ZlbGDn1h_tbBvhNoVdR9Z34xC2HU5lAA7wUyFASDSsJNek2rGOkIEHYIQa9rm3WlLsAfZAg594QTwUp_TF-mzuJnfg44GIYHGfVsNszJKlI5caJfyJyd1R52LlvZfK7MJ7EdO_tZNehqO6jekIVIYVynBaO3wRZMikod3K7i-_V7YxKHY_EZW_QMJ0v1JCc4pyDSKLEIZjYPHH9tjTQNCGg3sPIv1joESCGeYGChBBRi4VW5SR8TXCkDQ"

stocks = [
    ("圣邦股份", "300661.SZ"),
    ("光迅科技", "002281.SZ"),
    ("信维通信", "300136.SZ"),
    ("三环集团", "300408.SZ"),
    ("天岳先进", "688234.SH"),
    ("沪电股份", "002463.SZ"),
    ("安克创新", "300866.SZ"),
    ("鼎龙股份", "300054.SZ"),
    ("德业股份", "605117.SH"),
    ("新产业", "300832.SZ"),
    ("长川科技", "300604.SZ"),
    ("华润微", "688396.SH"),
    ("工业富联", "601138.SH"),
    ("伯特利", "603596.SH"),
    ("水晶光电", "002273.SZ"),
    ("华测检测", "300012.SZ"),
    ("石头科技", "688169.SH"),
    ("中际旭创", "300308.SZ"),
    ("思源电气", "002028.SZ"),
    ("药明康德", "603259.SH"),
    ("金山办公", "688111.SH"),
    ("中科创达", "300496.SZ"),
    ("景嘉微", "300474.SZ"),
    ("时代电气", "688187.SH"),
    ("宝信软件", "600845.SH"),
    ("全志科技", "300458.SZ"),
    ("联影医疗", "688271.SH"),
    ("公牛集团", "603195.SH"),
    ("汇顶科技", "603160.SH"),
    ("中国移动", "600941.SH"),
    ("深南电路", "002916.SZ"),
    ("三星电气", "601567.SH"),
    ("中航高科", "600862.SH"),
    ("海康威视", "002415.SZ"),
    ("润和软件", "300339.SZ"),
    ("华大九天", "301269.SZ"),
    ("分众传媒", "002027.SZ"),
    ("宏发股份", "600885.SH"),
    ("萤石网络", "688475.SH"),
    ("北方华创", "002371.SZ"),
    ("中航重机", "600765.SH"),
    ("开立医疗", "300633.SZ"),
    ("软通动力", "301236.SZ"),
    ("沃尔核材", "002130.SZ"),
    ("恒立液压", "601100.SH"),
    ("士兰微", "600460.SH"),
    ("浙江鼎力", "603338.SH"),
    ("鱼跃医疗", "002223.SZ"),
    ("鹏鼎控股", "002938.SZ"),
    ("扬杰科技", "300373.SZ"),
    ("中科软", "603927.SH"),
    ("思特威-W", "688213.SH"),
    ("科大讯飞", "002230.SZ"),
    ("拓邦股份", "002139.SZ"),
    ("亿联网络", "300628.SZ"),
    ("生益科技", "600183.SH"),
    ("数字政通", "300075.SZ"),
    ("恒生电子", "600570.SH"),
    ("紫光国微", "002049.SZ"),
    ("雅克科技", "002409.SZ"),
    ("格科微", "688728.SH"),
    ("中微公司", "688012.SH"),
    ("惠泰医疗", "688617.SH"),
    ("中航光电", "002179.SZ"),
    ("传音控股", "688036.SH"),
    ("安集科技", "688019.SH"),
    ("航天信息", "600271.SH"),
    ("深信服", "300454.SZ"),
    ("大华股份", "002236.SZ"),
    ("顺络电子", "002138.SZ"),
    ("阳光电源", "300274.SZ"),
    ("豪威集团", "603501.SH"),
    ("万兴科技", "300624.SZ"),
    ("中控技术", "688777.SH"),
    ("芯源微", "688037.SH"),
    ("中天科技", "600522.SH"),
    ("澜起科技", "688008.SH"),
    ("柏楚电子", "688188.SH"),
    ("汇川技术", "300124.SZ"),
    ("智飞生物", "300122.SZ"),
    ("云赛智联", "600602.SH"),
    ("国科微", "300672.SZ"),
    ("领益智造", "002600.SZ"),
    ("中科飞测", "688361.SH"),
    ("江丰电子", "300666.SZ"),
    ("特宝生物", "688278.SH"),
    ("晶盛机电", "300316.SZ"),
    ("精测电子", "300567.SZ"),
    ("电连技术", "300679.SZ"),
    ("航天电器", "002025.SZ"),
    ("拓荆科技", "688072.SH"),
    ("华海清科", "688120.SH"),
    ("法拉电子", "600563.SH"),
    ("铂科新材", "300811.SZ"),
    ("福晶科技", "002222.SZ"),
    ("天孚通信", "300394.SZ"),
    ("菲利华", "300395.SZ"),
    ("卓胜微", "300782.SZ"),
    ("爱玛科技", "603529.SH"),
    ("赛微电子", "300456.SZ"),
]

URL = "https://copilot.tencent.com/agenttool/v1/neodata"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

def parse_net_profit(content_text):
    """从 NeoData 返回的文本内容中解析净利润数值（元）"""
    # 匹配"归母净利润XXXXX元"或"净利润XXXXX元"
    patterns = [
        r'归母净利润([+-]?[\d,\.]+)元',
        r'净利润.*?([+-]?[\d,\.]+)元',
    ]
    for p in patterns:
        m = re.search(p, content_text)
        if m:
            val_str = m.group(1).replace(',', '')
            try:
                return float(val_str)
            except:
                pass
    return None

def query_stock_income(name, ts_code):
    """通过 NeoData 查询某股票2024年报和2023年报的净利润，返回 (net2024, net2023)"""
    payload = {
        "query": f"{name}({ts_code}) 2024年年报和2023年年报净利润归母",
        "channel": "neodata",
        "sub_channel": "workbuddy",
        "data_type": "api"
    }
    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=30)
        d = r.json()
        if d.get("code") != "200":
            return None, None, str(d.get("msg", ""))
        
        api_data = d.get("data", {}).get("apiData", {})
        recall_list = api_data.get("apiRecall", [])
        
        # 找利润表相关条目
        profits = {}
        for item in recall_list:
            desc = item.get("desc", "") + item.get("type", "")
            content = item.get("content", "")
            
            # 找年份
            year_match = re.search(r'截止日期为(\d{8})', content)
            if not year_match:
                continue
            period = year_match.group(1)
            year = period[:4]
            
            # 只取全年年报（末尾为1231）
            if not period.endswith("1231"):
                continue
            # 只取合并报表（非单季）
            if "单季" in content or "Q4" in content:
                continue
            
            # 解析归母净利润
            net = parse_net_profit(content)
            if net is not None and year not in profits:
                profits[year] = net
        
        net2024 = profits.get("2024")
        net2023 = profits.get("2023")
        return net2024, net2023, ""
    except Exception as e:
        return None, None, str(e)

results = []
total = len(stocks)
print(f"开始查询 {total} 只股票的2024/2023年报净利润...")
print("-" * 70)

for i, (name, ts_code) in enumerate(stocks):
    net2024, net2023, err = query_stock_income(name, ts_code)
    
    if net2024 is not None and net2023 is not None and net2023 != 0:
        yoy = (net2024 - net2023) / abs(net2023) * 100
        results.append({
            "name": name,
            "ts_code": ts_code,
            "net2024": net2024,
            "net2023": net2023,
            "netprofit_yoy": round(yoy, 2)
        })
        flag = " ***" if yoy > 50 else ""
        print(f"[{i+1:3d}/{total}] {name}({ts_code}): 2024={net2024/1e8:.2f}亿 2023={net2023/1e8:.2f}亿 增长={yoy:.1f}%{flag}")
    elif net2024 is not None and net2023 is not None and net2023 == 0:
        print(f"[{i+1:3d}/{total}] {name}({ts_code}): 2023净利润为0，无法计算增长率")
        results.append({"name": name, "ts_code": ts_code, "net2024": net2024, "net2023": net2023, "netprofit_yoy": None})
    else:
        print(f"[{i+1:3d}/{total}] {name}({ts_code}): 解析失败 net2024={net2024} net2023={net2023} {err}")
        results.append({"name": name, "ts_code": ts_code, "net2024": net2024, "net2023": net2023, "netprofit_yoy": None})
    
    # 避免请求过于频繁
    time.sleep(0.4)

# 筛选 > 50%
high_growth = [r for r in results if r.get("netprofit_yoy") is not None and r["netprofit_yoy"] > 50]
high_growth.sort(key=lambda x: x["netprofit_yoy"], reverse=True)

print("\n" + "=" * 70)
print(f"2024年报净利润增长率 > 50% 的股票，共 {len(high_growth)} 只：")
print("=" * 70)
print(f"{'名称':<10} {'代码':<13} {'2024净利润(亿)':>14} {'2023净利润(亿)':>14} {'增长率':>8}")
print("-" * 70)
for r in high_growth:
    n = r["name"]
    c = r["ts_code"]
    v24 = r["net2024"] / 1e8 if r["net2024"] else 0
    v23 = r["net2023"] / 1e8 if r["net2023"] else 0
    yoy = r["netprofit_yoy"]
    print(f"{n:<10} {c:<13} {v24:>14.2f} {v23:>14.2f} {yoy:>7.1f}%")

# 保存结果
with open("neodata_growth_result.json", "w", encoding="utf-8") as f:
    json.dump({"high_growth": high_growth, "all": results}, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到 neodata_growth_result.json")
