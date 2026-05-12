import sqlite3
conn = sqlite3.connect('d:/Project/ScoreSys/stock_data.db')
cur = conn.cursor()

# 000915具体情况
cur.execute('SELECT * FROM stocks WHERE symbol = ?', ('000915',))
row = cur.fetchone()
print('000915 stocks表:', row)

# 统计名称/行业缺失情况
cur.execute('SELECT COUNT(DISTINCT symbol) FROM financials')
total_fin = cur.fetchone()[0]

cur.execute('SELECT COUNT(*) FROM stocks')
total_stocks = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM stocks WHERE name IS NULL OR name = ''")
no_name = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM stocks WHERE name IS NOT NULL AND name != ''")
has_name = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM stocks WHERE industry IS NULL OR industry = ''")
no_ind = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM stocks WHERE industry IS NOT NULL AND industry != ''")
has_ind = cur.fetchone()[0]

# name=symbol的情况（名称等于代码，说明没取到真名）
cur.execute("SELECT COUNT(*) FROM stocks WHERE name = symbol")
name_is_code = cur.fetchone()[0]

print(f'\n财务数据: {total_fin}只')
print(f'stocks表: {total_stocks}条')
print(f'  有名称: {has_name} (其中名称=代码: {name_is_code})')
print(f'  无名称: {no_name}')
print(f'  有行业: {has_ind}')
print(f'  无行业: {no_ind}')

# 看几个样例
print('\n名称=代码的前10只:')
cur.execute("SELECT symbol, name, industry FROM stocks WHERE name = symbol LIMIT 10")
for r in cur.fetchall():
    print(f'  {r[0]}: name={r[1]}, industry={r[2]}')

conn.close()
