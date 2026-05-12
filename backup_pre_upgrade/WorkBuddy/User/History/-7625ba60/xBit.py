"""
检查 NeoData API 返回的季度报告数据格式
查询一只股票，看季度报告段落包含哪些字段
"""
import json, os, sys
sys.path.insert(0, r'c:\Users\green\WorkBuddy\20260424203734\workplace')

# 读取 token
token_path = os.path.join(os.path.expanduser('~'), '.workbuddy', '.neodata_token')
token = open(token_path).read().strip() if os.path.exists(token_path) else ''

import requests

# 用晓程科技测试
ts_code = "300139.SZ"
name = "晓程科技"

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {"query": f"{ts_code} {name} 季报"}

print(f"查询: {payload['query']}")
print("=" * 60)

try:
    resp = requests.post(
        "https://copilot.tencent.com/agenttool/v1/neodata",
        headers=headers, json=payload, timeout=30
    )
    data = resp.json()
    
    if data.get('code') == '200':
        content = ''
        for item in data.get('data', {}).get('apiRecall', []):
            content += item.get('content', '')
        
        # 找所有季度报告段落
        import re
        quarters = re.findall(r'统计截止日期为(\d{8})的(一季报|中报|三季报|年报)', content)
        print(f"\n找到报告段落: {len(quarters)} 个")
        for date, rtype in quarters:
            print(f"  {date} {rtype}")
        
        # 提取最新季度（非年报）
        quarterly_dates = [(d, t) for d, t in quarters if t != '年报']
        if quarterly_dates:
            latest = max(quarterly_dates, key=lambda x: x[0])
            print(f"\n最新季度报告: {latest[0]} {latest[1]}")
            
            # 提取该季度段落
            pattern = rf'统计截止日期为{latest[0]}的{latest[1]}(.*?)(?=统计截止日期为|$)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                block = match.group(1).strip()
                print(f"\n段落长度: {len(block)} 字符")
                print("\n--- 段落内容（前2000字符）---")
                print(block[:2000])
                
                # 检查关键指标是否存在
                keywords = [
                    '加权净资产收益率ROE', '净资产收益率ROE', '销售毛利率', '销售净利率',
                    '营业收入同比增长', '营收同比增长', '归母净利润同比增长',
                    '资产负债率', '营业总收入', '净利润', '扣非净利润',
                    '经营活动产生的现金流量净额', '总资产周转率', '应收账款周转率'
                ]
                print("\n--- 关键指标检查 ---")
                found = 0
                for kw in keywords:
                    if kw in block:
                        # 找到包含该关键词的行
                        for line in block.split('\n'):
                            if kw in line:
                                print(f"  [OK] {kw}: {line.strip()[:100]}")
                                found += 1
                                break
                    else:
                        print(f"  [MISSING] {kw}")
                print(f"\n找到 {found}/{len(keywords)} 个关键指标")
        else:
            print("\n未找到季度报告段落")
    else:
        print(f"API 错误: {data}")

except Exception as e:
    print(f"请求失败: {e}")
