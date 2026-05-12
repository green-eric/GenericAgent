import urllib.request
import json
import sys

# API调用函数
def call_finance_api(api_name, params=None, fields=""):
    url = "https://www.codebuddy.cn/v2/tool/financedata"
    data = {
        "api_name": api_name,
        "params": params or {},
        "fields": fields
    }

    try:
        request = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except Exception as e:
        print(f"API调用失败: {e}")
        return None

# 获取股票基础信息（包含行业分类）
print("正在获取股票基础数据...")
result = call_finance_api(
    api_name="stock_basic",
    params={"exchange": "SSE,SZSE,BJSE", "list_status": "L"},
    fields="ts_code,name,industry,area,list_date"
)

if result and result.get("code") == 0:
    data = result.get("data", {})
    fields = data.get("fields", [])
    items = data.get("items", [])

    print(f"\n=== 股票基础数据 (共{len(items)}只股票) ===")
    print(f"字段: {', '.join(fields)}")

    # 显示前20只股票的行业信息
    print(f"\n=== 前20只股票的行业分类 ===")
    for i, item in enumerate(items[:20]):
        ts_code = item[fields.index("ts_code")] if "ts_code" in fields else ""
        name = item[fields.index("name")] if "name" in fields else ""
        industry = item[fields.index("industry")] if "industry" in fields else "未知"
        area = item[fields.index("area")] if "area" in fields else ""

        print(f"{i+1}. {name}({ts_code}) - 行业: {industry} - 地区: {area}")

    # 统计各行业分布
    print(f"\n=== 行业分布统计 ===")
    industry_count = {}
    for item in items[:500]:  # 统计前500只股票
        if "industry" in fields:
            industry = item[fields.index("industry")]
            if industry and industry != "未知":
                industry_count[industry] = industry_count.get(industry, 0) + 1

    sorted_industries = sorted(industry_count.items(), key=lambda x: x[1], reverse=True)
    for industry, count in sorted_industries[:15]:
        print(f"{industry}: {count}只")

else:
    print(f"API调用失败: {result}")

# 特别查询xuan.txt中的股票
xuan_stocks = [
    "002705", "002718", "002730", "002738", "600103", "600105", "600110", "600114",
    "002752", "600118", "600126", "002787", "600150", "600152", "002796", "600166",
    "600176", "002810", "600183", "600184"
]

print(f"\n=== xuan.txt中股票的详细行业信息 ===")
for symbol in xuan_stocks:
    exchange_suffix = ".SZ" if symbol.startswith(('0','3')) else ".SH"
    ts_code = symbol + exchange_suffix

    result = call_finance_api(
        api_name="stock_basic",
        params={"ts_code": ts_code},
        fields="ts_code,name,industry,area"
    )

    if result and result.get("code") == 0:
        data = result.get("data", {})
        if data.get("items"):
            item = data["items"][0]
            fields_list = data.get("fields", [])
            name = item[fields_list.index("name")] if "name" in fields_list else ""
            industry = item[fields_list.index("industry")] if "industry" in fields_list else "未知"
            area = item[fields_list.index("area")] if "area" in fields_list else ""

            print(f"{symbol} -> {ts_code} ({name}) - 行业: {industry} - 地区: {area}")
        else:
            print(f"{symbol} -> {ts_code} - 未找到数据")
    else:
        print(f"{symbol} -> {ts_code} - API调用失败")