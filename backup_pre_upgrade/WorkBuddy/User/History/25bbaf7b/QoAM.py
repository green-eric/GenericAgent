#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试股票列表解析"""

def debug_parse_stocks():
    stock_list_file = r"C:\Users\green\Desktop\gy\xuan.txt"

    stocks = []
    with open(stock_list_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    ts_code = parts[0].strip()
                    name = parts[1].strip()

                    # 确定交易所后缀
                    if ts_code.startswith('0') or ts_code.startswith('3'):
                        exchange_suffix = '.SZ'
                    else:
                        exchange_suffix = '.SH'

                    full_ts_code = ts_code + exchange_suffix

                    # 过滤掉科创板股票（688、430开头）
                    if not (ts_code.startswith('688') or ts_code.startswith('430')):
                        stocks.append({
                            "ts_code": full_ts_code,
                            "symbol": ts_code,
                            "name": name
                        })
            elif line and ' ' in line:  # 尝试空格分隔格式
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    ts_code = parts[0].strip()
                    name = parts[1].strip()

                    if not (ts_code.startswith('688') or ts_code.startswith('430')):
                        stocks.append({
                            "ts_code": ts_code + ('.SZ' if ts_code.startswith('0') or ts_code.startswith('3') else '.SH'),
                            "symbol": ts_code,
                            "name": name
                        })

    print(f"成功解析 {len(stocks)} 只股票")
    for i, stock in enumerate(stocks[:5]):
        print(f"{i+1}: {stock}")

if __name__ == "__main__":
    debug_parse_stocks()