#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用东方财富公开API验证财务数据
"""
import requests
import json

def get_em_finance(ts_code):
    """东方财富主要财务指标"""
    code = ts_code.split(".")[0]
    market = "1" if ts_code.endswith(".SH") else "0"
    secid = f"{market}.{code}"
    
    # 主要财务指标 API
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": secid,
        "fields": "f162,f167,f168,f170,f171,f111,f112,f113,f114,f115,f116,f117,f118,f119,f120,f121,f122,f123,f124,f125,f126,f127,f128,f129,f130,f131,f132,f133,f134,f135,f136,f137,f138,f139,f140,f141,f142,f143,f144,f145,f146,f147,f148,f149,f150,f151,f152,f153,f154,f155,f156,f157,f158,f159,f160,f161,f163,f164,f165,f166,f169,f172,f173,f174,f175,f176,f177,f178,f179,f180,f181,f182,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f193,f194,f195,f196,f197,f198,f199,f200,f201,f202,f203,f204,f205,f206,f207,f208,f209,f210,f211,f212,f213,f214,f215,f216,f217,f218,f219,f220,f221,f222,f223,f224,f225",
        "ut": "fa5fd1943c7b386f172d6893dbbd1180",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        return resp.json().get("data", {})
    except Exception as e:
        print(f"  错误: {e}")
        return {}

def get_em_income(ts_code):
    """东方财富利润表"""
    code = ts_code.split(".")[0]
    market = "1" if ts_code.endswith(".SH") else "0"
    secid = f"{market}.{code}"
    
    url = "https://push2his.eastmoney.com/api/qt/stock/fflow/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "end": "20251231",
        "lmt": "5",
        "ut": "fa5fd1943c7b386f172d6893dbbd1180",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json().get("data", {})
        if data and data.get("klines"):
            # 找2024年报
            for kline in data["klines"]:
                if "2024" in kline:
                    return kline
    except Exception as e:
        print(f"  错误: {e}")
    return None

# 字段映射 (东方财富 -> 我们的指标)
# f111=ROE, f112=毛利率, f113=净利率
# 但东方财富这些字段可能是百分比形式

stocks = [
    ("603350.SH", "安乃达", {
        "ROE(%)": 8.67,
        "毛利率(%)": 15.53,
        "净利率(%)": 5.7,
        "营收同比(%)": 31.14,
        "净利润同比(%)": 4.62,
        "资产负债率(%)": 44.59,
        "净利润(元)": 115036375.06,
        "经营现金流(元)": -1455064.26,
    }),
    ("000852.SZ", "石化机械", {
        "ROE(%)": 0.35,
        "毛利率(%)": 14.09,
        "净利率(%)": 0.43,
        "营收同比(%)": -10.37,
        "净利润同比(%)": -88.79,
        "资产负债率(%)": 68.27,
        "净利润(元)": 10858163.44,
        "经营现金流(元)": 591141237.03,
    }),
]

for ts_code, name, excel_vals in stocks:
    print(f"\n{'='*60}")
    print(f"验证: {ts_code} {name}")
    print(f"{'='*60}")
    
    data = get_em_finance(ts_code)
    if not data:
        print("  API无数据")
        continue
    
    # 打印关键财务指标
    # f162=市盈率, f167=市净率 等
    # 需要找到ROE、毛利率等字段
    
    # 先打印所有非空字段，看看哪些有用
    print(f"\n  [东方财富 实时行情财务字段]")
    useful = {}
    for k, v in data.items():
        if v is not None and str(v).strip() and str(v) != "None" and str(v) != "0":
            useful[k] = v
    
    # 打印前30个非空字段
    for i, (k, v) in enumerate(list(useful.items())[:30]):
        print(f"    {k}: {v}")
    
    # 尝试对比已知字段
    print(f"\n  [关键指标对比]")
    
    # 东方财富字段映射（根据文档）
    # f111 = ROE (可能)
    em_fields = {
        "f111": "ROE(%)",
        "f112": "毛利率(%)", 
        "f113": "净利率(%)",
        "f114": "资产负债率(%)",
    }
    
    for em_field, our_field in em_fields.items():
        em_val = data.get(em_field)
        our_val = excel_vals.get(our_field)
        if em_val and our_val:
            try:
                diff = abs(float(em_val) - float(our_val))
                status = "✅" if diff < 1 else f"⚠️ 差{diff:.2f}"
            except:
                status = "无法比较"
            print(f"    {our_field}: Excel={our_val}  EM={em_val}  {status}")

print(f"\n{'='*60}")
print("验证完成")
print("\n注意: 东方财富实时行情API可能不包含年报详细指标")
print("建议直接对比东方财富网站年报页面")
