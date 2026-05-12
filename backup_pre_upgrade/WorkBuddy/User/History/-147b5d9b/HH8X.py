#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量查询新征程853股票池 2024年报净利润增长率"""

import json
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MDc5NzYzNDEsImlhdCI6MTc3NjkzNDIxOCwiYXV0aF90aW1lIjoxNzc2NDQwMzQyLCJqdGkiOiJhZGYzYzFkNi1kN2FlLTQ4ZGItYjg1Mi1lMTI3YjY2MTVjOGMiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJjYWY4Y2NkZC1hNjE4LTQ3MDEtOGVkZS02ZDhkMTNjZjI5MjAiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiNmNlZjhlOTktYTYzYi00NGM1LWE1NjAtNjY4YWMyNTFjN2E5IiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi6Z2Z5rC05rWB5rexIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTMwNjI4ODQyNTMifQ.h0E0KtMPMZG07c0hpbkolsoEnarS0s2P5QgmClNcIIkDFYemp79_iX_uEV4fKArp1jZZDaMfN03y19EDxf-VfTl_DT-u7ZlbGDn1h_tbBvhNoVdR9Z34xC2HU5lAA7wUyFASDSsJNek2rGOkIEHYIQa9rm3WlLsAfZAg594QTwUp_TF-mzuJnfg44GIYHGfVsNszJKlI5caJfyJyd1R52LlvZfK7MJ7EdO_tZNehqO6jekIVIYVynBaO3wRZMikod3K7i-_V7YxKHY_EZW_QMJ0v1JCc4pyDSKLEIZjYPHH9tjTQNCGg3sPIv1joESCGeYGChBBRi4VW5SR8TXCkDQ"

# 股票列表
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

URL = "https://www.codebuddy.cn/v2/tool/financedata"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

results = []
errors = []

total = len(stocks)
print(f"开始查询 {total} 只股票的2024年报(20241231)净利润增长率...")

for i, (name, ts_code) in enumerate(stocks):
    payload = {
        "api_name": "fina_indicator",
        "params": {
            "ts_code": ts_code,
            "period": "20241231"
        },
        "fields": "ts_code,ann_date,end_date,netprofit_yoy,dt_netprofit_yoy,tr_yoy,or_yoy,roe"
    }
    try:
        resp = requests.post(URL, headers=HEADERS, json=payload, timeout=15)
        data = resp.json()
        if data.get("code") == 0 and data.get("data") and data["data"].get("items"):
            fields = data["data"]["fields"]
            row = data["data"]["items"][0]
            row_dict = dict(zip(fields, row))
            row_dict["name"] = name
            results.append(row_dict)
            yoy = row_dict.get("netprofit_yoy")
            print(f"[{i+1:3d}/{total}] {name}({ts_code}): 净利润YoY={yoy}%")
        else:
            msg = data.get("msg", "无数据")
            print(f"[{i+1:3d}/{total}] {name}({ts_code}): {msg}")
            errors.append((name, ts_code, msg))
    except Exception as e:
        print(f"[{i+1:3d}/{total}] {name}({ts_code}): ERR {e}")
        errors.append((name, ts_code, str(e)))
    
    if (i + 1) % 10 == 0:
        time.sleep(0.3)

# 筛选 > 50%
high_growth = []
for r in results:
    yoy = r.get("netprofit_yoy")
    if yoy is not None:
        try:
            if float(yoy) > 50:
                high_growth.append(r)
        except:
            pass

high_growth.sort(key=lambda x: float(x.get("netprofit_yoy", 0)), reverse=True)

print("\n" + "=" * 80)
print(f"2024年报净利润增长率 > 50% 的股票，共 {len(high_growth)} 只：")
print("=" * 80)
header = f"{'名称':<10} {'代码':<12} {'净利润增长%':>12} {'扣非净利润增长%':>15} {'营收增长%':>10} {'ROE%':>8}"
print(header)
print("-" * 80)
for r in high_growth:
    n = r.get("name","")
    c = r.get("ts_code","")
    yoy   = r.get("netprofit_yoy")
    dt    = r.get("dt_netprofit_yoy")
    tr    = r.get("tr_yoy")
    roe   = r.get("roe")
    def fmt(v):
        return f"{float(v):.1f}" if v is not None else "N/A"
    print(f"{n:<10} {c:<12} {fmt(yoy):>12} {fmt(dt):>15} {fmt(tr):>10} {fmt(roe):>8}")

# 保存 JSON
out = {"high_growth_over_50pct": high_growth, "all_results": results, "errors": errors}
with open("growth_result.json","w",encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n结果已保存到 growth_result.json")
