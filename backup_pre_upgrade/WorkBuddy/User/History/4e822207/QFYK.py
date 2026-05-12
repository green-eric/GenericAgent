#!/usr/bin/env python3

# 读取文件并修复语法错误
with open('d:/Project/QAScorer/qa_scorer.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要修复的行
fixed_lines = []
for i, line in enumerate(lines):
    if 'Args:' in line and i > 590 and i < 610:  # 在特定范围内查找Args
        # 修复缩进
        fixed_line = '    Args:\n'
        fixed_lines.append(fixed_line)
    else:
        fixed_lines.append(line)

# 写入修复后的文件
with open('d:/Project/QAScorer/qa_scorer.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("语法修复完成")