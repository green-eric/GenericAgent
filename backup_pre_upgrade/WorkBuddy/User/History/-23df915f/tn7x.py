"""
测试新的混合行业判定逻辑
不依赖完整流程，单独验证行业映射构建和判定
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from annual_scorer import (
    build_industry_map_from_akshare,
    load_akshare_industry_map,
    determine_industry,
    load_industry_map,
    Config
)

print("=" * 60)
print("测试新的混合行业判定逻辑")
print("=" * 60)

# 1. 测试 akshare 构建（强制刷新）
print("\n📋 Step 1: 构建 akshare 申万行业映射")
print("-" * 45)
t0 = time.time()
akshare_map = build_industry_map_from_akshare(force_refresh=True)
elapsed = time.time() - t0
print(f"\n总耗时: {elapsed:.1f}s")
print(f"映射覆盖: {len(akshare_map)} 只股票")

# 2. 验证缓存
print("\n📋 Step 2: 验证缓存加载")
print("-" * 45)
t0 = time.time()
cached_map = load_akshare_industry_map()
print(f"缓存加载耗时: {time.time()-t0:.3f}s")
print(f"缓存覆盖: {len(cached_map)} 只股票")
print(f"缓存与构建一致: {akshare_map == cached_map}")

# 3. 测试 xuan.txt 覆盖度
print("\n📋 Step 3: xuan.txt 覆盖度")
print("-" * 45)
xuan_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xuan.txt")
codes = []
with open(xuan_file, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            parts = line.replace("\t", " ").split()
            if parts:
                codes.append(parts[0])

old_map = load_industry_map()

print(f"\n{'代码':<12} {'旧映射':<12} {'akshare':<12} {'最终判定':<12}")
print("-" * 50)
for c in codes:
    code_short = c.replace(".SH", "").replace(".SZ", "")
    old_ind = old_map.get(code_short, old_map.get(c, "无"))
    ak_ind = akshare_map.get(code_short, "无")

    # 模拟 determine_industry（无 content, 无 API）
    final = determine_industry(
        c, "", "", old_map,
        use_api=False, akshare_map=akshare_map
    )
    print(f"  {c:<10} {str(old_ind):<12} {str(ak_ind):<12} {str(final):<12}")

# 4. 统计
print("\n📋 Step 4: 统计")
print("-" * 45)
covered_by_akshare = sum(1 for c in codes if c.replace(".SH","").replace(".SZ","") in akshare_map)
covered_by_old = sum(1 for c in codes if old_map.get(c.replace(".SH","").replace(".SZ",""), old_map.get(c)) is not None)
print(f"xuan.txt 总数: {len(codes)}")
print(f"旧映射覆盖: {covered_by_old}/{len(codes)} ({covered_by_old/len(codes)*100:.0f}%)")
print(f"akshare覆盖: {covered_by_akshare}/{len(codes)} ({covered_by_akshare/len(codes)*100:.0f}%)")

# 5. 特别验证宏和科技
print("\n📋 Step 5: 宏和科技(603256)验证")
print("-" * 45)
print(f"旧映射: {old_map.get('603256', old_map.get('603256.SH', '无'))}")
print(f"akshare: {akshare_map.get('603256', '无')}")
final_603256 = determine_industry(
    "603256.SH", "宏和科技", "", old_map,
    use_api=False, akshare_map=akshare_map
)
print(f"最终判定: {final_603256}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
