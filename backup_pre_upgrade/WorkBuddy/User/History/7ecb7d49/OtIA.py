import re

# 模拟API返回的关键段落（简化版）
text = """
根据神农种业（代码:300189.SZ）在A股市场20260425发布的财报数据，统计截止日期为20260331的Q1单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：
营业总收入28089539.46元，
归母净利润-6497683.81元，

根据神农种业（代码:300189.SZ）在A股市场20260425发布的财报数据，统计截止日期为20251231的年报，其中利润表相关的财务指标如下（货币单位：人民币元）：
营业总收入249134153.16元，

根据神农种业（代码:300189.SZ）在A股市场20260425发布的财报数据，统计截止日期为20251231的Q4单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：
营业总收入90430968.47元，
归母净利润101502648.06元，

根据神农种业（代码:300189.SZ）在A股市场20251029发布的财报数据，统计截止日期为20250930的Q3单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：
营业总收入71481077.4元，
归母净利润20014517.99元，

根据神农种业（代码:300189.SZ）在A股市场20260113发布的财报数据，统计截止日期为20250630的Q2单季报，其中利润表相关的财务指标如下（货币单位：人民币元）：
营业总收入48253216.43元，
归母净利润-1717949.68元，

根据神农种业（代码:300189.SZ）在A股市场20260425发布的财报数据，统计截止日期为20250331的Q1单季报（最新调整），其中利润表相关的财务指标如下（货币单位：人民币元）：
营业总收入38968890.86元，
归母净利润-12641464.89元，
"""

# 测试当前正则
pattern = r"统计截止日期为(\d{4})(0331|0630|0930)的季报"
matches = list(re.finditer(pattern, text))
print("=== 当前正则匹配结果 ===")
for m in matches:
    print("Match: year=" + m.group(1) + " q=" + m.group(2) + " pos=" + str(m.start()) + "-" + str(m.end()))

print("\n=== 提取的段落 ===")
for i, m in enumerate(matches):
    year = m.group(1)
    q_date = m.group(2)
    start = m.end()
    if i + 1 < len(matches):
        end = matches[i + 1].start()
    else:
        end = len(text)
    block = text[start:end].strip()
    print("\n--- Block " + str(i) + " (year=" + year + ", q=" + q_date + ") ---")
    print(block[:200])

# 修复后的正则
print("\n\n=== 修复后正则匹配结果 ===")
pattern_fixed = r"统计截止日期为(\d{4})(0331|0630|0930|1231)的季报"
matches_fixed = list(re.finditer(pattern_fixed, text))
for m in matches_fixed:
    print("Match: year=" + m.group(1) + " q=" + m.group(2) + " pos=" + str(m.start()) + "-" + str(m.end()))

print("\n=== 修复后提取的段落 ===")
for i, m in enumerate(matches_fixed):
    year = m.group(1)
    q_date = m.group(2)
    start = m.end()
    if i + 1 < len(matches_fixed):
        end = matches_fixed[i + 1].start()
    else:
        end = len(text)
    block = text[start:end].strip()
    print("\n--- Block " + str(i) + " (year=" + year + ", q=" + q_date + ") ---")
    print(block[:200])
