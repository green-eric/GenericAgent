#!/usr/bin/env python3
"""Debug: 模拟 300308.SZ 的 API 返回文本，验证解析器行为"""
import os, json, re, subprocess, sys

os.environ['PYTHONIOENCODING'] = 'utf-8'

# Step 1: 获取 API 原始文本
cmd = [
    sys.executable, '-X', 'utf8',
    r'C:\Users\green\.workbuddy\plugins\marketplaces\cb_teams_marketplace\plugins\finance-data\skills\neodata-financial-search\scripts\query.py',
    '--query', '300308.SZ 中际旭创 年报',
    '--data-type', 'api'
]
result = subprocess.run(cmd, capture_output=True)
raw = result.stdout.decode('utf-8', errors='replace')
raw = re.sub(r'#< CLIXML\r?\n?', '', raw)
raw = re.sub(r'<Objs[\s\S]*?</Objs>', '', raw)
m = re.search(r'\{[\s\S]*\}', raw)
data = json.loads(m.group())
recalls = data['data']['apiData']['apiRecall']

# 拼接所有 content（和 stock_analyzer.py 完全相同的逻辑）
all_content = "\n".join(r.get("content", "") for r in recalls)
print(f"总文本长度: {len(all_content)} 字符")
print(f"API 返回块数: {len(recalls)}")
print()

# Step 2: 用和 stock_analyzer.py 完全相同的解析器
# 内联关键函数
def parse_number_with_unit(text):
    m = re.search(r'([-+]?\d+\.?\d*)\s*(万[亿]?元|亿元|万元|万亿元|千元|元)', text)
    if not m: return None
    num, unit = float(m.group(1)), m.group(2)
    if '万亿' in unit: return num * 1e12
    if '亿' in unit: return num * 1e8
    if '万' in unit: return num * 1e4
    if '千' in unit: return num * 1e3
    return num

def extract_percent_flex(text, keywords):
    if not text: return None
    for kw in keywords:
        pats = [
            re.escape(kw) + r'[：:=\s]*([-+]?\d+\.?\d*)%',
            re.escape(kw) + r'[为是]*([-+]?\d+\.?\d*)%',
            r'([-+]?\d+\.?\d*)%[，。；\s]*' + re.escape(kw)
        ]
        for pat in pats:
            m = re.search(pat, text)
            if m:
                try: return float(m.group(1))
                except: continue
    m = re.findall(r'(?<![0-9])([-+]?\d+\.?\d*)%', text)
    return float(m[-1]) if m else None

# 模拟 FinancialReportParser._split
def _split(text):
    parts = re.split(r'(\d{4}[-/年]?(?:\d{1,2}[-/月]?\d{1,2}[日号]?)?)', text)
    combined, i = [], 0
    while i < len(parts)-1:
        ds, ct = parts[i], parts[i+1] if i+1 < len(parts) else ""
        date_str = ds.strip()
        if re.match(r'\d{4}', date_str):
            n = date_str.replace('年', '').replace('月', '').replace('日', '').replace('/', '').replace('-', '').replace('年度', '')
            if len(n) == 4 and n.isdigit():
                n = n + '1231'
            elif len(n) == 8 and n.isdigit():
                pass
            else:
                n = None
            if n:
                combined.append({"date": n, "content": ct})
        i += 2
    if len(combined) < 1:
        combined = [{"date": None, "content": text}]
    for seg in combined:
        seg["type"] = _classify(seg["content"])
    return combined

def _classify(c):
    if not c: return "unknown"
    if re.search(r'年报|年度报告|全年', c): return "annual"
    return "unknown"

# 执行 split
segments = _split(all_content)
print(f"解析出 {len(segments)} 个段落:")
for i, seg in enumerate(segments):
    print(f"  [{i}] date={seg['date']}, type={seg['type']}, content_len={len(seg['content'])}")
    # 打印前200字符
    preview = seg['content'][:200].replace('\n', ' ')
    print(f"       preview: {preview}...")
print()

# 找 latest("annual")
cand = [s for s in segments if s["type"] == "annual" and s["date"]]
if cand:
    cand.sort(key=lambda x: x["date"], reverse=True)
    a = cand[0]
    print(f"选中段落: date={a['date']}, content_len={len(a['content'])}")
    print(f"内容预览:\n{a['content'][:1500]}")
    print()
    
    # 在这个段落里提取指标
    c = a['content']
    print("=== 在选中段落中提取指标 ===")
    
    # OCF
    ocf_match = re.search(r'经营活动.*现金流量净额\s*([-+]?\d+\.?\d*)\s*(万[亿]?元|亿元|万元|万亿元|千元|元)', c)
    if ocf_match:
        ocf_val = parse_number_with_unit(ocf_match.group(0))
        print(f"OCF 匹配: {ocf_match.group(0)[:60]}")
        print(f"OCF 值: {ocf_val}")
    else:
        print("OCF 未匹配!")
        # 搜索关键词
        for kw in ['经营活动', '现金流量', '现金流']:
            if kw in c:
                idx = c.index(kw)
                print(f"  找到关键词 '{kw}' 在位置 {idx}: ...{c[max(0,idx-20):idx+80]}...")
    
    # 净利润
    np_match = re.search(r'净利润\s*([-+]?\d+\.?\d*)\s*(万[亿]?元|亿元|万元|万亿元|千元|元)', c)
    if np_match:
        np_val = parse_number_with_unit(np_match.group(0))
        print(f"净利润匹配: {np_match.group(0)[:60]}")
        print(f"净利润值: {np_val}")
    else:
        print("净利润未匹配!")
    
    # 毛利率
    gm = extract_percent_flex(c, ["销售毛利率", "毛利率"])
    print(f"毛利率: {gm}")
    
    # 净利率
    nm = extract_percent_flex(c, ["销售净利率", "净利率"])
    print(f"净利率: {nm}")
    
    # 营收同比
    ry = extract_percent_flex(c, ["营业收入同比增长", "营收同比增长"])
    print(f"营收同比: {ry}")
    
    # 净利润同比
    py = extract_percent_flex(c, ["净利润同比增长", "归母净利润同比增长"])
    print(f"净利润同比: {py}")
    
    # 资产负债率
    dr = extract_percent_flex(c, ["资产负债率", "负债率"])
    print(f"资产负债率: {dr}")
    
    # ROE
    roe = extract_percent_flex(c, ["加权净资产收益率ROE", "净资产收益率", "ROE"])
    print(f"ROE: {roe}")
    
    # 计算 ocf_to_profit
    if ocf_val and np_val and np_val != 0:
        print(f"\nOCF/净利润 = {ocf_val} / {np_val} = {ocf_val/np_val}")
    else:
        print(f"\n无法计算 OCF/净利润: ocf={ocf_val}, np={np_val}")

else:
    print("未找到任何 annual 类型段落!")
    print("\n=== 回退: 对全部内容提取 ===")
    c = all_content
    for kw in ['经营活动', '现金流量净额', '毛利率', '净利率', '营收同比', '净利润同比', '资产负债率', 'ROE']:
        if kw in c:
            idx = c.index(kw)
            print(f"  [{kw}] 位置 {idx}: ...{c[max(0,idx-10):idx+80]}...")
