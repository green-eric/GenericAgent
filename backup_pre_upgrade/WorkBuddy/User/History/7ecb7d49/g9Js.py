import re

# 使用实际API返回的文本格式
text = u"统计截止日期为20260331的Q1单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：\n营业总收入28089539.46元，\n\n统计截止日期为20251231的年报，其中利润表相关的财务指标如下（货币单位：人民币元）：\n营业总收入249134153.16元，\n\n统计截止日期为20251231的Q4单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：\n营业总收入90430968.47元，\n\n统计截止日期为20250930的Q3单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：\n营业总收入71481077.4元，\n\n统计截止日期为20250630的Q2单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：\n营业总收入48253216.43元，\n\n统计截止日期为20250331的Q1单季报（最新调整），其中利润表相关的财务指标如下（货币单位：人民币元）：\n营业总收入38968890.86元，"

# 测试当前正则
pattern = r"\u7edf\u8ba1\u622a\u6b62\u65e5\u671f\u4e3a(\d{4})(0331|0630|0930)\u7684\u5b63\u62a5"
matches = list(re.finditer(pattern, text))
print("=== Current regex matches ===")
print("Count: " + str(len(matches)))
for m in matches:
    print("  year=" + m.group(1) + " q=" + m.group(2))

# 测试修复后的正则
pattern2 = r"\u7edf\u8ba1\u622a\u6b62\u65e5\u671f\u4e3a(\d{4})(0331|0630|0930|1231)\u7684\u5b63\u62a5"
matches2 = list(re.finditer(pattern2, text))
print("\n=== Fixed regex matches ===")
print("Count: " + str(len(matches2)))
for m in matches2:
    print("  year=" + m.group(1) + " q=" + m.group(2))

# Also try the actual pattern from the code
pattern3 = r"统计截止日期为(\d{4})(0331|0630|0930)的季报"
matches3 = list(re.finditer(pattern3, text))
print("\n=== Code regex matches ===")
print("Count: " + str(len(matches3)))
for m in matches3:
    print("  year=" + m.group(1) + " q=" + m.group(2))
