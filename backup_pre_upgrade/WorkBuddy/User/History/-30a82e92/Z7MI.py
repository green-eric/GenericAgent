#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, re, sys, io, time
try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MDc5NzYzNDEsImlhdCI6MTc3NjkzNDIxOCwiYXV0aF90aW1lIjoxNzc2NDQwMzQyLCJqdGkiOiJhZGYzYzFkNi1kN2FlLTQ4ZGItYjg1Mi1lMTI3YjY2MTVjOGMiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiJjYWY4Y2NkZC1hNjE4LTQ3MDEtOGVkZS02ZDhkMTNjZjI5MjAiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiNmNlZjhlOTktYTYzYi00NGM1LWE1NjAtNjY4YWMyNTFjN2E5IiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi6Z2Z5rC05rWB5rexIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTMwNjI4ODQyNTMifQ.h0E0KtMPMZG07c0hpbkolsoEnarS0s2P5QgmClNcIIkDFYemp79_iX_uEV4fKArp1jZZDaMfN03y19EDxf-VfTl_DT-u7ZlbGDn1h_tbBvhNoVdR9Z34xC2HU5lAA7wUyFASDSsJNek2rGOkIEHYIQa9rm3WlLsAfZAg594QTwUp_TF-mzuJnfg44GIYHGfVsNszJKlI5caJfyJyd1R52LlvZfK7MJ7EdO_tZNehqO6jekIVIYVynBaO3wRZMikod3K7i-_V7YxKHY_EZW_QMJ0v1JCc4pyDSKLEIZjYPHH9tjTQNCGg3sPIv1joESCGeYGChBBRi4VW5SR8TXCkDQ"

# 排除科创板688开头
stocks_all = [
    ("圣邦股份","300661.SZ"),("光迅科技","002281.SZ"),("信维通信","300136.SZ"),
    ("三环集团","300408.SZ"),("天岳先进","688234.SH"),("沪电股份","002463.SZ"),
    ("安克创新","300866.SZ"),("鼎龙股份","300054.SZ"),("德业股份","605117.SH"),
    ("新产业","300832.SZ"),("长川科技","300604.SZ"),("华润微","688396.SH"),
    ("工业富联","601138.SH"),("伯特利","603596.SH"),("水晶光电","002273.SZ"),
    ("华测检测","300012.SZ"),("石头科技","688169.SH"),("中际旭创","300308.SZ"),
    ("思源电气","002028.SZ"),("药明康德","603259.SH"),("金山办公","688111.SH"),
    ("中科创达","300496.SZ"),("景嘉微","300474.SZ"),("时代电气","688187.SH"),
    ("宝信软件","600845.SH"),("全志科技","300458.SZ"),("联影医疗","688271.SH"),
    ("公牛集团","603195.SH"),("汇顶科技","603160.SH"),("中国移动","600941.SH"),
    ("深南电路","002916.SZ"),("三星电气","601567.SH"),("中航高科","600862.SH"),
    ("海康威视","002415.SZ"),("润和软件","300339.SZ"),("华大九天","301269.SZ"),
    ("分众传媒","002027.SZ"),("宏发股份","600885.SH"),("萤石网络","688475.SH"),
    ("北方华创","002371.SZ"),("中航重机","600765.SH"),("开立医疗","300633.SZ"),
    ("软通动力","301236.SZ"),("沃尔核材","002130.SZ"),("恒立液压","601100.SH"),
    ("士兰微","600460.SH"),("浙江鼎力","603338.SH"),("鱼跃医疗","002223.SZ"),
    ("鹏鼎控股","002938.SZ"),("扬杰科技","300373.SZ"),("中科软","603927.SH"),
    ("思特威-W","688213.SH"),("科大讯飞","002230.SZ"),("拓邦股份","002139.SZ"),
    ("亿联网络","300628.SZ"),("生益科技","600183.SH"),("数字政通","300075.SZ"),
    ("恒生电子","600570.SH"),("紫光国微","002049.SZ"),("雅克科技","002409.SZ"),
    ("格科微","688728.SH"),("中微公司","688012.SH"),("惠泰医疗","688617.SH"),
    ("中航光电","002179.SZ"),("传音控股","688036.SH"),("安集科技","688019.SH"),
    ("航天信息","600271.SH"),("深信服","300454.SZ"),("大华股份","002236.SZ"),
    ("顺络电子","002138.SZ"),("阳光电源","300274.SZ"),("豪威集团","603501.SH"),
    ("万兴科技","300624.SZ"),("中控技术","688777.SH"),("芯源微","688037.SH"),
    ("中天科技","600522.SH"),("澜起科技","688008.SH"),("柏楚电子","688188.SH"),
    ("汇川技术","300124.SZ"),("智飞生物","300122.SZ"),("云赛智联","600602.SH"),
    ("国科微","300672.SZ"),("领益智造","002600.SZ"),("中科飞测","688361.SH"),
    ("江丰电子","300666.SZ"),("特宝生物","688278.SH"),("晶盛机电","300316.SZ"),
    ("精测电子","300567.SZ"),("电连技术","300679.SZ"),("航天电器","002025.SZ"),
    ("拓荆科技","688072.SH"),("华海清科","688120.SH"),("法拉电子","600563.SH"),
    ("铂科新材","300811.SZ"),("福晶科技","002222.SZ"),("天孚通信","300394.SZ"),
    ("菲利华","300395.SZ"),("卓胜微","300782.SZ"),("爱玛科技","603529.SH"),
    ("赛微电子","300456.SZ"),
]

