import os, json, re, sys
sys.path.insert(0, r'D:\Project\AnnualScorer')
from stock_analyzer import load_token, run_neodata, _extract_annual_block, parse_financial_all

token = load_token()

# 3只验证股票
targets = [
    ('300164.SZ', '通源石油'),
    ('002546.SZ', '新联电子'),
    ('689009.SH', '九号公司-WD'),
]

for ts_code, name in targets:
    print(f'{"="*60}')
    print(f'查询: {ts_code} {name}')
    print(f'{"="*60}')
    
    query = f'{ts_code} {name} 年报'
    text = run_neodata(query, token)
    
    if not text:
        print('  [空返回]')
        print()
        continue
    
    # 打印原始返回的前500字符
    print(f'原始返回(前800字符):')
    print(text[:800])
    print()
    
    # 提取年报段落
    block = _extract_annual_block(text)
    if block:
        print(f'年报段落(前500字符):')
        print(block[:500])
        print()
        
        metrics = parse_financial_all(block)
        print(f'解析结果:')
        for k, v in metrics.items():
            if v is not None:
                print(f'  {k}: {v}')
            else:
                print(f'  {k}: [None]')
    else:
        print('[未找到年报段落]')
        # 尝试兜底
        from stock_analyzer import _guess_date_from_trend
        fallback = _guess_date_from_trend(text)
        if fallback:
            print(f'兜底提取(前300字符):')
            print(fallback[:300])
            metrics = parse_financial_all(fallback)
            print(f'兜底解析结果:')
            for k, v in metrics.items():
                if v is not None:
                    print(f'  {k}: {v}')
                else:
                    print(f'  {k}: [None]')
    print()
