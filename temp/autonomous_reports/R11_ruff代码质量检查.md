# R11 · ruff 代码质量检查

## 执行时间
2026-05-05 (自主行动)

## 检查范围
D:/Project 下所有 Python 项目

## 结果汇总

| 项目 | .py文件数 | 初始问题 | 自动修复 | 剩余 |
|:---:|:---:|:---:|:---:|:---:|
| ScoreSys | 19 | 9 | 6 | 3 |
| AnnualScorer | 21 | 0 | 0 | 0 |
| BullishForMonitoring | 1649 | 6 | 1 | 5 |
| AtomCode | 0 | - | - | - |
| **合计** | **1689** | **15** | **7** | **8** |

## 自动修复的问题 (7个)
- ScoreSys: 6个 F401 unused import (os, typing.Optional, typing.Dict, typing.Any, math, numpy)
- BullishForMonitoring: 1个 F401 unused import (json)

## 剩余需手动修复 (8个)

### ScoreSys (3个) — f-string 引号嵌套语法错误
- evaluator.py:130 — Cannot reuse outer quote character in f-strings
- evaluator.py:288 — Cannot reuse outer quote character in f-strings
- fetcher.py:125 — Cannot reuse outer quote character in f-strings

### BullishForMonitoring (5个) — import 不在文件顶部
- monitor.py:31,36,37,38,42 — E402 Module level import not at top of file

## 建议
1. ScoreSys 的 f-string 问题：将内层引号改为不同字符 (外层单引号改外层双引号)
2. BfM 的 import 问题：将 monitor.py 中的条件 import 移到文件顶部或用 TYPE_CHECKING 包裹
