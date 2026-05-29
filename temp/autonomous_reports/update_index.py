#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_index.py — 自动更新报告知识图谱索引 (v2)
============================================
扫描 autonomous_reports/ 下所有 R*.md 文件，提取元数据，更新 index.json。

增强功能 (v2):
  - 自动分类: 基于关键词的规则分类
  - 关键词提取: 从标题+正文提取领域关键词
  - 交叉引用: 检测报告间的引用关系

用法:
  python update_index.py              # 更新索引
  python update_index.py --check      # 仅检查，不写入
"""
import os, json, re, argparse
from datetime import datetime
from collections import defaultdict, Counter

RPT_DIR = r'D:\GenericAgent\temp\autonomous_reports'
IDX_PATH = os.path.join(RPT_DIR, 'index.json')

# ============================================================
# 自动分类规则
# ============================================================
CATEGORY_RULES = [
    # (category, list_of_keywords_in_title_or_type)
    ('回测',     ['回测', 'IC', '夏普', '回撤', '净值', '持仓', '调仓', '持有期', 'ICIR', '因子']),
    ('数据',     ['数据', '回填', '断档', '覆盖', 'quotes', 'scores表', 'stock_data', 'pe_ttm', 'total_mv']),
    ('策略',     ['策略', '融合', 'RPS', 'ScoreSys', '选股', '参数优化', 'top_n', 'min_score']),
    ('因子',     ['因子', 'alpha', 'reversal', '动量', '波动率', 'regime', 'AlphaTrading', 'Alpha191']),
    ('系统',     ['定时任务', 'proxy', '监控', 'crontab', '计划任务', 'scheduled', 'supervisor']),
    ('维护',     ['维护', '修复', '日志', '索引', 'update_index', '增强', '整理']),
    ('分析',     ['分析', '诊断', '评估', '规划', '实测', '验证']),
    ('工具',     ['工具', '脚本', '脚本', '自动化', 'CDP', '浏览器', 'adb']),
    ('记忆',     ['记忆', 'SOP', 'global_mem', '索引', '知识库']),
]

def auto_categorize(title, r_type, content_preview=''):
    """基于关键词规则自动分类，返回类别列表"""
    text = f"{title} {r_type} {content_preview}".lower()
    categories = []
    for cat, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw.lower() in text:
                categories.append(cat)
                break
    return categories if categories else ['其他']

# ============================================================
# 关键词提取
# ============================================================
DOMAIN_KEYWORDS = [
    # 策略/系统
    'RPS20', 'ScoreSys', '融合', '选股', 'backtest', '回测', 'IC', 'ICIR',
    '夏普比率', '最大回撤', 'alpha', '因子', 'regime', 'reversal', '动量',
    '波动率', 'AlphaTrading', 'Alpha191', 'param_optimizer',
    # 数据
    'pe_ttm', 'total_mv', 'quotes', 'scores', 'stock_data', '回填', '断档',
    '覆盖率', 'fetcher', '数据源',
    # 系统
    '定时任务', '计划任务', 'proxy', '监控', 'scheduled_backtest',
    'update_index', '日志',
    # 技术
    'sqlite', 'pandas', 'numpy', 'Python', 'CDP', '浏览器',
    # 项目
    '自主行动', 'TODO', '规划', '验证', '修复', '优化',
]

def extract_keywords(title, r_type, content_preview=''):
    """从标题+类型+内容预览中提取领域关键词"""
    text = f"{title} {r_type} {content_preview}"
    found = []
    for kw in DOMAIN_KEYWORDS:
        if kw.lower() in text.lower():
            found.append(kw)
    return found

# ============================================================
# 交叉引用检测
# ============================================================
def detect_cross_references(reports_meta):
    """检测报告间的交叉引用关系
    
    策略:
    1. 检测报告正文中是否引用了其他报告的编号 (R\\d+)
    2. 检测共同关键词重叠度 > 阈值
    返回: [{from: Rxx, to: Ryy, type: 'ref'|'related', strength: N}]
    """
    refs = []
    r_num_map = {r['r_num']: r for r in reports_meta if r['r_num']}
    
    # 读取所有报告内容
    content_cache = {}
    for r in reports_meta:
        if not r['r_num']:
            continue
        fp = os.path.join(RPT_DIR, r['file'])
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content_cache[r['r_num']] = f.read()
        except:
            content_cache[r['r_num']] = ''
    
    # 1. 显式引用检测: R\d+ 格式
    for r in reports_meta:
        if not r['r_num'] or r['r_num'] not in content_cache:
            continue
        content = content_cache[r['r_num']]
        # 找所有 R\d+ 引用 (排除自身)
        found_refs = set(re.findall(r'R(\d+)', content))
        for ref_num_str in found_refs:
            ref_num = f"R{ref_num_str}"
            if ref_num != r['r_num'] and ref_num in r_num_map:
                refs.append({
                    'from': r['r_num'],
                    'to': ref_num,
                    'type': 'ref',
                    'strength': 3  # 显式引用强度高
                })
    
    # 2. 关键词重叠检测
    kw_map = {}
    for r in reports_meta:
        if r['r_num'] and 'keywords' in r:
            kw_map[r['r_num']] = set(r['keywords'])
    
    r_nums = sorted(kw_map.keys())
    for i in range(len(r_nums)):
        for j in range(i+1, len(r_nums)):
            a, b = r_nums[i], r_nums[j]
            overlap = kw_map[a] & kw_map[b]
            if len(overlap) >= 3:  # 至少3个共同关键词
                refs.append({
                    'from': a,
                    'to': b,
                    'type': 'related',
                    'strength': len(overlap),
                    'shared_keywords': sorted(overlap)
                })
    
    # 去重 (ref类型优先于related)
    dedup = {}
    for ref in refs:
        key = (ref['from'], ref['to'])
        if key not in dedup or ref['strength'] > dedup[key]['strength']:
            dedup[key] = ref
    
    return list(dedup.values())

# ============================================================
# 主流程
# ============================================================
def scan_reports():
    reports = []
    for f in sorted(os.listdir(RPT_DIR)):
        if not f.startswith('R') or not f.endswith('.md') or f == 'README.md':
            continue
        fp = os.path.join(RPT_DIR, f)
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                content = fh.read()
                lines = content.split('\n')[:10]
                preview = content[:500]
        except:
            continue

        title = f
        date = 'unknown'
        r_type = 'other'
        r_num = ''

        for line in lines:
            stripped = line.strip()
            m = re.match(r'^#?\s*(R\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+)\|s*(.+)', stripped)
            if not m:
                m = re.match(r'^(R\d+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+)\|s*(.+)', stripped)
            if m:
                r_num = m.group(1)
                date = m.group(2).strip()
                r_type = m.group(3).strip()
                title = f"{r_num} | {date} | {r_type} | {m.group(4).strip()}"
                break

        if not r_num:
            m3 = re.search(r'R(\d+)', f)
            if m3:
                r_num = f"R{m3.group(1)}"

        if date == 'unknown':
            m4 = re.search(r'(\d{4})(\d{2})(\d{2})', f)
            if m4:
                date = f"{m4.group(1)}-{m4.group(2)}-{m4.group(3)}"

        # 增强: 自动分类 + 关键词提取
        categories = auto_categorize(title, r_type, preview)
        keywords = extract_keywords(title, r_type, preview)

        reports.append({
            'file': f,
            'title': title,
            'date': date,
            'type': r_type,
            'r_num': r_num,
            'categories': categories,
            'keywords': keywords,
        })

    reports.sort(key=lambda x: int(re.search(r'R(\d+)', x['r_num']).group(1)) if re.search(r'R(\d+)', x['r_num']) else 0)
    return reports


def update_index(check_only=False):
    reports = scan_reports()
    matched = sum(1 for r in reports if r['date'] != 'unknown')

    if os.path.exists(IDX_PATH):
        with open(IDX_PATH, 'r', encoding='utf-8') as f:
            idx = json.load(f)
    else:
        idx = {'generated': '', 'total': 0, 'categories': {}, 'reports': [], 'cross_references': []}

    old_total = idx.get('total', 0)
    idx['reports'] = reports
    idx['total'] = len(reports)
    idx['generated'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 增强: 自动分类汇总
    cat_counter = Counter()
    for r in reports:
        for cat in r.get('categories', []):
            cat_counter[cat] += 1
    idx['categories'] = dict(cat_counter.most_common())

    # 增强: 交叉引用
    cross_refs = detect_cross_references(reports)
    idx['cross_references'] = cross_refs

    # 增强: 关键词云
    kw_counter = Counter()
    for r in reports:
        for kw in r.get('keywords', []):
            kw_counter[kw] += 1
    idx['keywords_cloud'] = dict(kw_counter.most_common(50))

    if check_only:
        print(f"[check] {len(reports)} reports, {matched} with date (old: {old_total})")
        print(f"  Categories: {idx['categories']}")
        print(f"  Cross-refs: {len(cross_refs)}")
        return

    with open(IDX_PATH, 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, indent=2)

    print(f"index.json updated: {len(reports)} reports ({matched} with date), +{len(reports)-old_total} new")
    print(f"  Categories: {idx['categories']}")
    print(f"  Cross-references: {len(cross_refs)}")
    print(f"  Top keywords: {list(idx['keywords_cloud'].items())[:10]}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update report knowledge graph index')
    parser.add_argument('--check', action='store_true', help='Check only, no write')
    args = parser.parse_args()
    update_index(check_only=args.check)
