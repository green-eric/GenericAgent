"""
详细检查季度报告字段覆盖情况 - 修正正则
"""
import json, os, re, requests

token_path = os.path.join(os.path.expanduser('~'), '.workbuddy', '.neodata_token')
token = open(token_path).read().strip() if os.path.exists(token_path) else ''
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 测试不同行业的股票
test_stocks = [
    ("300139.SZ", "晓程科技"),
    ("002755.SZ", "奥赛康"),
    ("000001.SZ", "平安银行"),
    ("600519.SH", "贵州茅台"),
    ("000858.SZ", "五粮液"),
]

# 7个核心评分指标关键词
core_keywords = {
    'ROE': ['加权净资产收益率ROE', '净资产收益率ROE'],
    '毛利率': ['销售毛利率'],
    '净利率': ['销售净利率'],
    '营收同比': ['营业收入同比增长', '营收同比增长'],
    '净利润同比': ['归母净利润同比增长'],
    '资产负债率': ['资产负债率'],
    '经营现金流': ['经营活动产生的现金流量净额'],
}

for ts_code, name in test_stocks:
    payload = {"query": f"{ts_code} {name} 年报"}
    try:
        resp = requests.post(
            "https://copilot.tencent.com/agenttool/v1/neodata",
            headers=headers, json=payload, timeout=30
        )
        data = resp.json()
        if data.get('code') != '200':
            print(f"{name}: API 错误 {data.get('code')}")
            continue
        
        content = ''
        for item in data.get('data', {}).get('apiRecall', []):
            content += item.get('content', '')
        
        # 找所有报告段落 - 匹配各种格式
        quarters = re.findall(r'统计截止日期为(\d{8})的([^，。\s]{2,6})', content)
        # 过滤掉非报告段落
        valid_types = {'年报', 'Q1单季报', 'Q3单季报', 'Q4单季报', '中报', '一季报', '三季报', '半年报'}
        quarters = [(d, t) for d, t in quarters if t in valid_types]
        
        print(f"\n{'='*60}")
        print(f"{name} ({ts_code}) - 找到 {len(quarters)} 个报告段落")
        
        for date, rtype in quarters:
            # 提取该段落
            pattern = rf'统计截止日期为{date}的{rtype}(.*?)(?=统计截止日期为|$)'
            match = re.search(pattern, content, re.DOTALL)
            if not match:
                continue
            block = match.group(1).strip()
            
            # 检查核心字段
            found = []
            missing = []
            for field, keywords in core_keywords.items():
                ok = any(kw in block for kw in keywords)
                if ok:
                    found.append(field)
                else:
                    missing.append(field)
            
            print(f"\n  [{date} {rtype}] 字段: {len(found)}/7")
            if missing:
                print(f"    缺失: {', '.join(missing)}")
            # 打印段落前200字符
            print(f"    预览: {block[:150].replace(chr(10), ' ')}...")
    
    except Exception as e:
        print(f"{name}: 请求失败 {e}")
