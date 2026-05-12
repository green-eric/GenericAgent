import re

# 从实际API返回中提取的关键文本
text = "统计截止日期为20260331的Q1单季报，其中利润表相关的财务指标如下"

# 测试
pattern = r"统计截止日期为(\d{4})(0331|0630|0930)的季报"
m = re.search(pattern, text)
print("Test 1: " + str(m))

# 也许是"的Q1单季报"而不是"的季报"？
pattern2 = r"统计截止日期为(\d{4})(0331|0630|0930)的"
m2 = re.search(pattern2, text)
print("Test 2: " + str(m2))
if m2:
    print("  year=" + m2.group(1) + " q=" + m2.group(2))

# 完整测试
text2 = "统计截止日期为20260331的Q1单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：营业总收入28089539.46元，归母净利润-6497683.81元，统计截止日期为20251231的年报，其中利润表相关的财务指标如下（货币单位：人民币元）：营业总收入249134153.16元，统计截止日期为20251231的Q4单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：营业总收入90430968.47元，统计截止日期为20250930的Q3单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：营业总收入71481077.4元，统计截止日期为20250630的Q2单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：营业总收入48253216.43元，统计截止日期为20250331的Q1单季报（最新调整），其中利润表相关的财务指标如下（货币单位：人民币元）：营业总收入38968890.86元，"

# 当前代码的正则
pattern3 = r"统计截止日期为(\d{4})(0331|0630|0930)的季报"
matches3 = list(re.finditer(pattern3, text2))
print("\n=== Code regex ===")
print("Count: " + str(len(matches3)))
for m in matches3:
    print("  year=" + m.group(1) + " q=" + m.group(2) + " text=" + text2[m.start():m.end()])

# 宽松匹配
pattern4 = r"统计截止日期为(\d{4})(0331|0630|0930|1231)的季报"
matches4 = list(re.finditer(pattern4, text2))
print("\n=== Fixed regex (with 1231) ===")
print("Count: " + str(len(matches4)))
for m in matches4:
    print("  year=" + m.group(1) + " q=" + m.group(2) + " text=" + text2[m.start():m.end()])

# 看看"的季报"vs"的Q1单季报"
pattern5 = r"统计截止日期为(\d{4})(0331|0630|0930|1231)"
matches5 = list(re.finditer(pattern5, text2))
print("\n=== Ultra loose regex ===")
print("Count: " + str(len(matches5)))
for m in matches5:
    print("  year=" + m.group(1) + " q=" + m.group(2) + " text=" + text2[m.start():m.start()+30])
