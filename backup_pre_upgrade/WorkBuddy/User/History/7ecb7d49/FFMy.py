import sqlite3

conn = sqlite3.connect(r'D:\Project\QAScorer\quarterly_cache.db')
conn.row_factory = sqlite3.Row

# 查看所有季度原始数据，按日期排序
print("=== quarterly_reports (all) ===")
cur = conn.execute('SELECT report_date, revenue, net_profit, revenue_yoy, profit_yoy FROM quarterly_reports WHERE ts_code=? ORDER BY report_date ASC', ('300189.SZ',))
for row in cur.fetchall():
    d = dict(row)
    print("report_date=" + str(d['report_date'])
          + " | revenue=" + str(d.get('revenue'))
          + " | net_profit=" + str(d.get('net_profit'))
          + " | revenue_yoy=" + str(d.get('revenue_yoy'))
          + " | profit_yoy=" + str(d.get('profit_yoy')))

# 对比API返回的数据
print("\n=== API返回的20260331 Q1数据 ===")
print("营业总收入: 28,089,539.46")
print("归母净利润: -6,497,683.81")
print("营收同比: 无直接字段(利润表段)")
print("净利润同比: 无直接字段(利润表段)")

print("\n=== API返回的财务主要复合指标(20260331) ===")
print("营业总收入: 28,089,539.46")
print("归母净利润同比增长: 48.60%")
print("净利润同比增长: 57.01%")

print("\n=== 问题分析 ===")
print("缓存中 report_date=20260331 的 revenue=90,430,968.47")
print("但API返回的20260331 Q1营收是 28,089,539.46")
print("90,430,968.47 实际是 20251231 Q4的营收！")
print("")
print("说明：_extract_all_quarterly_blocks 提取段落时，")
print("year/q_date 解析正确，但 block_text 内容取错了！")

conn.close()
