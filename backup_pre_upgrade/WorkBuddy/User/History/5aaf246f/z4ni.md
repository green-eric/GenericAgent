# 2026-04-23 工作记录

## 新征程853股票池 2024年报净利润增长率筛选

- 从15张图片中解析出100只"新征程853"池股票代码
- 通过 NeoData 接口（copilot.tencent.com/agenttool/v1/neodata）分两轮查询2024/2023年报归母净利润
- 计算净利润同比增长率，筛选出 >50% 的共18只
- 注意：codebuddy.cn/v2/tool/financedata 接口 token 认证失败，改用 neodata 接口
- 结果保存至 growth_result.json
