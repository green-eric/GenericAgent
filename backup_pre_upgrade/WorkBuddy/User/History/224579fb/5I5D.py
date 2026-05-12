# -*- coding: utf-8 -*-
import re

def parse_num(text):
    if not text: return None
    m = re.search(r"([-+]?\d+\.?\d*)%", text)
    if m: return float(m.group(1))
    m = re.search(r"([-+]?\d+\.?\d*)", text)
    if m: return float(m.group(1))
    return None

def _extract_metric_line(block, keywords):
    for line in block.split("\n"):
        line = line.strip()
        if not line: continue
        for kw in keywords:
            if kw in line: return line
    return None

block = """Q1单季报
销售毛利率45.23%
销售净利率22.15%
归母净利润同比增长18.67%
营业总收入3250000000.00元"""

def parse_quarterly_finance(block):
    r = {}
    line = _extract_metric_line(block, ["销售毛利率"])
    print(f"Gross margin line: {repr(line)}")
    if line and "毛利率" in line:
        val = line[line.find("毛利率"):]
        print(f"Extracted: {repr(val)}")
        r["gross_margin"] = parse_num(val)
    else:
        r["gross_margin"] = None

    line = _extract_metric_line(block, ["销售净利率"])
    print(f"Net margin line: {repr(line)}")
    if line and "净利率" in line:
        val = line[line.find("净利率"):]
        r["net_margin"] = parse_num(val)
    else:
        r["net_margin"] = None

    line = _extract_metric_line(block, ["营业收入同比增长", "营收同比增长", "营业总收入同比增长"])
    print(f"Revenue YoY line: {repr(line)}")
    r["revenue_yoy"] = parse_num(line) if line else None

    line = _extract_metric_line(block, ["归母净利润同比增长"])
    print(f"Profit YoY line: {repr(line)}")
    r["profit_yoy"] = parse_num(line) if line else None

    return r

qm = parse_quarterly_finance(block)
print(f"\nParsed metrics: {qm}")