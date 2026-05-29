#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""search_reports.py - unified search for GA reports + AnnualScorer
Usage: python search_reports.py <query> [top_n] [--source GA|AScorer]
"""
import json
import sys
import os
import io
import re

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

INDEX_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'search_index.json')
REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))

def get_snippet(filepath, query, context=60):
    try:
        with open(os.path.join(REPORTS_DIR, filepath), 'r', encoding='utf-8', errors='replace') as f:
            content = f.read().lower()
        pos = content.find(query.lower())
        if pos < 0:
            return content[:120].replace(chr(10), ' ')
        start = max(0, pos - context)
        end = min(len(content), pos + len(query) + context)
        return ('...' + content[start:end].replace(chr(10), ' ') + '...').strip()
    except:
        return ''

def compute_tfidf(term, entry, data, total_files):
    """计算 TF-IDF 权重: TF * log(N/DF)"""
    import math
    # DF: 包含该词的文件数
    df = len(data['index'].get(term, []))
    if df == 0:
        return 0
    # IDF
    idf = math.log(total_files / df) + 1
    # TF: 该词在此文件中出现次数（用条目数近似）
    tf = sum(1 for e in data['index'].get(term, []) if e['f'] == entry['f'])
    return tf * idf


def search(query, top_n=10, source_filter=None):
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    terms = query.lower().split()
    total_files = len(data.get('files', {}))
    results = {}
    for term in terms:
        for entry in data['index'].get(term, []):
            fname = entry['f']
            # Source filter
            if source_filter:
                src = data['files'].get(fname, {}).get('source', '')
                if source_filter == 'GA' and fname.startswith('AScorer:'):
                    continue
                if source_filter == 'AScorer' and not fname.startswith('AScorer:'):
                    continue
            if fname not in results:
                results[fname] = {'title': entry['t'], 'score': 0, 'file': fname, 'source': data['files'].get(fname, {}).get('source', '?'), 'matched_terms': set()}
            # TF-IDF 加权评分
            tfidf = compute_tfidf(term, entry, data, total_files)
            results[fname]['score'] += tfidf
            results[fname]['matched_terms'].add(term)
            # 标题匹配加权（标题中出现查询词 ×2）
            title_lower = entry.get('t', '').lower()
            if term in title_lower:
                results[fname]['score'] += tfidf * 2
    # 多词匹配额外加分（匹配词数/总词数 的比例加成）
    for fname in results:
        coverage = len(results[fname]['matched_terms']) / len(terms)
        results[fname]['score'] *= (1 + coverage)  # 全匹配 ×2, 半匹配 ×1.5
        results[fname]['coverage'] = coverage
    ranked = sorted(results.values(), key=lambda x: x['score'], reverse=True)[:top_n]
    print('Search: "%s" -- %d results (TF-IDF weighted)' % (query, len(ranked)))
    if source_filter:
        print('[Filter: %s]' % source_filter)
    print()
    for i, r in enumerate(ranked):
        src_tag = '[%s]' % r['source']
        score_bar = '█' * min(int(r['score'] * 2), 20) + '░' * max(0, 20 - int(r['score'] * 2))
        coverage = r.get('coverage', 0)
        cov_tag = '全匹配' if coverage >= 0.99 else '%.0f%%' % (coverage * 100)
        print('%d. %s [%.1f|%s] %s' % (i+1, src_tag, r['score'], cov_tag, r['title']))
        if r['source'] == 'AnnualScorer':
            print('   AScorer:%s' % r['file'])
        else:
            print('   %s' % r['file'])
        print('   %s' % score_bar)
        snippet = get_snippet(r['file'], terms[0]) if r['source'] == 'GA' else ''
        if snippet:
            print('   %s' % snippet[:150])
        print()
    if not ranked:
        print('  No results found.')

if __name__ == '__main__':
    args = sys.argv[1:]
    source_filter = None
    if '--source' in args:
        idx = args.index('--source')
        source_filter = args[idx+1]
        args = args[:idx] + args[idx+2:]
    query = ' '.join(args) if args else ''
    top = 10
    # Check if last arg is a digit
    if query.split() and query.split()[-1].isdigit():
        top = int(query.split()[-1])
        query = ' '.join(query.split()[:-1])
    if not query:
        print('Usage: python search_reports.py <query> [top_n] [--source GA|AScorer]')
        sys.exit(1)
    search(query, top, source_filter)
