import sqlite3

# Create a simple test to see what's happening
conn = sqlite3.connect('quarterly_cache.db')
cur = conn.execute("""
    CREATE TABLE IF NOT EXISTS test_table (
        ts_code TEXT,
        report_date TEXT,
        report_type TEXT,
        revenue REAL,
        operating_cost REAL,
        net_profit REAL,
        net_profit_deducted REAL,
        ocf_abs REAL,
        total_assets REAL,
        total_liabilities REAL,
        net_assets REAL,
        gross_margin REAL,
        net_margin REAL,
        debt_ratio REAL,
        ocf_ratio REAL,
        roa REAL,
        revenue_yoy REAL,
        profit_yoy REAL,
        last_update TEXT
    )
""")
conn.commit()

# Test INSERT with correct number of parameters
test_data = (
    "000001.SZ", "20260331", "quarterly",
    1000.0, 500.0, 200.0, 180.0, 250.0, 5000.0, 3000.0, 2000.0,
    50.0, 20.0, 60.0, 125.0, 4.0, 10.0, 15.0, "2026-04-26T23:30:00"
)

try:
    cur.execute("INSERT INTO test_table VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", test_data)
    conn.commit()
    print("Test insert succeeded!")
except Exception as e:
    print(f"Test insert failed: {e}")

# Check if data was inserted
cur.execute("SELECT * FROM test_table")
row = cur.fetchone()
if row:
    print(f"Inserted row has {len(row)} fields")
else:
    print("No rows inserted")

conn.close()