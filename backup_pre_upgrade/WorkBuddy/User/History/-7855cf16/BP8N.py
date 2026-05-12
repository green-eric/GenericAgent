"""快速获取宏和科技解析后的核心指标"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from annual_scorer import parse_financial_all, fetch_financial_data

TARGET = "603256.SH"
raw = fetch_financial_data(TARGET)
parsed = parse_financial_all(raw)

print("=== 宏和科技 603256.SH 解析指标 ===")
for k, v in parsed.items():
    if v is not None:
        print(f"  {k}: {v}")
    else:
        print(f"  {k}: [缺失]")
