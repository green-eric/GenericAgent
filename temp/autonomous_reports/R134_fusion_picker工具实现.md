# ScoreSys + BfM 动态权重融合选股工具实现报告

## 创建文件
- `D:/Project/ScoreSys/fusion_picker.py` (13.8KB)

## 功能

### 动态权重策略（基于R131回测结论）
| Regime | ScoreSys权重 | BfM权重 | 逻辑 |
|--------|-------------|---------|------|
| 牛市(bull) | 30% | 70% | BfM强势/量价维度更有效 |
| 熊市(bear) | 70% | 30% | ScoreSys基本面因子更稳定 |
| 震荡市(range) | 50% | 50% | 等权平衡 |

### BfM代理评分（5维，基于行情数据）
- **资金** (turnover_5d)：换手率活跃度
- **业绩** (pe_ttm)：PE倒数，低PE高分
- **稳定性** (MA5>MA10>MA20)：均线多头排列
- **动量** (ret_1m)：1月涨幅
- **行业动量** (industry_mom_1m)：行业1月涨幅

### 用法
```bash
python fusion_picker.py                        # 表格输出Top20
python fusion_picker.py --top 30               # Top30
python fusion_picker.py --regime bull          # 手动指定regime
python fusion_picker.py --weights 0.3,0.7      # 手动指定权重
python fusion_picker.py --json                 # JSON输出
python fusion_picker.py --export picks.json    # 导出文件
```

## 验证结果
- 4344只股票全部融合成功
- 自动推断regime=bull（基于ScoreSys scores表market_regime众数）
- 三种regime权重变化生效，排名随权重动态调整
- JSON/表格输出格式正确

## 数据流
```
ScoreSys stock_data.db
  ├── scores表 → ScoreSys 12因子评分
  └── quotes表 → BfM代理评分(5维)
       + market_regime推断 → 动态权重
       ↓
  融合排序 → Top N
```

## 与R131的对应
- R131发现两套系统负相关(-0.3976)，融合可降低波动
- R131建议动态权重，本工具直接实现
- R131仅2天数据，本工具可每日运行
