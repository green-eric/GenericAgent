#!/usr/bin/env python3

# 读取文件并修复语法错误
with open('d:/Project/QAScorer/qa_scorer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换所有有问题的中文字符
content = content.replace('（', '(').replace('）', ')').replace('，', ',').replace('。', '.').replace('：', ':').replace('、', 'and')

# 写入修复后的文件
with open('d:/Project/QAScorer/qa_scorer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("语法修复完成")