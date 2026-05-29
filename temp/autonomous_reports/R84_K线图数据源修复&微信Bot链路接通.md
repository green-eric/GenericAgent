# R84 — ScoreSys K线图数据源修复 & 微信Bot链路接通

## 执行摘要

修复kline_chart.py的东方财富API数据源（被墙不可达），改用腾讯行情API。wechatapp.py的K线图回复链路已集成（L63 import + L748调用），修复后微信发送股票代码即可收到K线图。

---

## 问题诊断

| 项目 | 详情 |
|:--|:--|
| 根因 | kline_chart.py使用东方财富push2 API，在当前网络环境下被墙不可达 |
| 影响 | 微信Bot回复K线图请求时，_gen_kline()返回None → 用户收到"生成失败" |
| 已有基础 | wechatapp.py L63已import kline_chart，L743-753已有完整K线图请求拦截+发送链路 |

## 修复过程

1. **验证腾讯API可达性** → `web.ifzq.gtimg.cn/appstock/app/fqkline/get` 返回200，数据完整
2. **重写fetch_kline()函数** → 东方财富API → 腾讯行情API，返回格式兼容（日期/O/H/L/C/V六列）
3. **更新函数名** → `fetch_kline_eastmoney()` → `fetch_kline()`
4. **同步调用处** → generate_kline()内调用更新

## 验收测试

| 股票代码 | 名称 | 结果 | 文件大小 |
|:--|:--|:--:|:--:|
| 000001 | 平安银行 | ✅ | 121.8KB |
| 600519 | 贵州茅台 | ✅ | 128.6KB |
| 300750 | 宁德时代 | ✅ | 133.2KB |

## 代码变更

```
kline_chart.py:
  - fetch_kline_eastmoney() → fetch_kline() [腾讯API]
  - generate_kline() 调用处同步更新
```

## 链路说明

```
微信消息 → wechatapp.py L744 正则匹配6位数字代码
         → _gen_kline(code) [kline_chart.generate_kline]
         → 腾讯API获取K线数据
         → matplotlib生成PNG
         → bot.send_image() 发送给用户
```

## 注意事项

- 腾讯API无需代理，直连可达
- 生成图片保存在 temp/ 目录（wechatapp.py L62 sys.path已配置）
- 如需评分卡片功能，需额外集成ScoreSys评分查询（TODO后续跟进）
