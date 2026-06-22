#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线数据源可用性探测 — 测试akshare非东方财富接口是否可用"""
import sys, io, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

results = {}

# === 测试1: akshare 新浪日线 ===
print("=== [1/6] akshare 新浪日线 (sina) ===")
try:
    import akshare as ak
    start = time.time()
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20250101", end_date="20251231", adjust="qfq")
    elapsed = time.time() - start
    if df is not None and len(df) > 0:
        print(f"  ✅ 成功! {len(df)}行, 耗时{elapsed:.1f}s")
        print(f"  列: {list(df.columns)}")
        print(f"  样本:\n{df.head(2)}")
        results['akshare_sina'] = {'status': 'OK', 'rows': len(df), 'time': round(elapsed, 1)}
    else:
        print(f"  ⚠️ 返回空DataFrame")
        results['akshare_sina'] = {'status': 'EMPTY', 'rows': 0}
except Exception as e:
    print(f"  ❌ 失败: {e}")
    results['akshare_sina'] = {'status': 'FAIL', 'error': str(e)[:100]}

# === 测试2: akshare 腾讯日线 ===
print("\n=== [2/6] akshare 腾讯日线 (tencent) ===")
try:
    import akshare as ak
    start = time.time()
    df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20250101", end_date="20251231", adjust="qfq", source="tencent")
    elapsed = time.time() - start
    if df is not None and len(df) > 0:
        print(f"  ✅ 成功! {len(df)}行, 耗时{elapsed:.1f}s")
        results['akshare_tencent'] = {'status': 'OK', 'rows': len(df), 'time': round(elapsed, 1)}
    else:
        print(f"  ⚠️ 返回空DataFrame")
        results['akshare_tencent'] = {'status': 'EMPTY', 'rows': 0}
except Exception as e:
    print(f"  ❌ 失败: {e}")
    results['akshare_tencent'] = {'status': 'FAIL', 'error': str(e)[:100]}

# === 测试3: akshare 北向资金 ===
print("\n=== [3/6] akshare 北向资金 ===")
try:
    import akshare as ak
    start = time.time()
    df = ak.stock_hsgt_north_net_flow_in_em()
    elapsed = time.time() - start
    if df is not None and len(df) > 0:
        print(f"  ✅ 成功! {len(df)}行, 耗时{elapsed:.1f}s")
        print(f"  列: {list(df.columns)}")
        results['akshare_north_flow'] = {'status': 'OK', 'rows': len(df), 'time': round(elapsed, 1)}
    else:
        print(f"  ⚠️ 返回空DataFrame")
        results['akshare_north_flow'] = {'status': 'EMPTY', 'rows': 0}
except Exception as e:
    print(f"  ❌ 失败: {e}")
    results['akshare_north_flow'] = {'status': 'FAIL', 'error': str(e)[:100]}

# === 测试4: akshare 融资融券 ===
print("\n=== [4/6] akshare 融资融券 ===")
try:
    import akshare as ak
    start = time.time()
    df = ak.stock_margin_sse()
    elapsed = time.time() - start
    if df is not None and len(df) > 0:
        print(f"  ✅ 成功! {len(df)}行, 耗时{elapsed:.1f}s")
        print(f"  列: {list(df.columns)}")
        results['akshare_margin'] = {'status': 'OK', 'rows': len(df), 'time': round(elapsed, 1)}
    else:
        print(f"  ⚠️ 返回空DataFrame")
        results['akshare_margin'] = {'status': 'EMPTY', 'rows': 0}
except Exception as e:
    print(f"  ❌ 失败: {e}")
    results['akshare_margin'] = {'status': 'FAIL', 'error': str(e)[:100]}

# === 测试5: baostock ===
print("\n=== [5/6] baostock ===")
try:
    import baostock as bs
    start = time.time()
    lg = bs.login()
    if lg.error_code == '0':
        rs = bs.query_all_stock(day=None)
        if rs.error_code == '0':
            print(f"  ✅ 登录成功! 获取股票列表, 耗时{time.time()-start:.1f}s")
            count = 0
            while rs.next():
                count += 1
                if count >= 5:
                    break
            print(f"  获取到{count}+只股票")
            results['baostock'] = {'status': 'OK', 'login': True}
        else:
            print(f"  ⚠️ 获取股票列表失败: {rs.error_msg}")
            results['baostock'] = {'status': 'PARTIAL', 'login': True, 'error': rs.error_msg}
        bs.logout()
    else:
        print(f"  ❌ 登录失败: {lg.error_msg}")
        results['baostock'] = {'status': 'FAIL', 'error': lg.error_msg}
except Exception as e:
    print(f"  ❌ 失败: {e}")
    results['baostock'] = {'status': 'FAIL', 'error': str(e)[:100]}

# === 测试6: 本地CSV/Excel数据 ===
print("\n=== [6/6] 本地数据文件 ===")
import os, glob
data_dirs = ['./data', './', '../']
local_files = []
for d in data_dirs:
    if os.path.exists(d):
        for ext in ['*.csv', '*.xlsx', '*.xls', '*.json']:
            files = glob.glob(os.path.join(d, ext))
            local_files.extend(files)
        # 递归一层
        for sub in os.listdir(d):
            subdir = os.path.join(d, sub)
            if os.path.isdir(subdir) and sub.startswith('.') is False:
                for ext in ['*.csv', '*.xlsx']:
                    files = glob.glob(os.path.join(subdir, ext))
                    local_files.extend(files)

if local_files:
    print(f"  找到{len(local_files)}个数据文件:")
    for f in local_files[:10]:
        size = os.path.getsize(f)
        print(f"    {f} ({size/1024:.1f}KB)")
    results['local_files'] = {'status': 'FOUND', 'count': len(local_files), 'files': local_files[:10]}
else:
    print("  ⚠️ 未找到本地数据文件")
    results['local_files'] = {'status': 'NONE'}

# === 汇总 ===
print("\n" + "="*60)
print("📊 数据源探测汇总")
print("="*60)
ok_sources = [k for k, v in results.items() if v.get('status') in ('OK', 'FOUND')]
fail_sources = [k for k, v in results.items() if v.get('status') in ('FAIL', 'EMPTY', 'NONE')]
partial_sources = [k for k, v in results.items() if v.get('status') == 'PARTIAL']

for name, info in results.items():
    status = info.get('status', '?')
    icon = '✅' if status in ('OK', 'FOUND') else '⚠️' if status == 'PARTIAL' else '❌'
    detail = f"{info.get('rows', '')}行" if 'rows' in info else info.get('count', '') + '个文件' if 'count' in info else info.get('error', '')[:50]
    print(f"  {icon} {name}: {status} {detail}")

print(f"\n可用: {len(ok_sources)} | 部分: {len(partial_sources)} | 失败: {len(fail_sources)}")

# 保存结果
with open('offline_data_probe_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\n结果已保存: offline_data_probe_results.json")

# 推荐下一步
if ok_sources:
    print(f"\n🎯 推荐数据源: {ok_sources[0]}")
    if 'akshare_sina' in ok_sources:
        print("  → 可用akshare新浪接口获取历史日K数据")
    elif 'baostock' in ok_sources:
        print("  → 可用baostock获取历史日K数据")
    elif 'local_files' in ok_sources:
        print("  → 可先用本地数据做分析，后续补充在线数据")
