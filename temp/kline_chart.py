#!/usr/bin/env python3
"""
K线图生成工具 — 腾讯行情API + 纯matplotlib
用法: python kline_chart.py <股票代码> [周期] [天数]
示例: python kline_chart.py 000001 daily 60
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Rectangle
import numpy as np

# === 腾讯行情 API ===
def _code_to_tencent(code: str) -> str:
    """股票代码转腾讯格式: 000001→sz000001, 600000→sh600000"""
    if code.startswith('6'):
        return f"sh{code}"
    elif code.startswith('0') or code.startswith('3'):
        return f"sz{code}"
    return f"sz{code}"

def _period_to_tencent(period: str) -> str:
    """周期映射: daily→day, weekly→week, monthly→month"""
    return {"daily": "day", "weekly": "week", "monthly": "month"}.get(period, "day")

def fetch_kline(code: str, period: str = "daily", count: int = 60) -> dict:
    """从腾讯行情API获取K线数据"""
    tc_code = _code_to_tencent(code)
    tc_period = _period_to_tencent(period)
    
    url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "param": f"{tc_code},{tc_period},,,{count},qfa",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.qq.com/",
    }
    
    # 绕过代理直连
    resp = requests.get(url, params=params, headers=headers, timeout=15,
                        proxies={"http": None, "https": None})
    resp.raise_for_status()
    data = resp.json()
    
    # 解析腾讯API响应
    inner = data.get("data", {}).get(tc_code, {})
    # 先尝试周期key，再尝试"qfq+周期key"
    klines = inner.get(tc_period) or inner.get(f"qfq{tc_period}")
    
    if not klines:
        return {"error": "无数据返回", "code": code}
    
    name = inner.get("name", code)
    
    # 解析K线: [日期, 开盘, 收盘, 最高, 最低, 成交量]
    dates, opens, closes, highs, lows, volumes = [], [], [], [], [], []
    for line in klines:
        if isinstance(line, list):
            parts = line
        else:
            parts = line.split(",")
        dates.append(str(parts[0]))
        opens.append(float(parts[1]))
        closes.append(float(parts[2]))
        highs.append(float(parts[3]))
        lows.append(float(parts[4]))
        volumes.append(float(parts[5]))
    
    return {
        "code": code,
        "name": name,
        "period": period,
        "dates": dates,
        "open": opens,
        "close": closes,
        "high": highs,
        "low": lows,
        "volume": volumes,
    }


def draw_kline_chart(data: dict, output_path: str) -> str:
    """用纯matplotlib画K线图"""
    dates = data["dates"]
    opens = np.array(data["open"])
    closes = np.array(data["close"])
    highs = np.array(data["high"])
    lows = np.array(data["low"])
    volumes = np.array(data["volume"])
    name = data.get("name", data["code"])
    code = data["code"]
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig = plt.figure(figsize=(14, 8))
    
    # 上方K线图
    ax1 = plt.subplot2grid((5, 1), (0, 0), rowspan=3)
    # 下方成交量
    ax2 = plt.subplot2grid((5, 1), (3, 0), rowspan=2, sharex=ax1)
    
    x = np.arange(len(dates))
    width = 0.6
    body_width = width * 0.8
    
    # 涨跌颜色：中国红涨绿跌
    up_color = '#ff3333'
    down_color = '#33aa33'
    
    for i in range(len(dates)):
        is_up = closes[i] >= opens[i]
        color = up_color if is_up else down_color
        
        # 影线
        ax1.plot([i, i], [lows[i], highs[i]], color=color, linewidth=0.8, solid_capstyle='round')
        
        # 实体
        body_bottom = min(opens[i], closes[i])
        body_height = abs(closes[i] - opens[i])
        if body_height == 0:
            body_height = max(highs[i] - lows[i], 0.01) * 0.1
        
        rect = Rectangle((i - body_width/2, body_bottom), body_width, body_height,
                        facecolor=color, edgecolor=color, linewidth=0.5)
        ax1.add_patch(rect)
    
    # 均线
    if len(closes) >= 5:
        ma5 = np.convolve(closes, np.ones(5)/5, mode='valid')
        ax1.plot(x[4:], ma5, color='#ff9900', linewidth=1, label='MA5', alpha=0.8)
    if len(closes) >= 10:
        ma10 = np.convolve(closes, np.ones(10)/10, mode='valid')
        ax1.plot(x[9:], ma10, color='#3399ff', linewidth=1, label='MA10', alpha=0.8)
    if len(closes) >= 20:
        ma20 = np.convolve(closes, np.ones(20)/20, mode='valid')
        ax1.plot(x[19:], ma20, color='#cc66ff', linewidth=1, label='MA20', alpha=0.8)
    
    ax1.legend(loc='upper left', fontsize=8)
    ax1.set_ylabel('价格', fontsize=10)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.tick_params(axis='x', rotation=30, labelsize=8)
    
    # 成交量柱状图
    for i in range(len(dates)):
        is_up = closes[i] >= opens[i]
        color = up_color if is_up else down_color
        ax2.bar(i, volumes[i] / 1e6, width=body_width, color=color, alpha=0.7)
    
    ax2.set_ylabel('成交量(百万)', fontsize=10)
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    # X轴标签：智能间隔
    total = len(dates)
    if total <= 20:
        step = 1
    elif total <= 50:
        step = total // 10
    else:
        step = total // 15
    
    tick_positions = list(range(0, total, max(1, step)))
    tick_labels = [dates[i] for i in tick_positions]
    ax2.set_xticks(tick_positions)
    ax2.set_xticklabels(tick_labels, rotation=30, fontsize=8)
    
    # 标题
    last_price = closes[-1]
    change = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) > 1 else 0
    sign = "+" if change >= 0 else ""
    fig.suptitle(f'{name}({code}) — {data["period"]} K线图 | 最新: {last_price:.2f} ({sign}{change:.2f}%)',
                 fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=120, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    return output_path


def generate_kline(code: str, period: str = "daily", days: int = 60, 
                   output_dir: str = None) -> str:
    """一站式生成K线图"""
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"[*] Fetching {code} {period} K-line data...")
    data = fetch_kline(code, period, days)
    
    if "error" in data:
        print(f"[!] {data['error']}")
        return None
    
    print(f"[+] Got data: {data['name']}({code}), {len(data['dates'])} rows, "
          f"{data['dates'][0]} -> {data['dates'][-1]}")
    
    filename = f"kline_{code}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    output_path = os.path.join(output_dir, filename)
    
    print(f"[*] Drawing chart...")
    draw_kline_chart(data, output_path)
    
    file_size = os.path.getsize(output_path)
    print(f"[+] Saved: {output_path} ({file_size/1024:.1f}KB)")
    
    return output_path


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "000001"
    period = sys.argv[2] if len(sys.argv) > 2 else "daily"
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    result = generate_kline(code, period, days)
    if result:
        print(f"\n>>> SUCCESS: {result}")
    else:
        print("\n>>> FAILED")
        sys.exit(1)