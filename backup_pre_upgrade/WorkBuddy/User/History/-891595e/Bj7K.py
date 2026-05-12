import sys, os
sys.path.insert(0, r'D:\Project\QAScorer')
from qa_scorer import load_token, run_neodata, _extract_all_quarterly_blocks, _parse_single_block

token = load_token()
# Test with a few stocks
test_stocks = ['600338.SH', '300502.SZ', '002466.SZ']
for ts_code in test_stocks:
    name = ts_code.split('.')[0]
    text = run_neodata(f"{ts_code} {name} 最新季报", token)
    if not text:
        print(f"{ts_code}: no data")
        continue
    
    # Search for net assets / equity keywords
    for keyword in ['净资产', '股东权益', '所有者权益', '归母净资产', '归母股东权益']:
        if keyword in text:
            # Find the line
            for line in text.split('\n'):
                if keyword in line:
                    print(f"{ts_code} [{keyword}]: {line.strip()[:120]}")
                    break
    
    # Also check blocks
    blocks = _extract_all_quarterly_blocks(text)
    if blocks:
        latest = blocks[0]
        block_text = latest[2]
        for keyword in ['净资产', '股东权益', '所有者权益']:
            if keyword in block_text:
                for line in block_text.split('\n'):
                    if keyword in line:
                        print(f"  Block[{latest[0]}{latest[1]}] [{keyword}]: {line.strip()[:120]}")
                        break
    print()
