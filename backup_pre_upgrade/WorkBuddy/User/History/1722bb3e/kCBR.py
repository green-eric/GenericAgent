#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys

# 添加项目目录到path
sys.path.insert(0, r'D:\Project\QAScorer')

# 导入qa_scorer中的函数
from qa_scorer import run_neodata, load_token

token = load_token()
ts_code = "300189.SZ"
name = "神农种业"

# 用代码中的查询方式
query = ts_code + " " + name + " 最新季报"
print("Query: " + query)

text = run_neodata(query, token)
print("\n=== Raw response length: " + str(len(text)) + " ===")

# 搜索59.18和444.78
import re
print("\n=== Searching for 59.18 ===")
for i, line in enumerate(text.split('\n')):
    if '59.18' in line:
        print("Line " + str(i) + ": " + line.strip())

print("\n=== Searching for 444.78 ===")
for i, line in enumerate(text.split('\n')):
    if '444.78' in line:
        print("Line " + str(i) + ": " + line.strip())

# 搜索所有同比
print("\n=== All yoy lines ===")
for i, line in enumerate(text.split('\n')):
    if '同比' in line:
        print("Line " + str(i) + ": " + line.strip())

# 打印前500字符
print("\n=== First 500 chars ===")
print(text[:500])
