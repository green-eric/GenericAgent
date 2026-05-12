import sys
sys.path.append('.')

from ultimate_analyzer_with_real_list import RealListAnalyzer

# 创建分析器实例
analyzer = RealListAnalyzer()

# 手动加载股票列表
stock_list_file = "C:\\Users\\green\\Desktop\\gy\\xuan.txt"
with open(stock_list_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        symbol = line.split()[0] if ' ' in line else line
        name = line if ' ' not in line else ' '.join(line.split()[1:])
        if symbol.startswith('688') or symbol.startswith('430'):
            continue
        exchange_suffix = '.SZ' if symbol.startswith(('0','3')) else '.SH'
        full_code = symbol + exchange_suffix
        analyzer.stock_list.append({
            "ts_code": full_code,
            "symbol": symbol,
            "name": name
        })

print(f"成功加载 {len(analyzer.stock_list)} 只股票")

# 测试前10个股票的行业分类
print("\n=== 行业分类测试 ===")
for i, stock in enumerate(analyzer.stock_list[:10]):
    industry = analyzer.get_industry(stock["symbol"])
    print(f"{i+1}. {stock['name']}({stock['symbol']}) -> '{industry}'")

# 显示行业映射表的前20项
print(f"\n=== 行业映射表前20项 ===")
items = list(analyzer.industry_map.items())
for i in range(min(20, len(items))):
    symbol, industry = items[i]
    print(f"'{symbol}' -> '{industry}'")