# 排除科创板(688开头)
stocks = [(n, c) for n, c in stocks_all if not c.startswith("688")]
excluded = [(n, c) for n, c in stocks_all if c.startswith("688")]
print(f"总共 {len(stocks_all)} 只，排除科创板 {len(excluded)} 只，剩余 {len(stocks)} 只")

URL = "https://copilot.tencent.com/agenttool/v1/neodata"
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}

def parse_profit(content, target_period_end="1231"):
    profits = {}
    segments = re.split(r'根据', content)
    for seg in segments:
        m_period = re.search(r'截止日期为(\d{8})', seg)
        if not m_period:
            continue
        period = m_period.group(1)
        if not period.endswith(target_period_end):
            continue
        if "单季" in seg or "Q4单季" in seg:
            continue
        m_profit = re.search(r'归母净利润([+-]?[\d,\.]+)元', seg)
        if m_profit:
            val = m_profit.group(1).replace(',', '')
            try:
                profits[period] = float(val)
            except:
                pass
        if not profits.get(period):
            m_net = re.search(r'净利润([+-]?[\d,\.]+)元', seg)
            if m_net:
                val = m_net.group(1).replace(',', '')
                try:
                    profits[period] = float(val)
                except:
                    pass
    return profits

def query_neodata(name, ts_code, year):
    payload = {
        "query": f"{name}({ts_code}) {year}年年报归母净利润",
        "channel": "neodata",
        "sub_channel": "workbuddy",
        "data_type": "api"
    }
    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=30)
        d = r.json()
        items = d.get("data", {}).get("apiData", {}).get("apiRecall", [])
        all_content = ""
        for it in items:
            all_content += it.get("content", "")
        profits = parse_profit(all_content)
        target = f"{year}1231"
        if target in profits:
            return profits[target]
        for k, v in profits.items():
            if k.endswith("1231"):
                return v
        return None
    except:
        return None

total = len(stocks)

# 第1轮：查2025年报
print(f"\n=== 第1轮：查询2025年报归母净利润 ({total}只) ===")
net2025_map = {}
for i, (name, ts_code) in enumerate(stocks):
    v = query_neodata(name, ts_code, "2025")
    net2025_map[ts_code] = v
    status = f"{v/1e8:.2f}亿" if v else "N/A"
    print(f"[{i+1:3d}/{total}] {name}({ts_code}): 2025={status}")
    time.sleep(0.25)

# 第2轮：查2024年报
print(f"\n=== 第2轮：查询2024年报归母净利润 ({total}只) ===")
net2024_map = {}
for i, (name, ts_code) in enumerate(stocks):
    v = query_neodata(name, ts_code, "2024")
    net2024_map[ts_code] = v
    status = f"{v/1e8:.2f}亿" if v else "N/A"
    print(f"[{i+1:3d}/{total}] {name}({ts_code}): 2024={status}")
    time.sleep(0.25)

# 计算增长率
results = []
high_growth = []
for name, ts_code in stocks:
    n25 = net2025_map.get(ts_code)
    n24 = net2024_map.get(ts_code)
    yoy = None
    if n25 is not None and n24 is not None and n24 != 0:
        yoy = round((n25 - n24) / abs(n24) * 100, 2)
    results.append({"name": name, "ts_code": ts_code, "net2025": n25, "net2024": n24, "yoy": yoy})
    if yoy is not None and yoy > 50:
        high_growth.append({"name": name, "ts_code": ts_code, "net2025": n25, "net2024": n24, "yoy": yoy})

high_growth.sort(key=lambda x: x["yoy"], reverse=True)

print(f"\n{'='*70}")
print(f"2025年报归母净利润增长率 > 50%（排除科创板）共 {len(high_growth)} 只：")
print(f"{'='*70}")
for r in high_growth:
    v25 = r["net2025"]/1e8 if r["net2025"] else 0
    v24 = r["net2024"]/1e8 if r["net2024"] else 0
    print(f"{r['name']:<10} {r['ts_code']:<13} 2025={v25:.2f}亿 2024={v24:.2f}亿 增长={r['yoy']:.1f}%")

# 保存
with open("growth_2025_result.json", "w", encoding="utf-8") as f:
    json.dump({"high_growth_over50": high_growth, "all": results, "excluded_kcb": excluded}, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存到 growth_2025_result.json")
