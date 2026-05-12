#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试股票列表加载"""

import os

def debug_load_stocks():
    stock_list_file = r"C:\Users\green\Desktop\gy\xuan.txt"

    print(f"检查文件是否存在: {stock_list_file}")
    print(f"文件存在: {os.path.exists(stock_list_file)}")

    if os.path.exists(stock_list_file):
        print("开始读取文件...")
        try:
            with open(stock_list_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"读取到 {len(lines)} 行")
                for i, line in enumerate(lines[:10]):  # 只显示前10行
                    print(f"第{i+1}行: '{line.strip()}'")
        except Exception as e:
            print(f"读取失败: {e}")

if __name__ == "__main__":
    debug_load_stocks()