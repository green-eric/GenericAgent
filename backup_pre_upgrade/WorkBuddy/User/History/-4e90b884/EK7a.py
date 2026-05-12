"""
检查 NeoData API 返回中包含哪些季度报告段落
"""
import json, os, re, requests

token_path = os.path.join(os.path.expanduser('~'), '.workbuddy', '.neodata_token')
token = open(token_path).read().strip() if os.path.exists(token_path) else ''

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 测试多种查询方式
test_queries = [
    "300139.SZ 晓程科技 年报",
    "300139.SZ 晓程科技 一季报",
    "300139.SZ 晓程科技 三季报",
    "300139.SZ 晓程科技 中报",
    "002755.SZ 奥赛康 年报",
    "002755.SZ 奥赛康 三季报",
]

for query in test_queries:
    payload = {"query": query}
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
            
            quarters = re.findall(r'统计截止日期为(\d{8})的(一季报|中报|三季报|年报)', content)
            print(f"\n查询: {query}")
            print(f"  内容长度: {len(content)} 字符")
            print(f"  报告段落: {quarters}")
            
            # 打印前500字符
            if content:
                print(f"  内容预览: {content[:300]}...")
        else:
            print(f"\n查询: {query}")
            print(f"  API 错误: {data.get('code')} {data.get('msg','')}")
    except Exception as e:
        print(f"\n查询: {query}")
        print(f"  请求失败: {e}")
