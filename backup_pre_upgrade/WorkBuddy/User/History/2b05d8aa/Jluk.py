#!/usr/bin/env python3
"""快速验证DB中net_profit_ex和fin_expense是否有值"""
import sqlite3

conn = sqlite3.connect(r'd:\Project\ScoreSys\stock_data_test.db')
cur = conn.cursor()

for symbol in ['600519', '000858']:
    cur.execute('SELECT report_date, net_profit_ex, fin_expense FROM financials WHERE symbol=? ORDER BY report_date DESC LIMIT 6', (symbol,))
    rows = cur.fetchall()
    print(f"\n{symbol} net_profit_ex & fin_expense (latest 6):")
    for r in rows:
        npx = r[1] if r[1] else 0
        fe = r[2] if r[2] else 0
        flag_np = " <<< ZERO" if npx == 0 else ""
        flag_fe = " <<< ZERO" if fe == 0 else ""
        print(f"  {r[0]} | np_ex={npx:>15,.2f}{flag_np} | fin_exp={fe:>12,.2f}{flag_fe}")

conn.close()
