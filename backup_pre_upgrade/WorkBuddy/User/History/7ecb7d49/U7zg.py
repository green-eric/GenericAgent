# 从之前查询返回的"财务主要复合指标"段落搜索
content = u"""根据神农种业（代码:300189.SZ）在A股市场20260425发布的财报数据，统计截止日期为20260331的Q1单季报，主要财务指标如下（货币单位：人民币元）：
1、资产负债结构方面：，
资产合计1275274622.54元，
负债合计492197113.25元。
2、现金流状况方面：
每股现金流量净额-0.03元
销售现金比率-133.00%
净利润现金含量574.94%，
每股经营活动产生的现金流量净额-0.04元。
3、盈利能力方面：
营业总收入28089539.46元，
营业收入28089539.46元，
营业成本16289532.96元，
净利润-4885797.09元，
归母净利润-6497683.81元，
扣非净利润-4441777.60元，
销售净利率-23.13%，
销售毛利率42.01%，
销售毛利11800006.50元，
资产回报率ROA-0.51%，
毛销差27.12%。
4、运营能力方面：
总资产周转率0.02次，
应收账款周转率0.22次，
存货周转率0.30次，
流动资产周转率0.08次。
5、成长性方面：，
归母净利润同比增长48.60%，
净利润同比增长57.01%。"""

# 搜索59.18
import re
print("=== Searching for 59.18 ===")
for line in content.split('\n'):
    if '59.18' in line:
        print("FOUND: " + line)

print("\n=== Searching for 444.78 ===")
for line in content.split('\n'):
    if '444.78' in line:
        print("FOUND: " + line)

# 搜索所有百分比
print("\n=== All percentages ===")
for line in content.split('\n'):
    matches = re.findall(r'(\d+\.?\d*)%', line)
    if matches:
        print(line.strip() + " -> " + str(matches))

# 看看是否有"营收同比增长"
print("\n=== Revenue yoy ===")
for line in content.split('\n'):
    if '营收' in line and '同比' in line:
        print(line)
    if '营业总收入' in line and '同比' in line:
        print(line)
