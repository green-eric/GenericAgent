# R69 — K线图集成到微信Bot

**日期**: 2026-05-08  
**类型**: 集成  
**状态**: ✅ 已完成

---

## 变更摘要

`kline_chart.py` → `wechatapp.py` 集成：用户发送"股票代码 K线"即可自动返回K线PNG图表。

## 变更详情

### wechatapp.py (2处修改)

**① Import (L39前插入)**
```python
try:
    _TEMP_DIR_KL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
    sys.path.insert(0, _TEMP_DIR_KL)
    from kline_chart import generate_kline as _gen_kline
except ImportError:
    _gen_kline = None
```

**② 消息拦截器 (L718后 `/auto` handler与 `_handle()` 之间)**
```python
_kl_match = re.search(r'[Kk]线.*?(\d{6})|(\d{6}).*?[Kk]线', text)
if _kl_match:
    _kl_code = _kl_match.group(1) or _kl_match.group(2)
    bot.send_text(uid, f'📈 正在获取 {_kl_code} K线数据...', context_token=ctx)
    png_path = _gen_kline(_kl_code) if _gen_kline else None
    if png_path and os.path.isfile(png_path):
        bot.send_image(uid, png_path, context_token=ctx)
    else:
        bot.send_text(uid, f'❌ {_kl_code} K线图生成失败，请检查代码或稍后重试', context_token=ctx)
    return
```

## 匹配模式

| 输入示例 | 提取代码 |
|----------|----------|
| `000001 K线` | 000001 ✅ |
| `K线 000001` | 000001 ✅ |
| `k线000001` | 000001 ✅ |
| `看看000001的k线图` | 000001 ✅ |

## 测试结果

| 测试项 | 结果 |
|--------|------|
| `generate_kline('000001', 'daily', 5)` | ✅ 平安银行 5行 69.3KB PNG |
| wechatapp.py 语法检查 | ✅ ast.parse 通过 |

## 未测试项

⚠️ 微信端到端测试需重启bot后人工验证。bot当前未运行（历史session timeout问题待解决）。